from __future__ import annotations

from datetime import datetime, timezone


_PRICES = {
    "gpt-5.3-codex": {"in": 1.75, "out": 14.00},
    "gpt-5.1-codex": {"in": 1.25, "out": 10.00},
    "gpt-5.1-codex-mini": {"in": 0.25, "out": 2.00},
    "gpt-5": {"in": 1.25, "out": 10.00},
    "gpt-5-mini": {"in": 0.25, "out": 2.00},
    "gpt-5-nano": {"in": 0.05, "out": 0.40},
    "gpt-4.1": {"in": 2.00, "out": 8.00},
    "gpt-4.1-mini": {"in": 0.40, "out": 1.60},
    "gpt-4.1-nano": {"in": 0.10, "out": 0.40},
    "gpt-4o": {"in": 2.50, "out": 10.00},
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-5.4": {"in": 1.25, "out": 10.00},
    "gpt-5.4-mini": {"in": 0.30, "out": 2.50},
}
_FALLBACK = {"in": 2.00, "out": 8.00}


def call_start_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _price(model: str) -> dict[str, float]:
    key = (model or "").strip().lower()
    return _PRICES.get(key, _FALLBACK)


def log_token_usage(fn_name: str, model: str, result, query_start: str = None, call_start: str = None) -> None:
    usage = None
    response_model = model

    if hasattr(result, "_raw_response"):
        raw = result._raw_response
        if getattr(raw, "usage", None):
            usage = raw.usage
        if getattr(raw, "model", None):
            response_model = raw.model
    elif getattr(result, "usage", None):
        usage = result.usage
        if getattr(result, "model", None):
            response_model = result.model

    if not usage:
        return

    p = _price(response_model)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
    cost = (prompt_tokens * p["in"] + completion_tokens * p["out"]) / 1_000_000
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(
        (
            f"\n===========================================\n"
            f"|| [TOKEN USAGE]\n"
            f"|| function:           {fn_name}\n"
            f"|| time:               {now}\n"
            f"|| model:              {response_model}\n"
            f"|| prompt_tokens:      {prompt_tokens}\n"
            f"|| completion_tokens:  {completion_tokens}\n"
            f"|| total_tokens:       {total_tokens}\n"
            f"|| call_start:         {call_start or ''}\n"
            f"|| query_start:        {query_start or ''}\n"
            f"|| cost:               ${cost:.6f}\n"
            f"==========================================="
        ),
        flush=True,
    )
