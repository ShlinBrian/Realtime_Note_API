#!/usr/bin/env python3
"""
Debug script to test the API directly
"""
import asyncio
import requests
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.db.database import ASYNC_DATABASE_URL
from api.models.models import Note, Organization
from sqlalchemy.future import select

async def test_db_connection():
    """Test direct database connection"""
    try:
        engine = create_async_engine(ASYNC_DATABASE_URL)
        AsyncSessionLocal = sessionmaker(
            class_=AsyncSession, autocommit=False, autoflush=False, bind=engine
        )
        
        async with AsyncSessionLocal() as session:
            # Test basic query
            result = await session.execute(select(Organization).limit(1))
            org = result.scalar_one_or_none()
            print(f"Found organization: {org.org_id if org else 'None'}")
            
            # Test notes query
            result = await session.execute(select(Note).where(Note.deleted == False).limit(5))
            notes = result.scalars().all()
            print(f"Found {len(notes)} notes")
            
        await engine.dispose()
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

async def main():
    print("Testing database connection...")
    db_ok = await test_db_connection()
    
    if db_ok:
        print("Database connection successful")
    else:
        print("Database connection failed")
    
    print("\nTesting API endpoint...")
    try:
        response = requests.get("http://localhost:8000/v1/notes", timeout=5)
        print(f"API Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Notes count: {len(data)}")
        else:
            print(f"Response text: {response.text}")
    except Exception as e:
        print(f"API request error: {e}")

if __name__ == "__main__":
    asyncio.run(main())