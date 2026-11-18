#!/usr/bin/env node
/**
 * EVENTOS by AJRA — Generador del feed público desde Airtable.
 *
 * Se ejecuta en GitHub Actions (ver .github/workflows/eventos-sync.yml):
 * lee la base de Airtable con AIRTABLE_TOKEN (secreto del repo, nunca en el
 * código), valida los registros, descarga las imágenes que falten a
 * images/events/<attachmentId>.webp y escribe api/events.json con el mismo
 * contrato que servía el antiguo Worker: { records, meta }.
 *
 * Falla cerrado: si la lectura es incompleta o el número de eventos cae más
 * de un 20% respecto al feed publicado, sale con error y no escribe nada.
 */
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE_ID = process.env.AIRTABLE_BASE_ID || 'apphXPfmF1OwvCPWC';
const TABLE = process.env.AIRTABLE_TABLE || 'eventos';
const TOKEN = process.env.AIRTABLE_TOKEN;
const SITE_ORIGIN = 'https://eventos.ajra.es';
const OUT_JSON = path.join(ROOT, 'api', 'events.json');
const IMG_DIR = path.join(ROOT, 'images', 'events');
const MAX_DROP_RATIO = 0.2;

if (!TOKEN) {
  console.error('Falta la variable de entorno AIRTABLE_TOKEN.');
  process.exit(1);
}

async function fetchAllRecords() {
  const records = [];
  let offset;
  do {
    const url = new URL(
      `https://api.airtable.com/v0/${BASE_ID}/${encodeURIComponent(TABLE)}`
    );
    url.searchParams.set('pageSize', '100');
    url.searchParams.set('sort[0][field]', 'FechaOrden');
    url.searchParams.set('sort[0][direction]', 'asc');
    if (offset) url.searchParams.set('offset', offset);
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });
    if (!res.ok) {
      throw new Error(`Airtable respondió ${res.status}: ${await res.text()}`);
    }
    const data = await res.json();
    if (!Array.isArray(data.records)) {
      throw new Error('Respuesta de Airtable sin lista de registros.');
    }
    records.push(...data.records);
    offset = data.offset;
  } while (offset);
  return records;
}

function cleanText(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

async function ensureImage(attachment) {
  const file = path.join(IMG_DIR, `${attachment.id}.webp`);
  if (existsSync(file)) return;
  const res = await fetch(attachment.url);
  if (!res.ok) {
    throw new Error(
      `No se pudo descargar la imagen ${attachment.id} (${res.status}).`
    );
  }
  const buffer = Buffer.from(await res.arrayBuffer());
  let webp;
  try {
    const sharp = (await import('sharp')).default;
    webp = await sharp(buffer).webp({ quality: 82 }).toBuffer();
  } catch {
    // Sin sharp disponible se guarda el original solo si ya es webp.
    if (attachment.type === 'image/webp') {
      webp = buffer;
    } else {
      throw new Error(
        'sharp no está disponible y la imagen no es webp: ' + attachment.id
      );
    }
  }
  await writeFile(file, webp);
  console.log(`Imagen nueva: images/events/${attachment.id}.webp`);
}

async function main() {
  const raw = await fetchAllRecords();
  const records = [];
  await mkdir(IMG_DIR, { recursive: true });

  for (const rec of raw) {
    const f = rec.fields || {};
    const titulo = cleanText(f.Titulo);
    const fecha = cleanText(f.FechaOrden);
    // Sin título o sin fecha no se publica (igual que en el sistema anterior).
    if (!titulo || !fecha) continue;

    const fields = { Titulo: titulo, FechaOrden: fecha };
    const texto = cleanText(f.FechaEstrenoTexto);
    if (texto) fields.FechaEstrenoTexto = texto;
    const categoria = cleanText(f.CategoriaEvento);
    if (categoria) fields.CategoriaEvento = categoria;
    const tipo = cleanText(f.Tipo);
    if (tipo) fields.Tipo = tipo;
    const franquicia = cleanText(f.Franquicia);
    if (franquicia) fields.Franquicia = franquicia;
    const imdb = cleanText(f.IMDbURL);
    if (imdb) fields.IMDbURL = imdb;

    const attachments = Array.isArray(f.Imagen) ? f.Imagen : [];
    if (attachments.length > 0) {
      const att = attachments[0];
      await ensureImage(att);
      fields.Imagen = [
        { url: `${SITE_ORIGIN}/images/events/${att.id}.webp` },
      ];
    }
    records.push({ id: rec.id, fields });
  }

  if (records.length === 0) {
    console.error('La lectura devolvió 0 eventos publicables. No se escribe.');
    process.exit(1);
  }

  // Guarda contra borrados masivos accidentales (>20% de caída).
  if (existsSync(OUT_JSON)) {
    try {
      const prev = JSON.parse(await readFile(OUT_JSON, 'utf8'));
      const prevCount = Array.isArray(prev.records) ? prev.records.length : 0;
      if (
        prevCount > 0 &&
        prev.meta &&
        prev.meta.source === 'airtable' &&
        records.length < prevCount * (1 - MAX_DROP_RATIO)
      ) {
        console.error(
          `Caída sospechosa: de ${prevCount} a ${records.length} eventos. No se escribe.`
        );
        process.exit(1);
      }
    } catch {
      // Si el feed anterior no se puede leer, se sigue con el nuevo.
    }
  }

  const now = new Date().toISOString();
  const revision = createHash('sha256')
    .update(JSON.stringify(records))
    .digest('hex');
  const feed = {
    records,
    meta: {
      source: 'airtable',
      publishedAt: now,
      revision,
      syncedAt: now,
      stale: false,
    },
  };
  await mkdir(path.dirname(OUT_JSON), { recursive: true });
  await writeFile(OUT_JSON, JSON.stringify(feed, null, 2) + '\n');
  console.log(`Feed generado: ${records.length} eventos desde Airtable.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
