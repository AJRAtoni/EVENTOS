# Repository Guidelines

## Project Structure & Module Organization

This repository is a small static site for `eventos.ajra.es`.

- `index.html` contains the page markup and inline JavaScript for fetching and rendering Airtable events.
- `css/eventos.css` contains all site styling and responsive rules.
- `images/` stores brand and favicon assets used by the page.
- `CNAME` configures the custom GitHub Pages domain.

Keep new files close to their purpose. Add styles to `css/eventos.css`, assets under `images/`, and avoid introducing a build system unless needed.

## Build, Test, and Development Commands

There is no package manager or build step. Serve the site locally with any static server:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

For quick static checks:

```sh
git status --short
```

Use browser developer tools to verify Airtable requests, responsive layout, console errors, and calendar downloads.

## Coding Style & Naming Conventions

- Use plain HTML, CSS, and browser JavaScript.
- Match the existing indentation: 4 spaces in `index.html`, 2 spaces in `css/eventos.css`.
- Keep CSS class names descriptive and consistent with existing Spanish names, such as `.botonesfiltro` and `.buscador`.
- Prefer small, focused JavaScript functions for rendering, filtering, searching, and downloads.
- Keep user-facing copy in Spanish unless the feature specifically requires another language.
- Do not add unused libraries. External dependencies currently load from CDN in `index.html`.

## Testing Guidelines

No automated test framework is configured. Before opening a pull request, manually verify:

- the page loads without console errors;
- event cards render from Airtable;
- category filters and search work together;
- the calendar `.ics` download button creates a valid event;
- the layout works on mobile and desktop widths.

Name future test files after the behavior under test, for example `events-filter.test.js`, and document the command here when a runner is added.

## Commit & Pull Request Guidelines

Recent history uses short, imperative messages, sometimes with conventional prefixes such as `fix:` and `chore:`. Follow that style:

- `fix: load all Airtable event pages`
- `Adjust hero logo size and shape`

Pull requests should include a short summary, testing notes, linked issue if applicable, and screenshots for visible UI changes.

## Security & Configuration Tips

Do not commit new private tokens or secrets. The current Airtable access is client-side, so treat all values in `index.html` as public and avoid expanding permissions beyond read-only needs.
