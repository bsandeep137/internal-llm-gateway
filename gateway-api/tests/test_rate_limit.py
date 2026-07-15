import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rate_limit import RateLimitService


def make_redis(get_val=None, incr_val=1):
    """Build a minimal async Redis mock."""
    r = AsyncMock()
    r.incr = AsyncMock(return_value=incr_val)
    r.expire = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=str(get_val) if get_val is not None else None)
    pipe = AsyncMock()
    pipe.incrby = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[])
    r.pipeline = MagicMock(return_value=pipe)
    return r


class TestRateLimitService:
    @pytest.mark.asyncio
    async def test_within_rpm_limit(self):
        redis = make_redis(incr_val=3)
        svc = RateLimitService(redis)
        result = await svc.check_requests_per_minute(api_key_id=1, limit=10)
        assert result is True

    @pytest.mark.asyncio
    async def test_exceeds_rpm_limit(self):
        redis = make_redis(incr_val=11)
        svc = RateLimitService(redis)
        result = await svc.check_requests_per_minute(api_key_id=1, limit=10)
        assert result is False

    @pytest.mark.asyncio
    async def test_token_budget_ok_when_no_limits(self):
        redis = make_redis()
        svc = RateLimitService(redis)
        ok, reason = await svc.check_token_budget(1, 1, 500, None, None)
        assert ok is True
        assert reason == "ok"

    @pytest.mark.asyncio
    async def test_token_budget_key_limit_exceeded(self):
        redis = make_redis(get_val=900)
        svc = RateLimitService(redis)
        ok, reason = await svc.check_token_budget(1, 1, 200, 1_000, None)
        assert ok is False
        assert "api_key" in reason

    @pytest.mark.asyncio
    async def test_token_budget_tenant_limit_exceeded(self):
        redis = make_redis(get_val=0)
        # First get (key budget) returns 0, second (tenant budget) returns 9900
        redis.get = AsyncMock(side_effect=["0", "9900"])
        svc = RateLimitService(redis)
        ok, reason = await svc.check_token_budget(1, 1, 200, 10_000, 10_000)
        assert ok is False
        assert "tenant" in reason

    @pytest.mark.asyncio
    async def test_record_token_usage_calls_pipeline(self):
        redis = make_redis()
        svc = RateLimitService(redis)
        await svc.record_token_usage(api_key_id=1, tenant_id=1, tokens=100)
        pipe = redis.pipeline()
        pipe.execute.assert_called_once()
