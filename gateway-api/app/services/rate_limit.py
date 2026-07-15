import logging
import time
from datetime import date

import redis.asyncio as aioredis

log = logging.getLogger(__name__)


class RateLimitService:
    """
    Redis-backed rate limiting and token budget enforcement.

    When Redis is unavailable (e.g. local dev without Docker) all checks
    return "allowed" so the rest of the gateway still works.

    Key schema
    ----------
    rl:key:{api_key_id}:{minute_bucket}   – sliding-window request count (TTL 2 min)
    budget:key:{api_key_id}:{date}         – cumulative tokens used today  (TTL 2 days)
    budget:tenant:{tenant_id}:{date}       – cumulative tokens used today  (TTL 2 days)
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    # ------------------------------------------------------------------
    # Request-per-minute sliding window
    # ------------------------------------------------------------------

    async def check_requests_per_minute(self, api_key_id: int, limit: int) -> bool:
        """Return True if the request is within the per-minute rate limit."""
        try:
            bucket = int(time.time()) // 60
            key = f"rl:key:{api_key_id}:{bucket}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 120)
            return count <= limit
        except Exception:
            log.warning("Redis unavailable – skipping rate-limit check")
            return True

    # ------------------------------------------------------------------
    # Token budget (pre-flight check)
    # ------------------------------------------------------------------

    async def check_token_budget(
        self,
        api_key_id: int,
        tenant_id: int,
        estimated_tokens: int,
        key_daily_limit: int | None,
        tenant_daily_budget: int | None,
    ) -> tuple[bool, str]:
        """
        Return (allowed, reason).
        Checks key-level and tenant-level budgets WITHOUT consuming tokens.
        """
        try:
            today = str(date.today())

            if key_daily_limit is not None:
                used = int(await self.redis.get(f"budget:key:{api_key_id}:{today}") or 0)
                if used + estimated_tokens > key_daily_limit:
                    return False, "api_key_token_budget_exceeded"

            if tenant_daily_budget is not None:
                used = int(await self.redis.get(f"budget:tenant:{tenant_id}:{today}") or 0)
                if used + estimated_tokens > tenant_daily_budget:
                    return False, "tenant_token_budget_exceeded"

            return True, "ok"
        except Exception:
            log.warning("Redis unavailable – skipping token budget check")
            return True, "ok"

    # ------------------------------------------------------------------
    # Token usage recording (post-response)
    # ------------------------------------------------------------------

    async def record_token_usage(
        self,
        api_key_id: int,
        tenant_id: int,
        tokens: int,
    ) -> None:
        """Atomically increment today's token counters for key and tenant."""
        try:
            today = str(date.today())
            ttl = 86400 * 2

            pipe = self.redis.pipeline()
            pipe.incrby(f"budget:key:{api_key_id}:{today}", tokens)
            pipe.expire(f"budget:key:{api_key_id}:{today}", ttl)
            pipe.incrby(f"budget:tenant:{tenant_id}:{today}", tokens)
            pipe.expire(f"budget:tenant:{tenant_id}:{today}", ttl)
            await pipe.execute()
        except Exception:
            log.warning("Redis unavailable – token usage not recorded")

    # ------------------------------------------------------------------
    # Read-only helpers for the usage API
    # ------------------------------------------------------------------

    async def get_key_tokens_today(self, api_key_id: int) -> int:
        try:
            today = str(date.today())
            return int(await self.redis.get(f"budget:key:{api_key_id}:{today}") or 0)
        except Exception:
            return 0

    async def get_tenant_tokens_today(self, tenant_id: int) -> int:
        try:
            today = str(date.today())
            return int(await self.redis.get(f"budget:tenant:{tenant_id}:{today}") or 0)
        except Exception:
            return 0

