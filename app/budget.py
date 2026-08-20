from collections import defaultdict


class BudgetTracker:
    def __init__(self, monthly_limit_usd: float = 5.0):
        self.spend: dict[str, float] = defaultdict(float)
        self.monthly_limit_usd = monthly_limit_usd

    def add_spend(self, user_id: str, amount: float):
        self.spend[user_id] += amount

    def is_near_limit(self, user_id: str, threshold: float = 0.8) -> bool:
        return self.spend[user_id] >= self.monthly_limit_usd * threshold

    def get_spend(self, user_id: str) -> float:
        return self.spend[user_id]
