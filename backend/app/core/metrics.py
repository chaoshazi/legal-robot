"""Custom Prometheus metrics for the legal bot."""

from prometheus_client import Counter

legal_bot_requests_total = Counter(
    "legal_bot_requests_total",
    "Total number of legal bot requests",
    ["endpoint"],
)

legal_bot_errors_total = Counter(
    "legal_bot_errors_total",
    "Total number of legal bot errors",
    ["endpoint", "error_type"],
)

legal_bot_tool_calls_total = Counter(
    "legal_bot_tool_calls_total",
    "Total number of tool calls made by the agent",
    ["tool_name"],
)

legal_bot_cache_hits_total = Counter(
    "legal_bot_cache_hits_total",
    "Total number of semantic cache hits",
    [],
)

legal_bot_cache_misses_total = Counter(
    "legal_bot_cache_misses_total",
    "Total number of semantic cache misses",
    [],
)

legal_bot_cache_size = Counter(
    "legal_bot_cache_size",
    "Current number of entries in the semantic cache",
    [],
)

legal_bot_audit_log_cleanup_total = Counter(
    "legal_bot_audit_log_cleanup_total",
    "Total number of audit log cleanup runs",
    ["status"],
)

legal_bot_llm_tokens_total = Counter(
    "legal_bot_llm_tokens_total",
    "Total LLM token usage by model and type",
    ["model", "type"],
)
