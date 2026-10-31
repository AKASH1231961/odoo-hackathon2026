import json
import redis
from app.isse.config import settings

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


class OnlineFeatureStore:
    """Minimal Redis-backed online feature store.
    Swap for Feast in production for online/offline parity and point-in-time joins.
    """

    @staticmethod
    def set_features(entity_key: str, features: dict, ttl_sec: int = 3600):
        _redis.setex(f"isse:features:{entity_key}", ttl_sec, json.dumps(features))

    @staticmethod
    def get_features(entity_key: str) -> dict:
        raw = _redis.get(f"isse:features:{entity_key}")
        return json.loads(raw) if raw else {}

    @staticmethod
    def incr_counter(entity_key: str, field: str, window_sec: int) -> int:
        key = f"isse:feat:counter:{entity_key}:{field}"
        pipe = _redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_sec)
        count, _ = pipe.execute()
        return count