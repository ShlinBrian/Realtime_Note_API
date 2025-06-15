from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import date, datetime, timedelta

from api.db.database import get_async_db
from api.models.models import User, UsageSummary
from api.models.schemas import UsageResponse, UserRole
from api.utils.organization import get_or_create_default_organization

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "/usage",
    response_model=List[UsageResponse],
    summary="Get usage statistics",
    description="""
**Description:** Retrieve API usage statistics and billing information for a specified date range. Provides insights into API consumption patterns and costs.

**Query Parameters:**
1. from (optional, date): Start date for usage statistics in YYYY-MM-DD format (default: 30 days ago)
2. to (optional, date): End date for usage statistics in YYYY-MM-DD format (default: today)

**Headers:**
- x-api-key: your_api_key (optional, for authentication)

**Response:** Array of daily usage summaries with request counts, bandwidth, and costs

**Example Request:**
```
GET /v1/admin/usage?from=2024-01-01&to=2024-01-31
```

**Example Response:**
```json
[
    {
        "period": "2024-01-15",
        "requests": 1250,
        "bytes": 2048576,
        "cost_usd": "12.50"
    },
    {
        "period": "2024-01-14", 
        "requests": 980,
        "bytes": 1572864,
        "cost_usd": "9.80"
    }
]
```

**Response Fields:**
- period: Date of the usage period (YYYY-MM-DD)
- requests: Total number of API requests for that day
- bytes: Total bandwidth usage in bytes for that day
- cost_usd: Calculated cost in USD (if billing is configured)
""",
    response_description="Array of daily usage summaries with request counts, bandwidth, and costs",
    responses={
        200: {
            "description": "Usage statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "period": "2024-01-15",
                            "requests": 1250,
                            "bytes": 2048576,
                            "cost_usd": "12.50",
                        },
                        {
                            "period": "2024-01-14",
                            "requests": 980,
                            "bytes": 1572864,
                            "cost_usd": "9.80",
                        },
                    ]
                }
            },
        },
        400: {"description": "Invalid date range"},
        500: {"description": "Internal server error"},
    },
)
async def get_usage(
    from_date: Optional[date] = Query(
        None,
        alias="from",
        description="Start date for usage statistics (YYYY-MM-DD)",
        example="2024-01-01",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to",
        description="End date for usage statistics (YYYY-MM-DD)",
        example="2024-01-31",
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve API usage statistics and billing information.

    **Query Parameters:**
    - **from**: Start date for the report (defaults to 30 days ago)
    - **to**: End date for the report (defaults to today)

    **Usage Metrics:**
    - **requests**: Total number of API requests per day
    - **bytes**: Total bandwidth usage in bytes per day
    - **cost_usd**: Calculated cost in USD (if billing is configured)

    **Features:**
    - **Date Range Filtering**: Specify custom date ranges
    - **Daily Granularity**: Usage broken down by day
    - **Billing Integration**: Shows costs when billing is enabled
    - **Organization Scoped**: Only shows usage for your organization

    **Date Format:** Use ISO date format (YYYY-MM-DD)

    **Example Usage:**
    - Last 7 days: `?from=2024-01-08&to=2024-01-15`
    - Specific month: `?from=2024-01-01&to=2024-01-31`
    - Default (last 30 days): No parameters needed

    **Use Cases:**
    - Monitor API usage patterns
    - Track billing and costs
    - Capacity planning
    - Usage analysis and optimization

    **Returns:** Array of daily usage summaries ordered by date
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Set default date range if not provided
    if not from_date:
        from_date = date.today() - timedelta(days=30)

    if not to_date:
        to_date = date.today()

    # Get usage summaries
    result = await db.execute(
        select(UsageSummary)
        .where(
            UsageSummary.org_id == org_id,
            UsageSummary.period >= from_date,
            UsageSummary.period <= to_date,
        )
        .order_by(UsageSummary.period)
    )
    summaries = result.scalars().all()

    # Convert to response format
    responses = []
    for summary in summaries:
        cost_usd = None
        if summary.invoice_json and "cost_usd" in summary.invoice_json:
            cost_usd = summary.invoice_json["cost_usd"]

        responses.append(
            UsageResponse(
                period=summary.period,
                requests=summary.requests,
                bytes=summary.bytes,
                cost_usd=cost_usd,
            )
        )

    return responses


@router.get("/users", response_model=List[dict])
async def list_users(
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all users
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Get users
    result = await db.execute(select(User).where(User.org_id == org_id))
    users = result.scalars().all()

    # Format response
    return [
        {
            "user_id": u.user_id,
            "email": u.email,
            "role": u.role.value,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/users/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: str,
    role: UserRole,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a user's role
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Get user
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.org_id == org_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Update role
    user.role = role.value
    db.add(user)
    await db.commit()

    return {"success": True, "user_id": user_id, "role": role}
