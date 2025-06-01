import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from api.billing.usage import generate_usage_summary
from api.db.database import ASYNC_DATABASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create async engine for worker
async_engine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession, autocommit=False, autoflush=False, bind=async_engine
)


async def get_async_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def process_previous_day():
    """Process usage data from the previous day"""
    yesterday = date.today() - timedelta(days=1)
    logger.info(f"Processing usage data for {yesterday}")

    try:
        # Get database session
        db = next(get_async_db())

        # Generate usage summaries
        await generate_usage_summary(db, yesterday)

        logger.info(f"Successfully processed usage data for {yesterday}")
    except Exception as e:
        logger.error(f"Error processing usage data: {e}")
        raise


async def run_worker():
    """Run the billing worker"""
    logger.info("Starting billing worker")

    try:
        await process_previous_day()
    except Exception as e:
        logger.error(f"Worker failed: {e}")
    finally:
        logger.info("Billing worker finished")


def main():
    """Main entry point for the worker"""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
