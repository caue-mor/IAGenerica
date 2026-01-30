"""
Rate Limiter - Protection against abuse and DDoS.

In-memory rate limiting that can be extended to Redis for distributed deployments.
Supports per-company and per-IP rate limiting with configurable windows.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    limit: int                      # Max requests
    window_seconds: int             # Time window in seconds
    burst_limit: Optional[int] = None  # Max burst (optional)
    cooldown_seconds: int = 0       # Cooldown after limit hit


@dataclass
class RequestRecord:
    """Record of a request."""
    timestamp: datetime
    count: int = 1


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after_seconds: int = 0


class RateLimiter:
    """
    In-memory rate limiter with sliding window algorithm.

    Tracks requests by key (company_id, IP, etc.) and enforces limits.
    """

    # Default configurations
    DEFAULT_CONFIGS = {
        "company": RateLimitConfig(limit=100, window_seconds=60),      # 100 req/min per company
        "ip": RateLimitConfig(limit=30, window_seconds=60),            # 30 req/min per IP
        "global": RateLimitConfig(limit=1000, window_seconds=60),      # 1000 req/min global
        "webhook": RateLimitConfig(limit=200, window_seconds=60),      # 200 req/min for webhooks
        "api": RateLimitConfig(limit=60, window_seconds=60),           # 60 req/min for API
    }

    def __init__(self, configs: Dict[str, RateLimitConfig] = None):
        """
        Initialize the rate limiter.

        Args:
            configs: Custom rate limit configurations
        """
        self.configs = configs or self.DEFAULT_CONFIGS.copy()
        self.requests: Dict[str, List[RequestRecord]] = defaultdict(list)
        self.blocked_until: Dict[str, datetime] = {}  # Cooldown tracking
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self):
        """Periodically clean up old records."""
        while True:
            try:
                await asyncio.sleep(60)  # Clean every minute
                self._cleanup_old_records()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")

    def _cleanup_old_records(self):
        """Remove old request records."""
        now = datetime.utcnow()
        max_window = max(c.window_seconds for c in self.configs.values())
        cutoff = now - timedelta(seconds=max_window + 60)

        keys_to_delete = []
        for key, records in self.requests.items():
            # Filter out old records
            self.requests[key] = [r for r in records if r.timestamp > cutoff]
            if not self.requests[key]:
                keys_to_delete.append(key)

        # Remove empty keys
        for key in keys_to_delete:
            del self.requests[key]

        # Clean up expired blocks
        for key in list(self.blocked_until.keys()):
            if self.blocked_until[key] < now:
                del self.blocked_until[key]

    def check_rate_limit(
        self,
        key: str,
        limit_type: str = "company"
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Args:
            key: Identifier for the requester (company_id, IP, etc.)
            limit_type: Type of limit to apply

        Returns:
            RateLimitResult with limit status
        """
        config = self.configs.get(limit_type, self.DEFAULT_CONFIGS["company"])
        now = datetime.utcnow()
        full_key = f"{limit_type}:{key}"

        # Check if in cooldown
        if full_key in self.blocked_until:
            if now < self.blocked_until[full_key]:
                retry_after = int((self.blocked_until[full_key] - now).total_seconds())
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=self.blocked_until[full_key],
                    retry_after_seconds=retry_after
                )
            else:
                del self.blocked_until[full_key]

        # Clean old records for this key
        window_start = now - timedelta(seconds=config.window_seconds)
        self.requests[full_key] = [
            r for r in self.requests[full_key]
            if r.timestamp > window_start
        ]

        # Count requests in window
        request_count = sum(r.count for r in self.requests[full_key])

        # Check limit
        if request_count >= config.limit:
            # Apply cooldown if configured
            if config.cooldown_seconds > 0:
                self.blocked_until[full_key] = now + timedelta(seconds=config.cooldown_seconds)

            # Find when window resets
            oldest_request = min(self.requests[full_key], key=lambda r: r.timestamp) if self.requests[full_key] else None
            reset_at = oldest_request.timestamp + timedelta(seconds=config.window_seconds) if oldest_request else now

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=int((reset_at - now).total_seconds())
            )

        # Request is allowed
        remaining = config.limit - request_count - 1
        reset_at = now + timedelta(seconds=config.window_seconds)

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at
        )

    def record_request(self, key: str, limit_type: str = "company") -> None:
        """
        Record a request for rate limiting.

        Args:
            key: Identifier for the requester
            limit_type: Type of limit
        """
        full_key = f"{limit_type}:{key}"
        self.requests[full_key].append(RequestRecord(timestamp=datetime.utcnow()))

    async def check_and_record(
        self,
        key: str,
        limit_type: str = "company"
    ) -> RateLimitResult:
        """
        Check rate limit and record request if allowed.

        Args:
            key: Identifier for the requester
            limit_type: Type of limit

        Returns:
            RateLimitResult
        """
        result = self.check_rate_limit(key, limit_type)
        if result.allowed:
            self.record_request(key, limit_type)
        return result

    def get_usage(self, key: str, limit_type: str = "company") -> Dict[str, any]:
        """
        Get current usage for a key.

        Args:
            key: Identifier for the requester
            limit_type: Type of limit

        Returns:
            Dictionary with usage information
        """
        config = self.configs.get(limit_type, self.DEFAULT_CONFIGS["company"])
        full_key = f"{limit_type}:{key}"
        now = datetime.utcnow()

        # Count requests in window
        window_start = now - timedelta(seconds=config.window_seconds)
        records = [r for r in self.requests.get(full_key, []) if r.timestamp > window_start]
        request_count = sum(r.count for r in records)

        return {
            "key": key,
            "limit_type": limit_type,
            "current_usage": request_count,
            "limit": config.limit,
            "remaining": max(0, config.limit - request_count),
            "window_seconds": config.window_seconds,
            "is_blocked": full_key in self.blocked_until
        }


