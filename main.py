import time
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.llm_classifier import classify
from app.router import ModelRouter
from app.budget import BudgetTracker
from app.health import HealthChecker
from app.cost_tracker import record_request
from app.groq_client import call_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("router")

app = FastAPI(title="Cost-Optimized Model Router")

budget_tracker = BudgetTracker(monthly_limit_usd=5.0)
health_checker = HealthChecker()
router = ModelRouter(budget_tracker, health_checker)

class ChatRequest(BaseModel):
    query: str
    user_id: str = "test-user"

@app.post("/chat")
async def chat(req: ChatRequest):
    tier = classify(req.query)
    cfg, reason = router.pick_model(tier, req.user_id)

    start = time.monotonic()
    try:
        response = call_model(cfg.name, cfg.reasoning_effort, req.query)
        health_checker.record_success(cfg.name)
    except Exception as e:
        health_checker.record_failure(cfg.name)
        logger.error(f"Model call failed: {e}")
        raise HTTPException(status_code=502, detail="Model provider error")

    latency = time.monotonic() - start
    usage = response.usage
    cost = record_request(
        cfg, tier, req.user_id,
        usage.prompt_tokens, usage.completion_tokens, latency
    )
    budget_tracker.add_spend(req.user_id, cost)

    logger.info(f"tier={tier.value} model={cfg.name} reason={reason} "
                f"cost=${cost:.6f} latency={latency:.2f}s")

    return {
        "answer": response.choices[0].message.content,
        "tier": tier.value,
        "model": cfg.name,
        "routing_reason": reason,
        "cost_usd": round(cost, 6),
        "latency_s": round(latency, 2),
        "total_user_spend_usd": round(budget_tracker.get_spend(req.user_id), 6),
    }

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    