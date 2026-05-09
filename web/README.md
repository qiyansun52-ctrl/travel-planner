# Travel Planner — Web (UI 层)

Next.js 应用,只负责 UI 和路由壳。所有规划逻辑在 `../api`(Python LangGraph)。

## Run

```bash
cd web
npm install
npm run dev
```

默认打开 `http://localhost:3000`,后端依赖 `../api` 跑在 `http://localhost:8000`。

## Test

```bash
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

## Canonical Flow

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

旧的 `/discover/[destination]`、`/plan/[id]`、Next.js server agents 和 Next.js API routes 是迁移期 legacy surface,最终会被 Python 后端取代。
