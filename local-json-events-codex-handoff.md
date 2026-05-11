# Eventos by AJRA: migración a JSON local — handoff para Codex

> **Para Codex:** implementa este plan en el repo `/Users/ajra/Documents/GitHub/EVENTOS`. Mantén el sitio estático, sin build system y sin dependencias nuevas salvo que sea imprescindible.

**Goal:** Sustituir la carga pública desde Airtable por un JSON local/estático para que `eventos.ajra.es` cargue más rápido, no exponga tokens y pueda servir como fuente central para `marvel.ajra.es` y `dc.ajra.es`.

**Architecture:** El repo `EVENTOS` publicará un archivo `data/events.json` en GitHub Pages. `index.html` leerá ese JSON con `fetch`, normalizará eventos y renderizará la UI existente. En fase 1 el JSON se mantiene manualmente/exportado; en fase 2 Airtable puede quedarse como CMS privado y exportar automáticamente a este JSON.

**Tech Stack:** HTML estático, CSS existente en `css/eventos.css`, JavaScript vanilla inline en `index.html`, GitHub Pages.

---

## Contexto recuperado de la sesión anterior

Sesión encontrada: `20260510_105842_e11c1c48`, WhatsApp, 2026-05-10 10:58.

Decisiones de aquella conversación:

- `eventos.ajra.es` actualmente carga HTML rápido, pero se frena por el fetch client-side a Airtable.
- El frontend tiene un Airtable PAT expuesto. Debe eliminarse del código público y rotarse en Airtable.
- Se decidió migrar a JSON local/estático.
- Airtable puede seguir existiendo como CMS privado, pero no debe ser llamado desde el navegador público.
- Arquitectura elegida: `eventos.ajra.es/data/events.json` como fuente central compartida.
- `marvel.ajra.es` y `dc.ajra.es` podrán consumir ese JSON central y filtrar localmente.
- Branding: mantener “Eventos by AJRA”, no independizar todavía la marca.
- Fase 2 opcional: mover datos a `data.ajra.es` si el proyecto crece.

Estado actual del repo:

- Repo local: `/Users/ajra/Documents/GitHub/EVENTOS`
- Remoto: `https://github.com/AJRAtoni/EVENTOS.git`
- Dominio GitHub Pages: `eventos.ajra.es` vía `CNAME`.
- Archivos principales:
  - `index.html`: markup y JS inline que ahora fetches Airtable.
  - `css/eventos.css`: estilos.
  - `images/`: assets.
  - `AGENTS.md`: guía del repo.
- No hay package manager ni build step.
- Dev server recomendado:
  ```bash
  cd /Users/ajra/Documents/GitHub/EVENTOS
  python3 -m http.server 8000
  ```

Importante: no copies, pegues ni documentes el valor del PAT actual. Solo elimínalo del frontend y avisa a AJRA de que debe rotarlo.

---

## Requisitos funcionales

1. `eventos.ajra.es` debe cargar eventos desde `data/events.json`.
2. El JSON debe incluir datos suficientes para:
   - listar eventos futuros;
   - filtrar por categorías actuales de la web;
   - buscar por título/descripción;
   - generar `.ics`;
   - exponer `sites` para decidir en qué web aparece cada evento;
   - exponer `brands` para filtrar por Marvel/DC/etc. en otros sitios.
3. Mantener la UI actual siempre que sea posible.
4. No introducir build system.
5. No usar Airtable desde el navegador público.
6. Evitar romper la descarga `.ics`.
7. Añadir fallback útil si el JSON no carga o está vacío.

---

## Schema recomendado para `data/events.json`

Crear `data/events.json` con este formato:

```json
{
  "version": 1,
  "updatedAt": "2026-05-11T00:00:00-04:00",
  "source": "manual-export-from-airtable",
  "events": [
    {
      "id": "evt-example-001",
      "title": "Ejemplo de evento",
      "description": "Descripción corta del evento.",
      "date": "2026-06-15",
      "category": "cineytv",
      "image": "images/eventos/eventos.webp",
      "url": "https://example.com",
      "status": "published",
      "sites": ["eventos", "marvel"],
      "brands": ["marvel"],
      "tags": ["cine", "estreno"]
    }
  ]
}
```

Notas de schema:

- `date`: usar `YYYY-MM-DD` para eventos all-day. Evita problemas de timezone.
- `category`: slug lowercase usado por los filtros actuales:
  - `cineytv`
  - `curiosidades`
  - `deportes`
  - `festividades`
  - `tecnologia`
  - `videojuegos`
- `status`: solo renderizar `published`.
- `sites`: array con `eventos`, `marvel`, `dc`. En `EVENTOS`, filtrar por `eventos`.
- `brands`: array opcional para Marvel/DC/franquicias.
- `image`: puede ser ruta local o URL absoluta. Si falta, usar placeholder.
- Mantener compatibilidad defensiva con nombres heredados si aparecen (`titulo`, `descripcion`, `FechaOrden`, etc.), pero el nuevo schema debe ser el preferido.

