import redis
import numpy as np
from app.isse.config import settings

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
SLOTS = [(dow, hour) for dow in range(7) for hour in range(24)]


def _slot_key(dow: int, hour: int) -> str:
    return f"isse:dunning:bandit:{dow}:{hour}"


def record_outcome(dow: int, hour: int, success: bool):
    key = _slot_key(dow, hour)
    _redis.hsetnx(key, "alpha", 1)
    _redis.hsetnx(key, "beta", 1)
    _redis.hincrby(key, "alpha" if success else "beta", 1)


def recommend_retry_slot(candidate_slots: list[tuple[int, int]] | None = None) -> tuple[int, int]:
    """Thompson sampling across candidate (day_of_week, hour) retry slots."""
    candidates = candidate_slots or SLOTS
    best_slot, best_sample = None, -1.0

    for dow, hour in candidates:
        stats = _redis.hgetall(_slot_key(dow, hour))
        alpha = float(stats.get("alpha", 1))
        beta = float(stats.get("beta", 1))
        sample = np.random.beta(alpha, beta)
        if sample > best_sample:
            best_sample, best_slot = sample, (dow, hour)

    return best_slot