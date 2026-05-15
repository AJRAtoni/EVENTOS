#!/usr/bin/env python3
"""Import AJRA's upcoming Letterboxd watchlist movies into data/events.json.

Default mode is --dry-run. Use --apply to write JSON and download posters.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

REPO = Path(__file__).resolve().parents[1]
EVENTS_JSON = REPO / "data" / "events.json"
IMAGES_DIR = REPO / "images" / "events"
LETTERBOXD_BASE = "https://letterboxd.com"
WATCHLIST_URL = "https://letterboxd.com/ajra/watchlist/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Chrome/123 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1
)}
PREFERRED_COUNTRIES = ["Spain", "USA", "UK", "United States", "Canada"]


def clean(value: Any = "") -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slugify(value: str = "") -> str:
    s = unicodedata.normalize("NFD", clean(value)).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " y ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def strip_tags(value: str) -> str:
    return clean(html.unescape(re.sub(r"<.*?>", " ", value, flags=re.S)))


def fetch(session: requests.Session, url: str) -> str:
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_watchlist(session: requests.Session) -> list[dict[str, str]]:
    first = fetch(session, WATCHLIST_URL)
    pages = max([1] + [int(x) for x in re.findall(r"/ajra/watchlist/page/(\d+)/", first)])
    films: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        text = first if page == 1 else fetch(session, f"{WATCHLIST_URL}page/{page}/")
        for name, link in re.findall(r'data-item-name="([^"]+)"[^>]+data-item-link="([^"]+)"', text):
            link = html.unescape(link)
            if link in seen:
                continue
            seen.add(link)
            name = html.unescape(name)
            year = None
            m = re.search(r"\((\d{4})\)$", name)
            if m:
                year = int(m.group(1))
            films.append({"watchlist_name": name, "link": link, "year": str(year or "")})
    return films


def parse_json_ld(text: str) -> dict[str, Any]:
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S):
        s = html.unescape(m.group(1)).strip()
        s = re.sub(r"^/\*\s*<!\[CDATA\[\s*\*/", "", s).strip()
        s = re.sub(r"/\*\s*\]\]>\s*\*/$", "", s).strip()
        try:
            data = json.loads(s)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") in {"Movie", "VideoGame"}:
            return data
    return {}


def parse_date(value: str) -> dt.date | None:
    value = strip_tags(value)
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", value)
    if not m or m.group(2) not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))


def iter_release_sections(text: str):
    pattern = re.compile(
        r'<h3 class="release-table-title">(.*?)</h3>\s*<div class="release-table -bydate">(.*?)(?=<h3 class="release-table-title">|</section>\s*</div>\s*</div>\s*<p class="text-link text-footer">|$)',
        re.I | re.S,
    )
    for m in pattern.finditer(text):
        yield strip_tags(m.group(1)), m.group(2)


def parse_releases(text: str) -> list[dict[str, Any]]:
    releases: list[dict[str, Any]] = []
    for section_title, body in iter_release_sections(text):
        # Each by-date listitem contains one date and one or more countries.
        for item in re.finditer(r'<div class="listitem">\s*<div class="cell">\s*<h5 class="date">(.*?)</h5>\s*</div>\s*<div class="cell countries">(.*?)(?=</div>\s*</div>\s*<div class="listitem">|</div>\s*</div>\s*</div>|$)', body, re.I | re.S):
            date = parse_date(item.group(1))
            if not date:
                continue
            countries = [strip_tags(x) for x in re.findall(r'<span class="name">(.*?)</span>', item.group(2), re.I | re.S)]
            releases.append({"type": section_title, "date": date, "countries": countries})
    return releases


def choose_release_date(releases: list[dict[str, Any]], today: dt.date) -> tuple[dt.date | None, str]:
    future = [r for r in releases if r["date"] > today]
    if not future:
        return None, "no future exact release date"

    def matches_type(r: dict[str, Any], keys: tuple[str, ...]) -> bool:
        t = r["type"].lower()
        return any(k in t for k in keys)

    # Only publish real public-release windows. Do not fall back to generic
    # Premiere/Physical rows because those create noisy calendar entries for
    # festival screenings, press events, discs, etc.
    buckets = [
        [r for r in future if matches_type(r, ("theatrical",))],
        [r for r in future if matches_type(r, ("digital", "streaming", "internet", "tv"))],
    ]
    for bucket in buckets:
        if not bucket:
            continue
        for country in PREFERRED_COUNTRIES:
            hits = [r for r in bucket if country in r.get("countries", [])]
            if hits:
                hit = sorted(hits, key=lambda r: r["date"])[0]
                return hit["date"], f'{hit["type"]} ({country})'
        hit = sorted(bucket, key=lambda r: r["date"])[0]
        country_note = ", ".join(hit.get("countries", [])[:3]) or "unknown country"
        return hit["date"], f'{hit["type"]} ({country_note})'
    return None, "no future exact public release date"


def improve_poster_url(url: str, session: requests.Session) -> str:
    candidates = [url]
    for size in ["-0-1000-0-1500-crop", "-0-500-0-750-crop"]:
        candidates.append(re.sub(r"-0-\d+-0-\d+-crop", size, url))
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            r = session.head(candidate, headers={**HEADERS, "Referer": LETTERBOXD_BASE + "/"}, timeout=15, allow_redirects=True)
            if r.ok and (r.headers.get("content-type") or "").startswith("image/"):
                return candidate
        except Exception:
            pass
    return url


def download_poster(session: requests.Session, url: str, event_id: str) -> str:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    poster_url = improve_poster_url(url, session)
    ext = ".jpg"
    m = re.search(r"\.(jpg|jpeg|png|webp)(?:\?|$)", poster_url, re.I)
    if m:
        ext = "." + ("jpg" if m.group(1).lower() == "jpeg" else m.group(1).lower())
    out = IMAGES_DIR / f"{event_id}{ext}"
    if out.exists() and out.stat().st_size > 1000:
        return str(out.relative_to(REPO))
    r = session.get(poster_url, headers={**HEADERS, "Referer": LETTERBOXD_BASE + "/"}, timeout=45)
    r.raise_for_status()
    out.write_bytes(r.content)
    return str(out.relative_to(REPO))


def extract_film(session: requests.Session, link: str, today: dt.date) -> tuple[dict[str, Any] | None, str]:
    url = urljoin(LETTERBOXD_BASE, link)
    text = fetch(session, url)
    ld = parse_json_ld(text)
    if not ld:
        return None, "no JSON-LD"
    title = clean(ld.get("name"))
    if not title:
        return None, "no title"
    releases = parse_releases(text)
    date, release_note = choose_release_date(releases, today)
    if not date:
        return None, release_note
    poster = ld.get("image") or ""
    if not poster:
        return None, "no poster"
    genres = [clean(g).lower() for g in (ld.get("genre") or []) if clean(g)]
    directors = ", ".join(p.get("name", "") for p in (ld.get("director") or []) if isinstance(p, dict) and p.get("name"))
    actors = ", ".join(p.get("name", "") for p in (ld.get("actors") or [])[:2] if isinstance(p, dict) and p.get("name"))
    desc = "Película"
    country = ""
    co = ld.get("countryOfOrigin") or []
    if co and isinstance(co[0], dict):
        country = clean(co[0].get("name"))
    if country:
        desc += f" de {country}"
    if genres:
        desc += " de " + " y ".join(genres)
    if directors:
        desc += ", dirigida por " + directors
    if actors:
        desc += ", con " + actors
    desc += f". Estreno: {release_note}."
    event_id = f"evt-{date.isoformat()}-{slugify(title) or 'sin-titulo'}"
    return {
        "id": event_id,
        "title": title,
        "description": clean(desc),
        "date": date.isoformat(),
        "category": "cineytv",
        "image_source": poster,
        "url": url,
        "status": "published",
        "sites": ["eventos"],
        "brands": [],
        "tags": ["cineytv", "letterboxd", "pelicula"] + genres,
        "release_note": release_note,
    }, "ok"


def norm_title(value: str) -> str:
    return slugify(re.sub(r"^\W+", "", value))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write data/events.json and download posters")
    ap.add_argument("--limit", type=int, default=0, help="limit candidate films for testing")
    args = ap.parse_args()

    today = dt.date.today()
    session = requests.Session()
    data = json.loads(EVENTS_JSON.read_text())
    events = data.get("events", [])
    existing_ids = {e.get("id") for e in events}
    existing_urls = {e.get("url") for e in events if e.get("url")}
    existing_titles = {norm_title(e.get("title", "")) for e in events if e.get("title")}
    existing_title_dates = {(norm_title(e.get("title", "")), e.get("date")) for e in events}

    films = parse_watchlist(session)
    candidates = []
    for f in films:
        year = int(f["year"] or 0)
        if not year or year >= today.year:
            candidates.append(f)
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"watchlist_films={len(films)} candidates={len(candidates)} today={today.isoformat()} apply={args.apply}")
    addable: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for idx, f in enumerate(candidates, 1):
        try:
            event, reason = extract_film(session, f["link"], today)
        except Exception as exc:
            skipped.append({"name": f["watchlist_name"], "link": f["link"], "reason": f"error: {exc}"})
            print(f"[{idx}/{len(candidates)}] SKIP error {f['watchlist_name']}: {exc}")
            continue
        if not event:
            skipped.append({"name": f["watchlist_name"], "link": f["link"], "reason": reason})
            print(f"[{idx}/{len(candidates)}] SKIP {f['watchlist_name']}: {reason}")
            continue
        duplicate = None
        if event["id"] in existing_ids:
            duplicate = "id"
        elif event["url"] in existing_urls:
            duplicate = "url"
        elif norm_title(event["title"]) in existing_titles:
            duplicate = "title"
        elif (norm_title(event["title"]), event["date"]) in existing_title_dates:
            duplicate = "title+date"
        if duplicate:
            skipped.append({"name": event["title"], "link": f["link"], "reason": f"duplicate {duplicate}"})
            print(f"[{idx}/{len(candidates)}] DUP {event['date']} {event['title']} ({duplicate})")
            continue
        addable.append(event)
        existing_ids.add(event["id"])
        existing_urls.add(event["url"])
        existing_titles.add(norm_title(event["title"]))
        existing_title_dates.add((norm_title(event["title"]), event["date"]))
        print(f"[{idx}/{len(candidates)}] ADD {event['date']} {event['title']} — {event['release_note']}")
        time.sleep(0.05)

    if args.apply and addable:
        for event in addable:
            source = event.pop("image_source")
            event.pop("release_note", None)
            event["image"] = download_poster(session, source, event["id"])
            events.append(event)
        events.sort(key=lambda e: (e.get("date", "9999-99-99"), e.get("title", "").lower()))
        data["events"] = events
        data["updatedAt"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        data["source"] = "manual-local-images"
        EVENTS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    report = {
        "apply": args.apply,
        "watchlist_films": len(films),
        "candidates": len(candidates),
        "added": [{k: e[k] for k in ["id", "title", "date", "url"]} for e in addable],
        "skipped_count": len(skipped),
        "skipped_sample": skipped[:40],
    }
    out = REPO / "tmp-letterboxd-watchlist-upcoming-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"report={out}")
    print(f"added_count={len(addable)} skipped_count={len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
