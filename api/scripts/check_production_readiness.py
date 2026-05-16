from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from app.config import get_settings
    from app.ops.readiness import assert_production_ready, redacted_env_status

    settings = get_settings()
    assert_production_ready(settings)
    print(json.dumps(redacted_env_status(settings), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
