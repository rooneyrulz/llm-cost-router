import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from app.budget import BudgetTracker
from app.cost_tracker import record_request
from app.groq_client import call_model
from app.health import HealthChecker
from app.llm_classifier import classify
from app.logging_config import (
    bind_request_context,
    clear_request_context,
    get_logger,
    setup_logging,
)
from app.router import ModelRouter

SKIP_LOG_PATHS = {"/health", "/metrics"}

setup_logging()
logger = get_logger("router")

app = FastAPI(title="Cost-Optimized Model Router")

budget_tracker = BudgetTracker(monthly_limit_usd=5.0)
health_checker = HealthChecker()
router = ModelRouter(budget_tracker, health_checker)


class ChatRequest(BaseModel):
    query: str
    user_id: str = "test-user"


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.monotonic()
    bind_request_context(request_id=request_id)

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
        )
        raise
    finally:
        clear_request_context()

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    if request.url.path not in SKIP_LOG_PATHS:
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    response.headers["X-Request-ID"] = request_id
    return response


@app.post("/chat")
async def chat(req: ChatRequest):
    tier = classify(req.query)
    cfg, reason = router.pick_model(tier, req.user_id)

    start = time.monotonic()
    try:
        response = call_model(cfg.name, cfg.reasoning_effort, req.query)
        health_checker.record_success(cfg.name)
    except Exception as e:
        latency = time.monotonic() - start
        health_checker.record_failure(cfg.name)
        logger.exception(
            "model_call_failed",
            model=cfg.name,
            query=req.query,
            user_id=req.user_id,
            tier=tier.value,
            reason=reason,
            error=str(e),
            latency_s=round(latency, 2),
        )
        raise HTTPException(status_code=502, detail="Model provider error")

    latency = time.monotonic() - start
    usage = response.usage
    cost = record_request(
        cfg, tier, req.user_id, usage.prompt_tokens, usage.completion_tokens, latency
    )
    budget_tracker.add_spend(req.user_id, cost)

    logger.info(
        "chat_routed",
        tier=tier.value,
        model=cfg.name,
        reason=reason,
        cost_usd=round(cost, 6),
        latency_s=round(latency, 2),
        user_id=req.user_id,
        query=req.query,
        answer=response.choices[0].message.content,
        total_user_spend_usd=round(budget_tracker.get_spend(req.user_id), 6),
    )

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

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["logs/*", "logs/**/*"], log_level="info")
