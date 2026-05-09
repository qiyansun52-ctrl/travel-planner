# LangGraph MVP Plan 8 Generated Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Pydantic schemas in `api/app/models/schemas.py` the source of truth for frontend TypeScript domain types.

**Architecture:** The API exports a combined JSON Schema document to `api/dist/schema.json`. The web app compiles that schema into `web/src/lib/generated/types.ts` with a local deterministic generator, then `web/src/lib/types.ts` re-exports generated domain types and keeps only frontend-only UI event types. This avoids adding network-installed packages while preserving the Plan 8 contract.

**Tech Stack:** Pydantic v2 `model_json_schema()`, Python script tests with pytest, Node.js ESM script, Next.js TypeScript strict mode.

---

## Context Notes

- `json-schema-to-typescript` is not installed in `web/node_modules`, and the current environment has restricted network access. This plan uses a small local JSON Schema to TypeScript compiler for the Pydantic subset we emit.
- Generated files are committed intentionally:
  - `api/dist/schema.json`
  - `web/src/lib/generated/types.ts`
- `web/src/lib/types.ts` must stop carrying hand-written domain interfaces after generation. It should only re-export generated types and define `PlanningProgressEvent`, which is a route/SSE UI type rather than a Pydantic domain model.

## File Structure

- Create `api/scripts/export_schema.py`: collect every public model from `api/app/models/schemas.py`, merge `$defs`, and write deterministic JSON to `api/dist/schema.json`.
- Create `api/tests/scripts/test_export_schema.py`: verify schema export includes root models and reflects Pydantic changes.
- Create `api/dist/schema.json`: generated JSON Schema artifact.
- Create `web/scripts/generate-types.mjs`: compile `api/dist/schema.json` into TypeScript interfaces and union types.
- Create `web/src/lib/generated/types.ts`: generated TypeScript domain contract.
- Modify `web/src/lib/types.ts`: re-export generated types and keep `PlanningProgressEvent`.
- Modify `web/package.json`: add `gen:types` and `check:types`.
- Create `Makefile`: add root `gen-types` and `check-types` convenience gates.
- Modify `web/README.md`: document generated type workflow.

---

### Task 1: Export Pydantic JSON Schema

**Files:**
- Create: `api/scripts/export_schema.py`
- Create: `api/tests/scripts/test_export_schema.py`
- Create: `api/dist/schema.json`

- [ ] **Step 1: Write failing exporter tests**

Create `api/tests/scripts/test_export_schema.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.export_schema import build_schema_document, export_schema


def test_build_schema_document_includes_frontend_root_models() -> None:
    schema = build_schema_document()

    defs = schema["$defs"]
    assert "PlanningSession" in defs
    assert "HardConstraints" in defs
    assert "Preference" in defs
    assert defs["PlanningSession"]["properties"]["hard_constraints"]["$ref"] == "#/$defs/HardConstraints"


def test_export_schema_writes_deterministic_json(tmp_path: Path) -> None:
    output = tmp_path / "schema.json"

    export_schema(output)

    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["title"] == "TravelPlannerSchemas"
    assert parsed["$defs"]["PlanningSession"]["type"] == "object"
    assert output.read_text(encoding="utf-8").endswith("\n")
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd api
uv run pytest tests/scripts/test_export_schema.py -v
```

Expected: FAIL because `api/scripts/export_schema.py` does not exist.

- [ ] **Step 3: Implement `api/scripts/export_schema.py`**

Use this structure:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel

from app.models.schemas import (
    AdjustmentRequest,
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    ConversationTurn,
    Coordinate,
    DiscoveryCard,
    DiscoveryOutput,
    DiscoveryState,
    FoodSummary,
    HardConstraints,
    IntracityStrategy,
    Itinerary,
    ItineraryDay,
    ItinerarySegment,
    NormalizedPlace,
    NormalizedRoute,
    PlanningSession,
    Preference,
    SampleHotel,
    SourceNote,
    StayOption,
    StayRecommendation,
    TransportLeg,
    TransportRecommendation,
    ValidatorIssue,
)

SchemaModel: TypeAlias = type[BaseModel]
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "dist" / "schema.json"

