import time
from threading import Lock
import redis
from app.core.config import settings

_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
_local = {}
_lock = Lock()


def _local_failures(key: str, add: int = 0) -> int:
    """Per-process fallback so login stays protected while Redis is down."""
    now = time.time()
    with _lock:
        count, expires = _local.get(key, (0, now + settings.LOGIN_LOCKOUT_SECONDS))
        if expires < now:
            count, expires = 0, now + settings.LOGIN_LOCKOUT_SECONDS
        count += add
        _local[key] = (count, expires)
        return count


def is_locked(key: str) -> bool:
    try:
        return int(_client.get(f"login:{key}") or 0) >= settings.LOGIN_MAX_FAILURES
    except redis.RedisError:
        return _local_failures(key) >= settings.LOGIN_MAX_FAILURES


def record_failure(key: str) -> None:
    try:
        name = f"login:{key}"
        pipe = _client.pipeline()
        pipe.incr(name)
        pipe.expire(name, settings.LOGIN_LOCKOUT_SECONDS)
        pipe.execute()
    except redis.RedisError:
        _local_failures(key, add=1)


def clear(key: str) -> None:
    try:
        _client.delete(f"login:{key}")
    except redis.RedisError:
        pass
    with _lock:
        _local.pop(key, None)
