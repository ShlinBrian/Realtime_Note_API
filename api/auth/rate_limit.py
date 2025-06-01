import time
import json
import redis
import os
from fastapi import Depends, HTTPException, Request, status
from typing import Optional, Tuple, Dict, Any

from api.models.models import User, Organization
from api.auth.auth import get_current_active_user

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Default rate limits
DEFAULT_REQUESTS_PER_MINUTE = 60
DEFAULT_BYTES_PER_MINUTE = 1024 * 1024  # 1 MB

# Lua script for token bucket algorithm
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('hmget', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1] or capacity)
local last_refill = tonumber(bucket[2] or 0)

-- Calculate token refill
local elapsed = math.max(0, now - last_refill)
local refill = math.floor(elapsed * capacity / window)
tokens = math.min(capacity, tokens + refill)

-- Try to consume tokens
if tokens >= requested then
    tokens = tokens - requested
    redis.call('hmset', key, 'tokens', tokens, 'last_refill', now)
    redis.call('expire', key, window)
    return {tokens, 0}  -- Success, remaining tokens
else
    local retry_after = math.ceil((requested - tokens) * window / capacity)
    return {tokens, retry_after}  -- Failure, retry after seconds
end
"""

# Load the script once
rate_limit_script = redis_client.register_script(RATE_LIMIT_SCRIPT)


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        bytes_per_minute: int = DEFAULT_BYTES_PER_MINUTE,
    ):
        self.requests_per_minute = requests_per_minute
        self.bytes_per_minute = bytes_per_minute
        self.window = 60  # 1 minute in seconds

    async def check_rate_limit(
        self, org_id: str, kind: str = "REST", bytes_count: int = 0
    ) -> bool:
        """
        Check if the request is within rate limits
        Returns True if allowed, False if rate limited
        """
        now = int(time.time())

        # Check request rate limit
        req_key = f"rl:org:{org_id}:req:{kind}"
        req_result = rate_limit_script(
            keys=[req_key], args=[now, self.window, self.requests_per_minute, 1]
        )

        if req_result[1] > 0:  # retry_after > 0 means rate limited
            return False

        # Check bytes rate limit if applicable
        if bytes_count > 0:
            bytes_key = f"rl:org:{org_id}:bytes:{kind}"
            bytes_result = rate_limit_script(
                keys=[bytes_key],
                args=[now, self.window, self.bytes_per_minute, bytes_count],
            )

            if bytes_result[1] > 0:  # retry_after > 0 means rate limited
                return False

        return True

    async def get_rate_limit_headers(
        self, org_id: str, kind: str = "REST"
    ) -> Dict[str, str]:
        """Get rate limit headers for the response"""
        req_key = f"rl:org:{org_id}:req:{kind}"
        bytes_key = f"rl:org:{org_id}:bytes:{kind}"

        # Get current token counts
        req_tokens = redis_client.hget(req_key, "tokens")
        bytes_tokens = redis_client.hget(bytes_key, "tokens")

        req_remaining = int(req_tokens) if req_tokens else self.requests_per_minute
        bytes_remaining = int(bytes_tokens) if bytes_tokens else self.bytes_per_minute

        return {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(req_remaining),
            "X-RateLimit-BytesLimit": str(self.bytes_per_minute),
            "X-RateLimit-BytesRemaining": str(bytes_remaining),
            "X-RateLimit-Reset": str(int(time.time()) + self.window),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request, current_user: Tuple[User, str] = Depends(get_current_active_user)
) -> None:
    """
    Dependency to check rate limits for the current request
    Raises HTTPException if rate limited
    """
    user, org_id = current_user

    # Get custom limits from organization if available
    custom_limits = {}
    if (
        hasattr(user, "organization")
        and user.organization
        and user.organization.quota_json
    ):
        try:
            custom_limits = json.loads(user.organization.quota_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Create rate limiter with custom limits if available
    limiter = RateLimiter(
        requests_per_minute=custom_limits.get(
            "requests_per_minute", DEFAULT_REQUESTS_PER_MINUTE
        ),
        bytes_per_minute=custom_limits.get(
            "bytes_per_minute", DEFAULT_BYTES_PER_MINUTE
        ),
    )

    # Estimate content size from request
    content_length = request.headers.get("content-length", "0")
    bytes_count = int(content_length) if content_length.isdigit() else 0

    # Determine API kind
    path = request.url.path
    if path.startswith("/ws/"):
        kind = "WS"
    elif path.startswith("/v1/"):
        kind = "REST"
    else:
        kind = "gRPC"

    # Check rate limit
    allowed = await limiter.check_rate_limit(org_id, kind, bytes_count)

    if not allowed:
        # Add rate limit headers to the response
        headers = await limiter.get_rate_limit_headers(org_id, kind)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"{DEFAULT_REQUESTS_PER_MINUTE} req/min limit",
            },
            headers=headers,
        )