---

## Task 1: Crear `data/events.json` inicial

**Objective:** Añadir el archivo estático que reemplazará el fetch público a Airtable.

**Files:**
- Create: `data/events.json`

**Step 1:** Crear carpeta y archivo:

```bash
cd /Users/ajra/Documents/GitHub/EVENTOS
mkdir -p data
```

**Step 2:** Crear `data/events.json` con al menos 2-3 eventos de ejemplo futuros usando el schema anterior.

Ejemplo mínimo aceptable:

```json
{
  "version": 1,
  "updatedAt": "2026-05-11T00:00:00-04:00",
  "source": "manual",
  "events": [
    {
      "id": "evt-placeholder-001",
      "title": "Evento de ejemplo",
      "description": "Sustituir por evento real exportado desde Airtable.",
      "date": "2026-12-31",
      "category": "curiosidades",
      "image": "images/eventos/eventos.webp",
      "url": "",
      "status": "published",
      "sites": ["eventos"],
      "brands": [],
      "tags": ["placeholder"]
    }
  ]
}
```

**Step 3:** Validar JSON:

```bash
python3 -m json.tool data/events.json >/tmp/events-json-check.json
```

Expected: exit code 0, sin errores.

---

## Task 2: Reemplazar configuración Airtable por configuración JSON

**Objective:** Eliminar token y config Airtable del frontend público.

**Files:**
- Modify: `index.html`

**Current area:** Dentro del `<script>` final, ahora existe un bloque `CONFIG.AIRTABLE` y una función `fetchAirtableEvents()`.

**Step 1:** Cambiar `CONFIG` a algo así:

```js
const CONFIG = {
    DATA_URL: 'data/events.json',
    SITE_ID: 'eventos'
};
```

**Step 2:** Eliminar por completo:

- `AIRTABLE.TOKEN`
- `AIRTABLE.BASE_ID`
- `AIRTABLE.TABLE_NAME`
- `AIRTABLE.CATEGORY_FIELD`
- cualquier header `Authorization` en `fetch`

**Step 3:** Asegurarse de que el valor del token ya no aparece en `index.html`.

Comando de verificación:

```bash
grep -n "AIRTABLE\|TOKEN\|Authorization\|pat" index.html
```

Expected: no debe aparecer ningún token ni header Authorization. Si aparece la palabra `Airtable` solo en comentarios de migración, mejor eliminarla también para evitar confusión.

---

## Task 3: Añadir normalización de eventos desde JSON

**Objective:** Separar la lectura del JSON de la forma interna que usa la UI.

**Files:**
- Modify: `index.html`

**Step 1:** Añadir helper para parsear fechas locales all-day sin desfase timezone:

```js
const parseEventDate = (dateString) => {
    if (!dateString) return null;
    const [year, month, day] = dateString.split('-').map(Number);
    if (!year || !month || !day) return null;
    return new Date(year, month - 1, day);
};
```

**Step 2:** Añadir helper para normalizar evento:

```js
const normalizeEvent = (event) => {
    const rawDate = event.date || event.FechaOrden;
    const eventDate = parseEventDate(rawDate);

    return {
        id: event.id || crypto.randomUUID?.() || `${event.title || event.titulo}-${rawDate}`,
        titulo: event.title || event.titulo || 'Sin Título',
        eventDate,
        descripcion: event.description || event.descripcion || '',
        imagen: event.image || event.imagen || placeholderimagen,
        categoria: event.category || event.categoria || 'General',
        url: event.url || event.IMDbURL || event.URL || '',
        status: event.status || 'published',
        sites: Array.isArray(event.sites) ? event.sites : ['eventos'],
        brands: Array.isArray(event.brands) ? event.brands : [],
        tags: Array.isArray(event.tags) ? event.tags : []
    };
};
```

Nota: si se prefiere evitar `crypto.randomUUID` por compatibilidad, usar solo fallback string estable.

---

## Task 4: Sustituir `fetchAirtableEvents()` por `fetchJsonEvents()`

**Objective:** Cargar datos desde `data/events.json`, filtrar y renderizar.

**Files:**
- Modify: `index.html`

**Step 1:** Reemplazar la función actual por:

