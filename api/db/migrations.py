from alembic import command
from alembic.config import Config
import os
import logging
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from api.db.database import engine, Base
from api.models.models import (
    Organization,
    User,
    ApiKey,
    Note,
    UsageLog,
    UsageSummary,
    SwaggerAcl,
    UserRole,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_rls_policies():
    """Set up Row-Level Security policies for PostgreSQL"""
    logger.info("Setting up Row-Level Security policies")

    try:
        with engine.connect() as conn:
            # Enable RLS on tables
            conn.execute(text("ALTER TABLE note ENABLE ROW LEVEL SECURITY"))
            conn.execute(text("ALTER TABLE usage_log ENABLE ROW LEVEL SECURITY"))
            conn.execute(text("ALTER TABLE usage_summary ENABLE ROW LEVEL SECURITY"))

            # Create policies
            conn.execute(
                text(
                    """
                CREATE POLICY org_isolation_note ON note
                USING (org_id = current_setting('app.org_id')::text)
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE POLICY org_isolation_usage_log ON usage_log
                USING (org_id = current_setting('app.org_id')::text)
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE POLICY org_isolation_usage_summary ON usage_summary
                USING (org_id = current_setting('app.org_id')::text)
            """
                )
            )

            # Commit changes
            conn.commit()

            logger.info("RLS policies created successfully")
    except ProgrammingError as e:
        if "already exists" in str(e):
            logger.info("RLS policies already exist, skipping")
        else:
            logger.error(f"Error setting up RLS policies: {e}")
            raise


def create_default_acls():
    """Create default ACL entries for roles"""
    logger.info("Creating default ACL entries")

    try:
        # Skip ACL creation for now to avoid enum issues
        logger.info("Skipping ACL creation to avoid enum compatibility issues")
        return

        # This code is commented out until enum issues are resolved
        with engine.connect() as conn:
            # Define default permissions
            acls = [
                # Viewer permissions
                {
                    "role": UserRole.VIEWER.value,
                    "tag": "notes",
                    "can_read": True,
                    "can_write": False,
                },
                {
                    "role": UserRole.VIEWER.value,
                    "tag": "search",
                    "can_read": True,
                    "can_write": False,
                },
                # Editor permissions
                {
                    "role": UserRole.EDITOR.value,
                    "tag": "notes",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.EDITOR.value,
                    "tag": "search",
                    "can_read": True,
                    "can_write": False,
                },
                # Owner permissions
                {
                    "role": UserRole.OWNER.value,
                    "tag": "notes",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.OWNER.value,
                    "tag": "search",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.OWNER.value,
                    "tag": "admin",
                    "can_read": True,
                    "can_write": False,
                },
                {
                    "role": UserRole.OWNER.value,
                    "tag": "api-keys",
                    "can_read": True,
                    "can_write": True,
                },
                # Admin permissions
                {
                    "role": UserRole.ADMIN.value,
                    "tag": "notes",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.ADMIN.value,
                    "tag": "search",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.ADMIN.value,
                    "tag": "admin",
                    "can_read": True,
                    "can_write": True,
                },
                {
                    "role": UserRole.ADMIN.value,
                    "tag": "api-keys",
                    "can_read": True,
                    "can_write": True,
                },
            ]

            # Insert ACLs
            for acl in acls:
                conn.execute(
                    text(
                        """
                        INSERT INTO swagger_acl (role, tag, can_read, can_write)
                        VALUES (:role, :tag, :can_read, :can_write)
                        ON CONFLICT (role, tag) DO UPDATE
                        SET can_read = :can_read, can_write = :can_write
                    """
                    ),
                    acl,
                )

            # Commit changes
            conn.commit()

            logger.info("Default ACL entries created successfully")
    except Exception as e:
        logger.error(f"Error creating default ACL entries: {e}")
        raise


def run_migrations():
    """Run database migrations"""
    logger.info("Running database migrations")

    try:
        # Create tables directly with SQLAlchemy
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")

        # Set up RLS policies
        setup_rls_policies()

        # Create default ACLs
        create_default_acls()

        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise


if __name__ == "__main__":
    run_migrations()
