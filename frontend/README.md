# Sentiment Pulse · web

The Next.js frontend for Sentiment Pulse: analyze single posts, upload CSV batches, and
explore stored predictions on a live dashboard.

## Run it

```bash
npm install
npm run dev            # http://localhost:3000, expects the API on http://localhost:8000
```

| Script              | What it does                         |
| ------------------- | ------------------------------------ |
| `npm run dev`       | Development server                   |
| `npm run build`     | Production build (standalone output) |
| `npm start`         | Serve a production build locally     |
| `npm run lint`      | ESLint                               |
| `npm run typecheck` | TypeScript, no emit                  |
| `npm test`          | Vitest + Testing Library             |
| `npm run format`    | Prettier (with Tailwind class order) |

## Talking to the API

The browser only calls same-origin paths (`/api/*`, `/health`). `next.config.ts` rewrites
them to `API_INTERNAL_URL` (default `http://localhost:8000`), so the API needs no CORS
setup. The value is read **at build time**: pass it as a Docker build arg, or set it as an
environment variable on Vercel. See `.env.example`.

## Structure

```
app/                  routes; each page.tsx is a small server component rendering a client view
components/
  analyze/ dashboard/ history/ batch/ model/    one folder per page
  charts/             Recharts donut and stacked bars
  sentiment/          sentiment, cache and probability displays shared by every page
  filters/            URL-synced filter bar (Dashboard + History)
  feedback/           empty, error and loading states
  common/             small shared pieces (stat card, table card, relative time, ...)
  layout/             sidebar, top bar, status pill, theme toggle
  ui/                 shadcn/ui primitives
hooks/                URL state, current time, platform detection
lib/
  api.ts              typed fetch wrapper + ApiError
  types.ts            the API contract as TypeScript types
  queries.ts          TanStack Query keys and options
  sentiment.ts        colours, icons and labels for each sentiment
  filters.ts          filters <-> URL <-> API params
  format.ts csv.ts highlight.ts errors.ts
__tests__/            unit and component tests
```

## Notes

- **Sentiment colours** are defined once as CSS variables (`app/globals.css`) and mapped to
  labels and icons in `lib/sentiment.ts`. A sentiment is never shown by colour alone.
- **Every data view** has a skeleton, an empty state with a next step, and an error state
  with the API's message, request ID and a Retry button.
- **Filters live in the URL**, so a filtered dashboard or history page can be shared.

## Docker

```bash
docker build -t sentiment-pulse-web --build-arg API_INTERNAL_URL=http://api:8000 .
docker run -p 3000:3000 sentiment-pulse-web
```
