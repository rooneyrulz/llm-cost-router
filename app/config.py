from dataclasses import dataclass
from enum import Enum

class Tier(str, Enum):
    CHEAP = "cheap"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class ModelConfig:
    name: str                  # Groq model ID
    tier: Tier
    reasoning_effort: str | None  # low / medium / high / None
    input_cost_per_1m: float   # USD, from console.groq.com/docs/models
    output_cost_per_1m: float
    max_context: int


# Prices as of Aug 2026 — reverify at console.groq.com/docs/models before trusting for real spend tracking.
MODEL_REGISTRY: dict[Tier, ModelConfig] = {
    Tier.CHEAP: ModelConfig(
        name="openai/gpt-oss-20b",
        tier=Tier.CHEAP,
        reasoning_effort="low",
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        max_context=131_072,
    ),
    Tier.STANDARD: ModelConfig(
        name="openai/gpt-oss-120b",
        tier=Tier.STANDARD,
        reasoning_effort="medium",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_context=131_072,
    ),
    Tier.PREMIUM: ModelConfig(
        name="openai/gpt-oss-120b",
        tier=Tier.PREMIUM,
        reasoning_effort="high",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_context=131_072,
    ),
}