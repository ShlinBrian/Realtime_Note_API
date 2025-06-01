from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional
from datetime import date, datetime, timedelta

from api.db.database import get_async_db, set_tenant_context
from api.models.models import User, UsageSummary
from api.models.schemas import UsageResponse, UserRole
from api.auth.auth import get_current_active_user, get_user_with_permission
from api.auth.rate_limit import check_rate_limit

router = APIRouter(
    prefix="/v1/admin", tags=["admin"], dependencies=[Depends(check_rate_limit)]
)


@router.get("/usage", response_model=List[UsageResponse])
async def get_usage(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.OWNER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get usage statistics for the organization

    Requires owner role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all users in the organization

    Requires admin role
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a user's role

    Requires admin role
    """
    admin, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