ROOT_MODELS: tuple[SchemaModel, ...] = (
    Coordinate,
    NormalizedPlace,
    BudgetBand,
    NormalizedRoute,
    DiscoveryCard,
    AreaSummary,
    FoodSummary,
    SourceNote,
    BudgetSummary,
    DiscoveryOutput,
    SampleHotel,
    StayOption,
    StayRecommendation,
    TransportLeg,
    IntracityStrategy,
    TransportRecommendation,
    ValidatorIssue,
    ItinerarySegment,
    ItineraryDay,
    Itinerary,
    HardConstraints,
    Preference,
    AdjustmentRequest,
    ConversationTurn,
    DiscoveryState,
    PlanningSession,
)


def build_schema_document() -> dict[str, object]:
    defs: dict[str, object] = {}
    for model in ROOT_MODELS:
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        nested_defs = schema.pop("$defs", {})
        defs.update(nested_defs)
        defs[model.__name__] = schema

    ordered_defs = {name: defs[name] for name in sorted(defs)}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TravelPlannerSchemas",
        "type": "object",
        "$defs": ordered_defs,
    }


def export_schema(output_path: Path = DEFAULT_OUTPUT) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_schema_document(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    export_schema()
```

- [ ] **Step 4: Generate the schema artifact**

Run:

```bash
cd api
uv run python scripts/export_schema.py
```

Expected: `api/dist/schema.json` exists and includes `$defs.PlanningSession`.

- [ ] **Step 5: Verify exporter tests**

Run:

```bash
cd api
uv run pytest tests/scripts/test_export_schema.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/scripts/export_schema.py api/tests/scripts/test_export_schema.py api/dist/schema.json
git commit -m "feat(api): export pydantic schema for web types"
```

---

### Task 2: Generate TypeScript from Exported Schema

**Files:**
- Create: `web/scripts/generate-types.mjs`
- Create: `web/src/lib/generated/types.ts`
- Modify: `web/package.json`
- Create: `Makefile`

- [ ] **Step 1: Add web generation scripts**

Modify `web/package.json`:

```json
{
  "gen:types": "cd ../api && uv run python scripts/export_schema.py && cd ../web && node scripts/generate-types.mjs",
  "check:types": "npm run gen:types && npm run typecheck"
}
```

Keep existing scripts unchanged.

- [ ] **Step 2: Add root Makefile gates**

Create `Makefile`:

```makefile
.PHONY: gen-types check-types

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types
```

- [ ] **Step 3: Implement `web/scripts/generate-types.mjs`**

The generator must:

```js
import { readFile, writeFile, mkdir } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "../..")
const schemaPath = path.join(repoRoot, "api/dist/schema.json")
const outputPath = path.join(repoRoot, "web/src/lib/generated/types.ts")

const schema = JSON.parse(await readFile(schemaPath, "utf-8"))
const defs = schema.$defs ?? {}
const names = Object.keys(defs).sort()

function refName(ref) {
  return ref.replace("#/$defs/", "")
}

function literal(value) {
  return JSON.stringify(value)
}

function compile(schemaNode) {
  if (!schemaNode || typeof schemaNode !== "object") return "unknown"
  if (schemaNode.$ref) return refName(schemaNode.$ref)
  if (Array.isArray(schemaNode.enum)) return schemaNode.enum.map(literal).join(" | ")
  if (schemaNode.const !== undefined) return literal(schemaNode.const)
  if (Array.isArray(schemaNode.anyOf)) return compileUnion(schemaNode.anyOf)
  if (Array.isArray(schemaNode.oneOf)) return compileUnion(schemaNode.oneOf)

  if (schemaNode.type === "array") return `${compile(schemaNode.items)}[]`
  if (schemaNode.type === "integer" || schemaNode.type === "number") return "number"
  if (schemaNode.type === "string") return "string"
  if (schemaNode.type === "boolean") return "boolean"
  if (schemaNode.type === "null") return "null"
  if (schemaNode.type === "object") {
    if (schemaNode.additionalProperties && typeof schemaNode.additionalProperties === "object") {
      return `Record<string, ${compile(schemaNode.additionalProperties)}>`
    }
    if (schemaNode.additionalProperties === true || !schemaNode.properties) {
      return "Record<string, unknown>"
    }
    return compileInlineObject(schemaNode)
  }
  return "unknown"
}

