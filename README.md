# eventos.ajra.es

Sitio web estático para publicar y consultar eventos de AJRA.

## Descripción

Este proyecto genera una página simple (sin build ni dependencias de frontend) que:

- carga eventos desde Airtable mediante JavaScript en el navegador;
- muestra tarjetas de eventos con filtros por categoría y buscador;
- permite descargar eventos en formato `.ics` para calendario.

## Estructura del proyecto

- `index.html`: marcado principal e integración JavaScript para obtener y renderizar eventos.
- `css/eventos.css`: estilos globales y reglas responsive.
- `images/`: recursos visuales (logo, favicon, etc.).
- `CNAME`: dominio personalizado para GitHub Pages.
- `scripts/export-airtable-events.mjs`: script auxiliar para exportación de eventos.
- `data/`: datos y documentación de apoyo para eventos.

## Ejecución en local

No hay instalación de paquetes ni compilación. Solo hace falta servir archivos estáticos:

```bash
python3 -m http.server 8000
```

Después abre:

- http://localhost:8000

## Flujo recomendado de revisión manual

Antes de publicar cambios, comprobar en navegador:

1. La página carga sin errores de consola.
2. Se renderizan correctamente las tarjetas de eventos.
3. Filtros y buscador funcionan en conjunto.
4. La descarga `.ics` genera eventos válidos.
5. El diseño responde bien en móvil y escritorio.

## Despliegue

El proyecto está pensado para GitHub Pages con dominio personalizado configurado en `CNAME`.

## Buenas prácticas

- Mantener HTML/CSS/JS simples y sin librerías innecesarias.
- No subir secretos ni tokens privados al repositorio.
- Mantener el texto visible para usuarios en español, salvo necesidad específica.
