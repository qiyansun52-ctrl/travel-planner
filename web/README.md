# Travel Planner Web MVP

Session-based single-city travel planning MVP built with Next.js App Router.

## Run

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Test

```bash
npm run test
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```

## MVP Flow

1. Submit hard constraints on `/`.
2. Review fixture-backed discovery ideas at `/discovery/[sessionId]`.
3. Select cards and complete stay/transport preferences.
4. Review the itinerary at `/trips/[sessionId]`.
5. Use the adjustment panel for partial replanning.

## Notes

See `web/docs/mvp-launch-checklist.md` for environment variables, fallback behavior, and current MVP limits.

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
