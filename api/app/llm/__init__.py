"""Async LLM client -- port of web/src/server/llm/."""

from app.llm.client import (
    GeminiLLMProvider,
    LLMAuthError,
    LLMConfigurationError,
    LLMJsonParseError,
    LLMNetworkError,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    create_default_provider,
    generate_structured,
    read_api_key,
)
from app.llm.cost_logger import (
    LLMCostLogEntry,
    LLMCostLogger,
    create_cost_log_entry,
    default_cost_log_path,
    estimate_token_count,
    log_cost,
)
from app.llm.json_repair import (
    JsonRepairError,
    extract_json_candidate,
    parse_json_with_repair,
    repair_json,
)
from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    RetryResult,
    is_transient_network_error,
    with_retry,
)

__all__ = [
    # client
    "GeminiLLMProvider",
    "LLMAuthError",
    "LLMConfigurationError",
    "LLMJsonParseError",
    "LLMNetworkError",
    "LLMProvider",
    "LLMProviderError",
    "LLMTimeoutError",
    "create_default_provider",
    "generate_structured",
    "read_api_key",
    # cost_logger
    "LLMCostLogEntry",
    "LLMCostLogger",
    "create_cost_log_entry",
    "default_cost_log_path",
    "estimate_token_count",
    "log_cost",
    # json_repair
    "JsonRepairError",
    "extract_json_candidate",
    "parse_json_with_repair",
    "repair_json",
    # retry
    "RetryExhaustedError",
    "RetryOptions",
    "RetryResult",
    "is_transient_network_error",
    "with_retry",
]
