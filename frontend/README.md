# Frontend

React single-page UI for the Academic Research Assistant. For project setup,
the pipeline and the API contract, see the [root README](../README.md); this
file covers only what is specific to this directory.

## Layout

```
src/
├── main.jsx          React entry point
├── App.jsx           The entire UI: search box, autocomplete, results, exports
├── exportUtils.js    Markdown builder and print-ready HTML for the PDF export
└── index.css         Tailwind import + the two custom font families
e2e/app.spec.js       Playwright tests (run against the live deployment)
public/               favicon.svg, icons.svg — copied to dist as-is
dist/                 Production build. Committed on purpose — see below.
```

`App.jsx` is deliberately one file. The UI is a single screen with no routing,
and the presentational pieces (`PaperCard`, `SourceList`, the skeletons) are
only used by it, so splitting them across files would add imports without
adding clarity.

## Running

```bash
npm install
npm run dev      # http://localhost:5173
```

The API base URL comes from `VITE_API_URL`, and both env files are gitignored:

- `.env` → `http://localhost:8000`. Needed for `npm run dev`, because the Vite
  dev server on `:5173` and the API on `:8000` are different origins.
- `.env.production` → optional. See `.env.production.example`.

If `VITE_API_URL` is unset the app falls back to **same-origin relative
requests**, which is what production actually wants: FastAPI serves this
bundle itself, so `/api/search` resolves against whatever domain the app is
on. That makes the production build portable across domains and means a fresh
clone builds correctly without any env file.

Never put a secret in a `VITE_`-prefixed variable. Vite inlines them into the
client bundle at build time, so anything there ships to every visitor in
plain text. API keys belong in the backend's own `.env`.

Run the backend separately (`uvicorn main:app --reload --port 8000` from the
project root) or point `VITE_API_URL` at the deployed API to work on the UI
alone.

## Styling

Tailwind CSS 4 via `@tailwindcss/vite` — configured in `src/index.css`, not in
a `tailwind.config.js`. Two custom families are declared in the `@theme` block
and loaded from Google Fonts in `index.html`:

- `font-heading` → Inter, for headings and the title
- `font-academic` → Merriweather, for body prose

Because Tailwind 4 generates CSS by scanning the source for class names, the
bundle only contains classes that are actually used. Deleting UI shrinks the
CSS on the next build.

## Build

```bash
npm run build    # outputs to dist/
npm run preview  # serve the build locally
```

**`dist/` is committed to the repository.** FastAPI serves it directly, so the
deployed frontend is whatever was last built and committed — not whatever is
in `src/`. Any change here needs `npm run build` and the rebuilt bundle
committed, or the deploy silently ships the previous version. The asset
filenames are content-hashed, so a rebuild usually renames them; stage the
deletions alongside the additions.

## Tests

```bash
npx playwright test -g "API health|landing page"   # free
npx playwright test                                # includes a live paid search
```

`playwright.config.js` points `baseURL` at the **live Railway deployment**, not
at localhost. Two consequences worth knowing:

- The full suite's search test runs the real pipeline on a cache miss, which
  costs Claude API calls. CI runs only the two free tests.
- A test that asserts on UI text fails between pushing a change and Railway
  finishing the deploy. Re-run the job once the deploy is live.

## Lint

```bash
npm run lint
```

Currently reports pre-existing errors: the presentational components defined
inside `App.jsx` trip `react-hooks/static-components`, and `exportUtils.js` has
one unnecessary regex escape. Neither affects the build.
