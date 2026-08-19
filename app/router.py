from app.config import MODEL_REGISTRY, Tier, ModelConfig
from app.budget import BudgetTracker
from app.health import HealthChecker

class ModelRouter:
    def __init__(self, budget_tracker: BudgetTracker, health_checker: HealthChecker):
        self.budget_tracker = budget_tracker
        self.health_checker = health_checker

    def pick_model(self, tier: Tier, user_id: str) -> tuple[ModelConfig, str]:
        """Returns (config, reason) so you can log why a decision was made."""

        if self.budget_tracker.is_near_limit(user_id):
            tier = Tier.CHEAP
            reason = "budget_downgrade"
        else:
            reason = "classifier"

        cfg = MODEL_REGISTRY[tier]

        if not self.health_checker.is_healthy(cfg.name):
            # fall back one tier down; cheap has nowhere further to fall
            fallback_tier = Tier.CHEAP if tier != Tier.CHEAP else None
            if fallback_tier is None:
                raise RuntimeError("No healthy models available")
            cfg = MODEL_REGISTRY[fallback_tier]
            reason = "health_fallback"

        return cfg, reason