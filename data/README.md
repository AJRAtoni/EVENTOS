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
