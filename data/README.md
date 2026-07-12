# Eventos: Airtable

La página pública de `eventos.ajra.es` carga los eventos directamente desde la tabla `eventos` de Airtable al abrirse.

`events.json` y el script de exportación se conservan solo como respaldo histórico de la migración temporal a JSON; no alimentan la web actual.

## Export con imagenes

El script `scripts/export-airtable-events.mjs` puede leer Airtable y copiar los adjuntos de `Imagen` a Cloudinary antes de escribir `events.json`.

Variables necesarias:

- `AIRTABLE_TOKEN`
- `CLOUDINARY_URL`

Tambien se pueden usar las variables separadas `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` y `CLOUDINARY_API_SECRET`.

Uso:

```sh
AIRTABLE_TOKEN="..." \
CLOUDINARY_URL="cloudinary://..." \
node scripts/export-airtable-events.mjs
```

Si faltan las variables de Cloudinary, el script exporta los eventos con `images/logo.webp` como placeholder.
