import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import MODEL_REGISTRY, Tier

CODE_PATTERN = re.compile(r"```|def |class |function\(|import |SELECT |async ")
REASONING_KEYWORDS = {
    "analyze",
    "plan",
    "compare",
    "why",
    "explain",
    "design",
    "architect",
    "debug",
    "refactor",
    "optimize",
    "prove",
    "derive",
    "code",
    "build",
    "generate",
    "create",
    "make",
    "write",
}
SIMPLE_KEYWORDS = {
    "what is",
    "define",
    "translate",
    "capital of",
    "spell",
    "convert",
    "summarise",
    "summarize",
    "tell me",
}


def classify(query: str) -> Tier:
    q = query.lower()
    word_count = len(query.split())

    if any(k in q for k in SIMPLE_KEYWORDS) and word_count < 20:
        return Tier.CHEAP

    if CODE_PATTERN.search(query) or any(k in q for k in REASONING_KEYWORDS):
        return Tier.PREMIUM if word_count > 60 else Tier.STANDARD

    if word_count > 150:
        return Tier.PREMIUM
    if word_count > 30:
        return Tier.STANDARD

    return Tier.CHEAP


# For testing purposes:
if __name__ == "__main__":
    user_text = "can you code and build a website for me?"
    tier = classify(user_text)
    cost_model = MODEL_REGISTRY[tier]
    print(f"User text length: {len(user_text.split())} words")
    print(f"Routed to tier: {tier.value}")
    print(f"Model: {cost_model.name}")
    print(f"Reasoning: {cost_model.reasoning_effort}")
