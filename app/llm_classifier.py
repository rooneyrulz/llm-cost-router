import sys
from pathlib import Path

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Tier
from app.groq_client import client
from app.logging_config import get_logger

logger = get_logger("LLM Classifier")


# --- Output schema ---------------------------------------------------------
class ClassificationResult(BaseModel):
    tier: str = Field(description="One of: cheap, standard, premium")
    confidence: float = Field(
        description="0.0 to 1.0 confidence in this classification"
    )
    reasoning: str = Field(
        description="One short sentence explaining the classification"
    )


CLASSIFICATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "classification_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["cheap", "standard", "premium"],
                },
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["tier", "confidence", "reasoning"],
            "additionalProperties": False,
        },
    },
}

CLASSIFIER_SYSTEM_PROMPT = """You classify queries by how complex a response requires.

CHEAP: simple factual lookups, definitions, short translations, basic formatting.
STANDARD: everyday reasoning, summarization, moderate-length coding, explanations.
PREMIUM: multi-step reasoning, complex/multi-file coding or debugging, architecture
design, long-form synthesis, or anything where a wrong answer is costly.

Classify conservatively: if unsure between two tiers, pick the higher one."""


# --- Caching -----------------------------------------------------------
# Avoid paying the classification cost twice for the same (or near-identical)
# query. A simple normalized-hash LRU cache covers exact repeats cheaply;
# swap for embedding-similarity caching if you need to catch paraphrases too.

def _classify_query(query: str) -> ClassificationResult:
    return _classify_llm(query)


def _classify_llm(query: str) -> ClassificationResult:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",  # cheap model doing the classification itself
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        reasoning_effort="low",
        tool_choice="none",
        response_format=CLASSIFICATION_SCHEMA,
    )
    raw = response.choices[0].message.content
    return ClassificationResult.model_validate_json(raw)


def classify(query: str) -> Tier:
    """Classify a query into a routing tier using an LLM with a strict
    JSON schema. Falls back to a safe default on any failure so a classifier
    outage never takes the whole router down."""
    try:
        result = _classify_query(query)
        logger.info(
            "query classified",
            query=query,
            tier=result.tier,
            confidence=f"{result.confidence:.2f}",
            reasoning=result.reasoning,
        )
        return Tier(result.tier)
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "query classification failed",
            error=str(e),
            query=query,
            defaulting_to_tier=Tier.STANDARD.value,
        )
        return Tier.STANDARD