```js
const fetchJsonEvents = async () => {
    try {
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const response = await fetch(CONFIG.DATA_URL, { cache: 'no-store' });

        if (!response.ok) {
            throw new Error(`Error JSON: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        const records = Array.isArray(data.events) ? data.events : [];

        allEvents = records
            .map(normalizeEvent)
            .filter(event =>
                event &&
                event.status === 'published' &&
                Array.isArray(event.sites) &&
                event.sites.includes(CONFIG.SITE_ID) &&
                event.eventDate instanceof Date &&
                !isNaN(event.eventDate.getTime()) &&
                event.eventDate >= today
            )
            .sort((a, b) => a.eventDate - b.eventDate);

        displayEvents(allEvents);
    } catch (error) {
        console.error('Error al cargar eventos desde JSON:', error);
        eventsContainer.innerHTML = `<p style="text-align:center; color: red; width:100%; grid-column: 1 / -1;">Error cargando eventos: ${error.message}</p>`;
    }
};
```

**Step 2:** Cambiar inicialización:

```js
document.addEventListener("DOMContentLoaded", function () {
    fetchJsonEvents();
    document.getElementById("searchInput").addEventListener("input", searchEvents);
});
```

**Step 3:** Confirmar que no queda ninguna llamada a `fetchAirtableEvents()`.

```bash
grep -n "fetchAirtableEvents\|Airtable" index.html
```

Expected: sin resultados.

---

## Task 5: Mantener filtros y búsqueda funcionando

**Objective:** Confirmar que la lógica actual sigue funcionando con los campos normalizados.

**Files:**
- Modify only if needed: `index.html`

**Checks:**

- `filterEvents('todos')` muestra todos los eventos publicados futuros del sitio `eventos`.
- `filterEvents('cineytv')` filtra por `category: "cineytv"`.
- `searchEvents()` busca en `titulo` y `descripcion`.

Si se mejora algo, mantener las funciones globales porque los botones usan `onclick="filterEvents('...')"`.

---

## Task 6: Verificar descarga ICS con fechas locales

**Objective:** Evitar que los eventos all-day salten de día por timezone.

**Files:**
- Modify if needed: `index.html`

**Checks manuales:**

1. Crear un evento en `data/events.json` con fecha futura clara, por ejemplo `2026-12-31`.
2. Servir localmente:
   ```bash
   python3 -m http.server 8000
   ```
3. Abrir `http://localhost:8000`.
4. Pulsar el botón de calendario.
5. Abrir el `.ics` descargado y confirmar:
   ```text
   DTSTART;VALUE=DATE:20261231
   ```

---

## Task 7: Probar en local con static server

**Objective:** Validar la migración de punta a punta.

**Files:**
- No nuevos archivos, salvo cambios de tareas previas.

**Command:**

```bash
cd /Users/ajra/Documents/GitHub/EVENTOS
python3 -m http.server 8000
```

**Manual QA en navegador:**

- `http://localhost:8000` carga sin errores en consola.
- Network muestra `GET /data/events.json` 200.
- No hay llamadas a `api.airtable.com`.
- Se renderizan eventos futuros.
- Los filtros de categorías funcionan.
- La búsqueda funciona.
- El botón `.ics` descarga un evento válido.
- Mobile y desktop siguen razonables.

---

## Task 8: Añadir nota operativa para futuros datos

**Objective:** Dejar claro cómo actualizar el JSON sin tocar JS.

**Files:**
- Create: `data/README.md`

Contenido recomendado:

```md
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
```

---

## Task 9: Seguridad y limpieza final

**Objective:** Evitar que queden secretos o dependencias de Airtable en el sitio público.

**Commands:**

```bash
cd /Users/ajra/Documents/GitHub/EVENTOS
grep -RIn "pat\|AIRTABLE\|Airtable\|Authorization\|api.airtable.com" -- index.html data css || true
git diff -- index.html data/events.json data/README.md
```

Expected:

- No hay PAT ni Authorization en código público.
- No hay llamadas a `api.airtable.com`.
- El diff solo contiene la migración planeada.

Nota para AJRA: después de merge/deploy, rotar el PAT de Airtable que estuvo expuesto en frontend.

---

## Acceptance Criteria

- [ ] `index.html` carga `data/events.json`.
- [ ] `index.html` no contiene token Airtable ni config Airtable pública.
- [ ] `data/events.json` existe y valida como JSON.
- [ ] Eventos pasados no se muestran.
- [ ] Eventos con `status` distinto de `published` no se muestran.
- [ ] Eventos que no incluyan `eventos` en `sites` no se muestran en esta web.
- [ ] Filtros por categoría siguen funcionando.
- [ ] Buscador sigue funcionando.
- [ ] `.ics` mantiene fecha correcta.
- [ ] No hay errores de consola en carga local.
- [ ] No hay request a Airtable en Network.

---

## Prompt corto para lanzar Codex

Puedes pegarle esto a Codex:

```text
Trabaja en /Users/ajra/Documents/GitHub/EVENTOS. Sigue el plan docs/plans/2026-05-11-local-json-events-codex-handoff.md. Migra el sitio estático eventos.ajra.es de Airtable público a data/events.json local. No añadas build system. No expongas ni copies tokens. Mantén UI/filtros/buscador/ICS funcionando. Verifica con python3 -m json.tool data/events.json, grep de secretos y prueba local con python3 -m http.server 8000. Al final resume cambios y pruebas.
```

---

## Fase 2 opcional, no implementar ahora

- Script privado de export Airtable → `data/events.json`.
- GitHub Action programada si hay token guardado como secret.
- Separar fuente central en `data.ajra.es` si Marvel/DC crecen.
- Añadir tests JS con runner ligero solo si empieza a haber lógica compleja.
