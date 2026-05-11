# Eventos JSON

`events.json` es la fuente pública de eventos para `eventos.ajra.es`.

- No incluir tokens ni secretos.
- Publicar solo eventos con `status: "published"`.
- Usar fechas `YYYY-MM-DD`.
- Usar `sites` para decidir en qué web aparece cada evento:
  - `eventos`
  - `marvel`
  - `dc`
- Usar `brands` para franquicias/marcas.

En fase 1 se actualiza manualmente o mediante export privado desde Airtable.
En fase 2 se puede automatizar Airtable → JSON en GitHub Actions o un script local.

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
