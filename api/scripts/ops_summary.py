from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


async def _main() -> int:
    from app.ops.summary import build_ops_summary

    parser = argparse.ArgumentParser(description="Summarize local ops JSONL logs.")
    parser.add_argument("--metrics", type=Path, default=None, help="Metrics JSONL path.")
    parser.add_argument("--costs", type=Path, default=None, help="LLM cost JSONL path.")
    args = parser.parse_args()

    print(
        json.dumps(
            await build_ops_summary(metric_path=args.metrics, cost_path=args.costs),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
