# EVENTOS by AJRA

Web pública: https://eventos.ajra.es

Sitio estático servido por GitHub Pages desde este repositorio.

## Cómo funciona

- **Fuente de datos:** la base «EVENTOS» de Airtable (tabla `eventos`).
  Airtable es el máster: ahí se crean, editan y borran los eventos
  (la automatización «EVENTOS - Limpiar pasados» borra cada noche los
  eventos con más de 7 días).
- **Sincronización:** la GitHub Action `eventos-sync`
  (`.github/workflows/eventos-sync.yml`) se ejecuta cada 30 minutos y
  bajo demanda. Ejecuta `scripts/export-airtable-events.mjs`, que lee
  Airtable con el token guardado en los secretos del repo
  (`AIRTABLE_TOKEN`), genera `api/events.json` con el contrato
  `{ records, meta }` y descarga a `images/events/` las imágenes que
  falten, convertidas a webp. Si hay cambios, los commitea.
- **Front:** `index.html` + `css/eventos.css`, sin build. Lee
  `api/events.json` y filtra en el navegador.
- **Seguridad:** ningún secreto vive en el código. El script falla
  cerrado: si la lectura de Airtable es incompleta o el número de
  eventos cae más de un 20%, no publica nada.

## Historia

Hasta noviembre de 2026 el sitio vivía en OpenAI Sites (Worker + D1
alimentado por un Apps Script desde Google Sheets). El 18-nov-2026 se
recreó como sitio estático en este repositorio, con Airtable como
fuente única.
