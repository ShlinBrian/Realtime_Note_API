#!/usr/bin/env python
import os
import sys
import time
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import hashlib

# Add parent directory to path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.db.migrations import run_migrations
from api.models.models import Organization, User, ApiKey, UserRole
from api.auth.auth import hash_api_key, API_KEY_PREFIX


# Wait for database to be ready
def wait_for_db(url, max_retries=10, retry_interval=3):
    print("Waiting for database to be ready...")
    engine = create_engine(url)
    retries = 0

    while retries < max_retries:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Database is ready!")
                return True
        except Exception as e:
            print(f"Database not ready yet: {e}")
            retries += 1
            time.sleep(retry_interval)

    print("Failed to connect to database")
    return False


def create_initial_data(db_url):
    # Create engine and session
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if organization already exists
        org = session.query(Organization).first()

        if not org:
            # Create organization
            org_id = str(uuid.uuid4())
            org = Organization(org_id=org_id, name="Demo Organization")
            session.add(org)
            session.flush()

            # Create admin user
            admin_id = str(uuid.uuid4())
            admin = User(
                user_id=admin_id,
                org_id=org_id,
                email="admin@example.com",
                role=UserRole.ADMIN,
            )
            session.add(admin)

            # Generate API key
            api_key = f"{API_KEY_PREFIX}{uuid.uuid4().hex}"
            api_key_hash = hash_api_key(api_key)

            # Create API key record
            key = ApiKey(
                key_id=str(uuid.uuid4()),
                org_id=org_id,
                hash=api_key_hash,
                name="Initial API Key",
            )
            session.add(key)

            # Commit changes
            session.commit()

            print("Initial data created successfully!")
            print(f"API Key: {api_key}")

            # Save API key to file for easy access
            with open("local_api_key.txt", "w") as f:
                f.write(f"API_KEY={api_key}\n")

            print("API key saved to local_api_key.txt")
        else:
            print("Organization already exists, skipping initial data creation")

    except Exception as e:
        session.rollback()
        print(f"Error creating initial data: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    # Get database URL from environment or use default
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/notes")

    # Wait for database
    if wait_for_db(db_url):
        # Run migrations
        try:
            run_migrations()
            print("Migrations completed successfully")
        except Exception as e:
            print(f"Error running migrations: {e}")
            sys.exit(1)

        # Create initial data
        create_initial_data(db_url)
    else:
        print("Could not connect to database")
        sys.exit(1)
