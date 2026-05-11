# Travel Planner

> An AI-orchestrated workflow that turns a one-line trip idea into a printable, styled day-by-day itinerary — by chaining Claude with three real-world MCP tools (China rail, maps, lifestyle social).
>
> 用 Claude + MCP 工具链把一句话旅行想法变成一张可打印的精美行程表。

![status](https://img.shields.io/badge/status-prototype-orange)
![stack](https://img.shields.io/badge/AI-Claude%20%2B%20MCP-5A4AE3)
![template](https://img.shields.io/badge/output-HTML%20%2F%20printable-blue)
![license](https://img.shields.io/badge/license-TBD-lightgrey)

---

## Why this exists / 项目动机

Planning a domestic trip in China usually means juggling at least three tabs: **12306** for trains, **Amap (高德)** for routes, and **Xiaohongshu (小红书)** for what locals actually recommend. Each tool answers part of the question. None of them produces something you can hand to a travel companion.

This project is an experiment in using a single AI agent — **Claude with MCP** — to do the cross-tool reasoning for you, and to spit out an artifact you can print or send to a friend.

> 一次国内旅行通常要在 12306、高德、小红书之间反复切换。这个项目把它们交给 Claude 统一编排，最终输出一张可打印的 HTML 行程表。

This repo is intentionally small and prompt-driven. The Next.js web-app version is **specced but not yet built** — see [Roadmap](#roadmap--status).

---

## Highlights

- **AI as the planner, not the form-filler.** A single prompt drives the entire workflow: rail lookup, attraction research, route optimization, itinerary synthesis.
- **Three real MCP tools, not mocks.** Live calls to 高德地图 MCP (routes/POI), 12306 MCP (train tickets), and `xhs-mcp` (Xiaohongshu notes).
- **Print-ready output.** A self-contained HTML template (Tailwind via CDN + Chart.js + Font Awesome) with a timeline, budget doughnut chart, tips card, and A4 print stylesheet.
- **One-file install.** `setup_mcp.sh` installs the only non-trivial dependency (`xhs-mcp`); the other two MCPs are hosted SSE endpoints.
- **Honest scope.** Manual workflow today; designed so the prompt and HTML template can later be wrapped by the Next.js app described in `docs/`.

---

## Tech stack

**AI orchestration**
- Claude (any model that supports MCP — invoked via Claude Code / Claude Desktop)
- Model Context Protocol (MCP) servers:
  - `amap` — Amap (高德地图) — route planning, POI search (hosted SSE)
  - `12306` — China railway ticket lookup via ModelScope (hosted SSE)
  - `xhs-mcp` — Xiaohongshu (小红书) note search (local, stdio)

**Itinerary template** (`travel-template.html`)
- Tailwind CSS (CDN build)
- Chart.js — budget breakdown doughnut chart
- Font Awesome 6 — icons
- Noto Sans SC — CJK typography
- Vanilla JS — scroll-fade animation + print

**Tooling**
- `uv` — installs `xhs-mcp`
- Bash — `setup_mcp.sh`

---

## How it works / 工作原理

```
User prompt (workflow_prompt.md)
        │
        ▼
   ┌─────────┐    1. 12306 MCP  ──►  train options
   │ Claude  │    2. xhs-mcp    ──►  attractions / food / lodging notes
   │ (agent) │    3. Amap MCP   ──►  daily route + travel time
   └────┬────┘
        │
        ▼
   Structured itinerary (text)
        │
        ▼
   Render into travel-template.html  ──►  printable plan
```

The workflow is sequential by design: rail first (so arrival/departure anchor the schedule), local research second (to pick the places worth going), routing last (to make each day geographically sane). The Claude prompt that enforces this order lives in [`workflow_prompt.md`](workflow_prompt.md).

---

## Quick start

**Prereqs:** Claude Code or Claude Desktop with MCP support; `bash`; an Amap web API key; a ModelScope account; a Xiaohongshu account.

```bash
# 1. Clone
git clone <this-repo> travel-planner && cd travel-planner

# 2. Install xhs-mcp (also installs uv if missing)
bash setup_mcp.sh

# 3. Get credentials
#   - Amap key:        https://lbs.amap.com/  →  Console  →  Web service
#   - 12306 SSE URL:   https://modelscope.cn  →  find "12306-mcp"  →  copy your SSE link
#   - xhs cookie:      log into xiaohongshu.com  →  DevTools  →  Network  →  copy Cookie header

# 4. Merge mcp_config.json into ~/.claude/settings.json
#    (replace the YOUR_xxx placeholders first)

# 5. Run the workflow
#    Paste workflow_prompt.md into Claude with [出发城市] / [目的地] / [出发日期] / [天数] filled in
#    Then ask Claude to render the result into travel-template.html
```

> Replacement variables in `workflow_prompt.md`: `[出发城市]` (departure), `[目的地]` (destination), `[出发日期]` (date), `[天数]` (days).

---

## Project structure

```
travel-planner/
├── README.md                 # You are here
├── workflow_prompt.md        # The master prompt — paste into Claude to run a plan
├── mcp_config.json           # MCP server config template (merge into ~/.claude/settings.json)
├── setup_mcp.sh              # Installs uv + xhs-mcp; prints cookie instructions
├── travel-template.html      # Self-contained printable itinerary template
├── .gitignore
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-04-30-travel-planner-web-app-design.md   # Product spec for future web app
        └── plans/
            ├── 2026-04-30-travel-planner-mvp-core.md         # Plan A: split-panel chat MVP
            └── 2026-05-07-single-city-travel-planning-mvp.md # Plan B: four-agent pipeline MVP
```

---

## Roadmap & status / 路线图

**What works today**
- End-to-end manual workflow: prompt → 3 MCPs → text itinerary → rendered HTML.
- Reusable, print-friendly HTML template with budget chart and timeline.
- Reproducible MCP setup via `setup_mcp.sh` + config template.

**What's in `docs/` but not built**
- A Next.js 14 (App Router) + TypeScript + Tailwind web app that wraps this workflow with a real UI: natural-language intake, streamed itinerary, conversational adjustment, exportable HTML.
- Two distinct design takes live side-by-side in `docs/superpowers/plans/`:
  - **Plan A (2026-04-30)** — split-panel chat + itinerary, Claude streaming directly.
  - **Plan B (2026-05-07)** — four-agent pipeline (discovery → stay → transport → planner) with a deterministic validator, anonymous server-side sessions, and provider adapters.
- Live international suppliers (Amadeus flights, Booking hotels) are listed in the spec as later phases.

> 当前是手动驱动的提示词工作流；`docs/` 里是未实现的 Web 应用设计。后续会沿其中一条路线把工作流封装成网页。

**Known limitations**
- No retries or fallbacks if an MCP call fails — Claude just keeps going with partial data.
- Xiaohongshu access depends on a manually-pasted browser cookie, which expires.
- The HTML template is currently filled in by Claude one-shot; it isn't a parameterized renderer.
- Domestic China only (rail-first design); international flights are roadmap.

---

## License

Not yet licensed — TBD. / 暂未授权。