# Singleton instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded header (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to client host
    if request.client:
        return request.client.host

    return "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting.

    Applies rate limits based on:
    - Company ID (from path parameter)
    - Client IP
    - Global limit
    """
    # Skip health check endpoints
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
        return await call_next(request)

    client_ip = get_client_ip(request)

    # Check IP-based limit
    ip_result = await rate_limiter.check_and_record(client_ip, "ip")
    if not ip_result.allowed:
        logger.warning(f"Rate limited IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": ip_result.retry_after_seconds,
                "limit_type": "ip"
            },
            headers={"Retry-After": str(ip_result.retry_after_seconds)}
        )

    # Check company-based limit if company_id in path
    company_id = request.path_params.get("company_id")
    if company_id:
        company_result = await rate_limiter.check_and_record(str(company_id), "company")
        if not company_result.allowed:
            logger.warning(f"Rate limited company: {company_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": company_result.retry_after_seconds,
                    "limit_type": "company"
                },
                headers={"Retry-After": str(company_result.retry_after_seconds)}
            )

    # Check webhook-specific limit
    if "/webhook" in request.url.path:
        webhook_result = await rate_limiter.check_and_record(
            company_id or client_ip,
            "webhook"
        )
        if not webhook_result.allowed:
            logger.warning(f"Rate limited webhook: {company_id or client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": webhook_result.retry_after_seconds,
                    "limit_type": "webhook"
                },
                headers={"Retry-After": str(webhook_result.retry_after_seconds)}
            )

    # Add rate limit headers to response
    response = await call_next(request)

    # Add headers with remaining limits
    if company_id:
        usage = rate_limiter.get_usage(str(company_id), "company")
        response.headers["X-RateLimit-Limit"] = str(usage["limit"])
        response.headers["X-RateLimit-Remaining"] = str(usage["remaining"])
        response.headers["X-RateLimit-Reset"] = str(usage["window_seconds"])

    return response


def create_rate_limiter(configs: Dict[str, RateLimitConfig] = None) -> RateLimiter:
    """
    Factory function to create a rate limiter with custom configs.

    Args:
        configs: Custom rate limit configurations

    Returns:
        RateLimiter instance
    """
    return RateLimiter(configs)


# Dependency for FastAPI
async def get_rate_limiter() -> RateLimiter:
    """FastAPI dependency to get rate limiter."""
    return rate_limiter