function compileUnion(items) {
  return Array.from(new Set(items.map(compile))).join(" | ")
}

function propertyName(name) {
  return /^[A-Za-z_$][\w$]*$/.test(name) ? name : JSON.stringify(name)
}

function compileInlineObject(schemaNode) {
  const required = new Set(schemaNode.required ?? [])
  const lines = Object.entries(schemaNode.properties ?? {}).map(([name, prop]) => {
    const optional = required.has(name) ? "" : "?"
    return `  ${propertyName(name)}${optional}: ${compile(prop)}`
  })
  return `{\n${lines.join("\n")}\n}`
}

function emitDefinition(name, schemaNode) {
  if (schemaNode.type === "object" && schemaNode.properties) {
    return `export interface ${name} ${compileInlineObject(schemaNode)}`
  }
  return `export type ${name} = ${compile(schemaNode)}`
}

const content = [
  "/* eslint-disable */",
  "// Generated by web/scripts/generate-types.mjs from api/dist/schema.json.",
  "// Do not edit manually.",
  "",
  ...names.map((name) => emitDefinition(name, defs[name])),
  "",
].join("\n\n")

await mkdir(path.dirname(outputPath), { recursive: true })
await writeFile(outputPath, content, "utf-8")
```

- [ ] **Step 4: Run generation**

Run:

```bash
cd web
npm run gen:types
```

Expected: `web/src/lib/generated/types.ts` exists and exports `PlanningSession`, `HardConstraints`, and `Preference`.

- [ ] **Step 5: Commit**

```bash
git add web/scripts/generate-types.mjs web/src/lib/generated/types.ts web/package.json Makefile
git commit -m "feat(web): generate types from api schema"
```

---

### Task 3: Replace Hand-Written Domain Types

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/README.md`

- [ ] **Step 1: Replace hand-written domain interfaces with generated exports**

Change `web/src/lib/types.ts` to:

```ts
export * from "./generated/types"

export interface PlanningProgressEvent {
  stage: string
  status: "start" | "started" | "finish" | "completed" | "skipped" | "failed" | "error"
  message: string
  payload?: Record<string, unknown>
}
```

- [ ] **Step 2: Document type generation**

Add to `web/README.md`:

```md
## Generated Types

Pydantic models in `../api/app/models/schemas.py` are the source of truth for domain types.

```bash
npm run gen:types
npm run check:types
```

`web/src/lib/types.ts` re-exports generated domain types and only keeps frontend-only UI event types.
```

- [ ] **Step 3: Verify generation is stable**

Run:

```bash
cd web
npm run gen:types
git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
```

Expected: no diff after a second generation run.

- [ ] **Step 4: Verify frontend and backend checks**

Run:

```bash
cd web
npm run check:types
npm run lint
npm run test

cd ../api
uv run pytest tests/scripts/test_export_schema.py -v
uv run ruff check app tests
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/types.ts web/README.md
git commit -m "chore(web): consume generated domain types"
```

---

### Task 4: Full Acceptance

**Files:**
- No planned code changes unless acceptance finds a regression.

- [ ] **Step 1: Run full web checks**

Run:

```bash
cd web
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

Expected: all PASS.

- [ ] **Step 2: Run full API checks**

Run:

```bash
cd api
uv run pytest -v
uv run ruff check app tests
```

Expected: all PASS.

- [ ] **Step 3: Verify schema drift gate**

Run:

```bash
cd web
npm run gen:types
git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
```

Expected: no output.

- [ ] **Step 4: Final repository check**

Run:

```bash
git status --short
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree and no whitespace errors.

If acceptance fixes were needed:

```bash
git add -A
git commit -m "fix(types): complete generated type acceptance"
```

---

## Self-Review

- **Spec coverage:** Exports Pydantic schema, generates TypeScript types, adds `gen:types` and `check:types`, removes hand-written domain interfaces, and verifies type drift.
- **Dependency decision:** Uses a local generator because `json-schema-to-typescript` is unavailable without network install.
- **Placeholder scan:** No red-flag placeholders or undefined follow-up tasks remain.
- **Type consistency:** Existing imports continue using `@/lib/types`; generated exports provide the same domain model names.
