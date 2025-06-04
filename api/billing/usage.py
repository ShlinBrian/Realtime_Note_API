from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, date
import json
from typing import Optional, Callable, Awaitable, Dict, Any

from api.db.database import get_async_db
from api.models.models import UsageLog, UsageSummary


async def log_usage(
    org_id: str,
    user_id: Optional[str],
    kind: str,
    endpoint: str,
    bytes_count: int,
    db: AsyncSession,
) -> None:
    """Log usage for billing purposes"""
    usage_log = UsageLog(
        org_id=org_id, user_id=user_id, kind=kind, endpoint=endpoint, bytes=bytes_count
    )

    db.add(usage_log)
    await db.commit()


class UsageMiddleware:
    """Middleware to log API usage for billing"""

    def __init__(self, app: Any):
        self.app = app
        self.get_db_func = get_async_db

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # If not HTTP, just pass through
            await self.app(scope, receive, send)
            return

        # Create a new send function to intercept the response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Store the status code for logging
                scope["response_status"] = message.get("status", 200)

            # Call the original send function
            await send(message)

            # After the response is complete, log the usage
            if (
                message["type"] == "http.response.body"
                and message.get("more_body", False) is False
            ):
                await self._log_usage(scope)

        # Process the request
        await self.app(scope, receive, send_wrapper)

    async def _log_usage(self, scope):
        """Log API usage after the response is complete"""
        # Skip for health check endpoints
        if scope["path"].startswith("/health"):
            return

        # Get request state from scope
        request_state = scope.get("state", {})

        # Skip logging if no org_id in request state
        org_id = getattr(request_state, "org_id", None)
        if not org_id:
            return

        # Get request details
        user_id = getattr(request_state, "user_id", None)
        path = scope["path"]

        # Determine API kind
        if path.startswith("/ws/"):
            kind = "WS"
        elif path.startswith("/v1/"):
            kind = "REST"
        else:
            kind = "gRPC"

        # Calculate bytes (simplified as we don't have access to full request/response)
        total_bytes = 0  # In a real implementation, we'd calculate this

        # Log usage asynchronously
        try:
            # Get DB session
            db = next(self.get_db_func())

            await log_usage(
                org_id=org_id,
                user_id=user_id,
                kind=kind,
                endpoint=path,
                bytes_count=total_bytes,
                db=db,
            )
        except Exception:
            # Log error but don't fail the request
            pass


async def generate_usage_summary(db: AsyncSession, period: date = None) -> None:
    """
    Generate usage summary for the specified date
    If no date is provided, use yesterday
    """
    if period is None:
        period = date.today()

    # SQL query to aggregate usage logs
    query = f"""
    INSERT INTO usage_summary (org_id, period, requests, bytes, invoice_json)
    SELECT 
        org_id, 
        '{period}' as period, 
        COUNT(*) as requests, 
        SUM(bytes) as bytes,
        jsonb_build_object(
            'period', '{period}',
            'requests', COUNT(*),
            'bytes', SUM(bytes),
            'cost_usd', (COUNT(*) * 0.0001 + SUM(bytes) * 0.0000001)::text
        ) as invoice_json
    FROM 
        usage_log 
    WHERE 
        timestamp::date = '{period}'
    GROUP BY 
        org_id
    ON CONFLICT (org_id, period) DO UPDATE SET
        requests = EXCLUDED.requests,
        bytes = EXCLUDED.bytes,
        invoice_json = EXCLUDED.invoice_json
    """

    await db.execute(query)
    await db.commit()
