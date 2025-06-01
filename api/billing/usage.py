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

    def __init__(self, app: Any, get_db_func: Callable = get_async_db):
        self.app = app
        self.get_db_func = get_db_func

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip for health check endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Skip logging if no org_id in request state
        if not hasattr(request.state, "org_id") or not request.state.org_id:
            return response

        # Get request details
        org_id = request.state.org_id
        user_id = getattr(request.state, "user_id", None)

        # Determine API kind
        path = request.url.path
        if path.startswith("/ws/"):
            kind = "WS"
        elif path.startswith("/v1/"):
            kind = "REST"
        else:
            kind = "gRPC"

        # Calculate bytes
        request_bytes = 0
        if request.headers.get("content-length"):
            request_bytes = int(request.headers.get("content-length", "0"))

        response_bytes = 0
        if response.headers.get("content-length"):
            response_bytes = int(response.headers.get("content-length", "0"))

        total_bytes = request_bytes + response_bytes

        # Log usage asynchronously
        try:
            # Get DB session
            db = next(self.get_db_func())

            await log_usage(
                org_id=org_id,
                user_id=user_id,
                kind=kind,
                endpoint=request.url.path,
                bytes_count=total_bytes,
                db=db,
            )
        except Exception:
            # Log error but don't fail the request
            pass

        return response


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
