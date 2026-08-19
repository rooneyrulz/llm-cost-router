from prometheus_client import Counter, Histogram

REQUEST_COST = Counter(
    "llm_request_cost_usd", "Cost per request in USD", ["model", "tier", "user_id"]
)
REQUEST_TOKENS = Counter(
    "llm_request_tokens", "Tokens used", ["model", "tier", "direction"]
)
REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds", "Latency per request", ["model", "tier"]
)

def record_request(cfg, tier, user_id, input_tokens, output_tokens, latency_s) -> float:
    cost = (input_tokens / 1_000_000 * cfg.input_cost_per_1m +
            output_tokens / 1_000_000 * cfg.output_cost_per_1m)

    REQUEST_COST.labels(model=cfg.name, tier=tier.value, user_id=user_id).inc(cost)
    REQUEST_TOKENS.labels(model=cfg.name, tier=tier.value, direction="input").inc(input_tokens)
    REQUEST_TOKENS.labels(model=cfg.name, tier=tier.value, direction="output").inc(output_tokens)
    REQUEST_LATENCY.labels(model=cfg.name, tier=tier.value).observe(latency_s)

    return cost