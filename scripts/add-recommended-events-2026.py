#!/usr/bin/env python3
"""Add AJRA-approved recommended events to data/events.json.

Downloads representative images locally into images/events/ because Cloudinary
credentials are not guaranteed in this shell.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import mimetypes
import pathlib
import re
import sys
import unicodedata
from urllib.parse import urljoin

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "events.json"
IMAGE_DIR = ROOT / "images" / "events"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36 Hermes/1.0",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

EVENTS = [
    {
        "title": "Google I/O 2026",
        "date": "2026-05-19",
        "category": "tecnologia",
        "url": "https://io.google/2026/",
        "description": "Conferencia anual de Google para desarrolladores, con novedades de IA, Gemini, Android, web y herramientas de desarrollo.",
        "tags": ["tecnologia", "ia", "google", "developers"],
    },
    {
        "title": "Microsoft Build 2026",
        "date": "2026-06-02",
        "category": "tecnologia",
        "url": "https://build.microsoft.com/",
        "description": "Conferencia de Microsoft para desarrolladores centrada en IA, Copilot, cloud, productividad y herramientas para crear software.",
        "tags": ["tecnologia", "ia", "microsoft", "developers"],
    },
    {
        "title": "Copa Mundial FIFA 2026 — partido inaugural",
        "date": "2026-06-11",
        "category": "deportes",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026",
        "description": "Inicio de la Copa Mundial de la FIFA 2026, organizada por Canadá, México y Estados Unidos.",
        "tags": ["deportes", "futbol", "mundial", "fifa"],
    },
    {
        "title": "Copa Mundial FIFA 2026 — final",
        "date": "2026-07-19",
        "category": "deportes",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026",
        "description": "Final de la Copa Mundial de la FIFA 2026.",
        "tags": ["deportes", "futbol", "mundial", "fifa"],
    },
    {
        "title": "gamescom 2026",
        "date": "2026-08-26",
        "category": "videojuegos",
        "url": "https://www.gamescom.global/en",
        "description": "El mayor evento mundial de videojuegos y cultura gaming, celebrado en Colonia del 26 al 30 de agosto de 2026.",
        "tags": ["videojuegos", "gaming", "gamescom"],
    },
    {
        "title": "Resident Evil",
        "date": "2026-09-18",
        "category": "cineytv",
        "url": "https://en.wikipedia.org/wiki/Resident_Evil_(2026_film)",
        "description": "Nueva película de terror dirigida por Zach Cregger y basada en la franquicia de videojuegos Resident Evil.",
        "tags": ["cineytv", "pelicula", "terror", "videojuegos"],
    },
    {
        "title": "Avatar Aang: The Last Airbender",
        "date": "2026-10-09",
        "category": "cineytv",
        "url": "https://en.wikipedia.org/wiki/Avatar_Aang:_The_Last_Airbender",
        "description": "Película animada de fantasía de Avatar Studios, continuación del universo Avatar: The Last Airbender.",
        "tags": ["cineytv", "pelicula", "animacion", "fantasia"],
    },
    {
        "title": "Microsoft Ignite 2026",
        "date": "2026-11-17",
        "category": "tecnologia",
        "url": "https://ignite.microsoft.com/",
        "description": "Evento de Microsoft para tecnología empresarial, cloud, Microsoft 365, Copilot e IA aplicada a productividad.",
        "tags": ["tecnologia", "ia", "microsoft", "productividad"],
    },
    {
        "title": "The Angry Birds Movie 3",
        "date": "2026-12-23",
        "category": "cineytv",
        "url": "https://en.wikipedia.org/wiki/The_Angry_Birds_Movie_3",
        "description": "Tercera película animada basada en la franquicia Angry Birds.",
        "tags": ["cineytv", "pelicula", "animacion", "videojuegos"],
    },
    {
        "title": "Ice Age: Boiling Point",
        "date": "2027-02-05",
        "category": "cineytv",
        "url": "https://en.wikipedia.org/wiki/Ice_Age:_Boiling_Point",
        "description": "Nueva entrega animada de la franquicia Ice Age, producida por 20th Century Animation.",
        "tags": ["cineytv", "pelicula", "animacion", "comedia"],
    },
    {
        "title": "Sonic the Hedgehog 4",
        "date": "2027-03-19",
        "category": "cineytv",
        "url": "https://en.wikipedia.org/wiki/Sonic_the_Hedgehog_4_(film)",
        "description": "Cuarta película de Sonic the Hedgehog, basada en la franquicia de videojuegos de SEGA.",
        "tags": ["cineytv", "pelicula", "videojuegos", "aventura"],
    },
    {
        "title": "Super Bowl LXI",
        "date": "2027-02-14",
        "category": "deportes",
        "url": "https://en.wikipedia.org/wiki/Super_Bowl_LXI",
        "description": "61.ª edición del Super Bowl, uno de los mayores eventos deportivos y publicitarios de Estados Unidos.",
        "tags": ["deportes", "nfl", "super-bowl", "publicidad"],
    },
]

FALLBACK_IMAGES = {
    "Copa Mundial FIFA 2026 — partido inaugural": "https://upload.wikimedia.org/wikipedia/en/thumb/1/17/2026_FIFA_World_Cup_emblem.svg/500px-2026_FIFA_World_Cup_emblem.svg.png",
    "Copa Mundial FIFA 2026 — final": "https://upload.wikimedia.org/wikipedia/en/thumb/1/17/2026_FIFA_World_Cup_emblem.svg/500px-2026_FIFA_World_Cup_emblem.svg.png",
}


def clean(v=""):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def slugify(v=""):
    s = unicodedata.normalize("NFD", clean(v)).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " y ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def make_id(date: str, title: str) -> str:
    return f"evt-{date}-{slugify(title) or 'sin-titulo'}"


def norm_title(title: str) -> str:
    s = unicodedata.normalize("NFD", title or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def extract_meta_image(page_url: str) -> str:
    if page_url in FALLBACK_IMAGES.values():
        return page_url
    r = requests.get(page_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    text = html.unescape(r.text)
    candidates = []
    for prop in ["og:image", "twitter:image", "twitter:image:src"]:
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']+)', text, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\']', text, re.I)
        if m:
            candidates.append(urljoin(page_url, m.group(1)))
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S):
        raw = re.sub(r"^/\*\s*<!\[CDATA\[\s*\*/", "", m.group(1).strip())
        raw = re.sub(r"/\*\s*\]\]>\s*\*/$", "", raw.strip())
        try:
            data = json.loads(html.unescape(raw))
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        for item in stack:
            if isinstance(item, dict) and item.get("image"):
                img = item["image"]
                if isinstance(img, list):
                    img = img[0]
                if isinstance(img, dict):
                    img = img.get("url")
                if img:
                    candidates.append(urljoin(page_url, img))
    for c in candidates:
        if c and c.startswith(("http://", "https://")):
            return c
    raise RuntimeError(f"No image found for {page_url}")


def download_image(image_url: str, event_id: str) -> str:
    r = requests.get(image_url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").split(";")[0].lower()
    ext = mimetypes.guess_extension(ctype) or pathlib.Path(image_url.split("?", 1)[0]).suffix or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
        ext = ".jpg"
    out = IMAGE_DIR / f"{event_id}{ext}"
    out.write_bytes(r.content)
    return str(out.relative_to(ROOT))


def main():
    data = json.loads(DATA_PATH.read_text())
    events = data["events"]
    by_id = {e.get("id"): e for e in events}
    by_title_date = {(norm_title(e.get("title", "")), e.get("date")): e for e in events}
    added = []
    updated = []
    for item in EVENTS:
        event_id = make_id(item["date"], item["title"])
        key = (norm_title(item["title"]), item["date"])
        target = by_id.get(event_id) or by_title_date.get(key)
        image_path = None
        if target and target.get("image"):
            image_path = target["image"]
        else:
            try:
                img_url = FALLBACK_IMAGES.get(item["title"]) or extract_meta_image(item["url"])
                image_path = download_image(img_url, event_id)
                print(f"image {event_id}: {image_path}")
            except Exception as exc:
                print(f"placeholder image for {item['title']}: {exc}", file=sys.stderr)
                bg = {
                    "cineytv": "#111827",
                    "tecnologia": "#0f172a",
                    "videojuegos": "#18230f",
                    "deportes": "#102a43",
                }.get(item["category"], "#111827")
                accent = {
                    "cineytv": "#f97316",
                    "tecnologia": "#60a5fa",
                    "videojuegos": "#a3e635",
                    "deportes": "#38bdf8",
                }.get(item["category"], "#f97316")
                safe_title = html.escape(item["title"])
                safe_cat = html.escape(item["category"].upper())
                svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="#020617"/></linearGradient></defs>
  <rect width="1200" height="675" fill="url(#g)"/>
  <circle cx="1020" cy="120" r="180" fill="{accent}" opacity="0.16"/>
  <circle cx="160" cy="560" r="220" fill="{accent}" opacity="0.10"/>
  <text x="80" y="115" fill="{accent}" font-family="Inter,Arial,sans-serif" font-size="34" font-weight="800" letter-spacing="4">{safe_cat}</text>
  <text x="80" y="330" fill="#f8fafc" font-family="Inter,Arial,sans-serif" font-size="72" font-weight="900">{safe_title}</text>
  <text x="80" y="430" fill="#cbd5e1" font-family="Inter,Arial,sans-serif" font-size="38" font-weight="600">{item['date']}</text>
  <text x="80" y="590" fill="#94a3b8" font-family="Inter,Arial,sans-serif" font-size="28">eventos.ajra.es</text>
</svg>'''
                out = IMAGE_DIR / f"{event_id}.svg"
                out.write_text(svg)
                image_path = str(out.relative_to(ROOT))
        event = {
            "id": event_id,
            "title": item["title"],
            "description": item["description"],
            "date": item["date"],
            "category": item["category"],
            "url": item["url"],
            "status": "published",
            "sites": ["eventos"],
            "brands": [],
            "tags": item["tags"],
            "image": image_path,
        }
        if target:
            target.update(event)
            updated.append(event_id)
        else:
            events.append(event)
            by_id[event_id] = event
            by_title_date[key] = event
            added.append(event_id)
    events.sort(key=lambda e: (e.get("date", "9999-99-99"), e.get("title", "")))
    data["updatedAt"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    data["source"] = "manual-local-images"
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("added", len(added), added)
    print("updated", len(updated), updated)
    print("total", len(events))


if __name__ == "__main__":
    main()
