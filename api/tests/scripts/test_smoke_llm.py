from __future__ import annotations

import pytest

import scripts.smoke_llm as smoke_llm


@pytest.mark.asyncio
async def test_smoke_llm_fails_when_gemini_key_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import app.config as app_config

    monkeypatch.setattr(app_config, "load_environment", lambda: False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)

    result = await smoke_llm.main()

    assert result == 1
    assert "failed: no GEMINI_API_KEY" in capsys.readouterr().err
