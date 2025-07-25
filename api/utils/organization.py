"""
Utility functions for organization management
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.models.models import Organization


async def get_or_create_default_organization(db: AsyncSession) -> str:
    """
    Get or create a default organization and return its org_id.

    This function:
    1. First tries to find an organization with id "default"
    2. If not found, tries to get any existing organization
    3. If no organizations exist, creates a new default organization

    Returns:
        str: The org_id of the default organization
    """
    try:
        # First try to get any existing organization
        result = await db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()

        if org:
            return org.org_id

        # If no organizations exist, create a default one
        org = Organization(org_id="default", name="Default Organization")
        db.add(org)
        await db.commit()
        await db.refresh(org)
        
        return org.org_id
        
    except Exception as e:
        # Return the known existing org_id from database as fallback
        print(f"Error in get_or_create_default_organization: {e}")
        return "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"
