import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.classifier import classify
from app.config import Tier

with open("eval/eval_set.json") as f:
    cases = json.load(f)

correct = 0
for case in cases:
    predicted = classify(case["query"]).value
    ok = predicted == case["expected_tier"]
    correct += ok
    print(
        f"{'✓' if ok else '✗'} expected={case['expected_tier']} got={predicted} | {case['query'][:50]}"
    )

print(f"\nAccuracy: {correct}/{len(cases)} = {correct / len(cases):.0%}")
