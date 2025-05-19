#!/usr/bin/env python3
"""
Database Reset Script for Contract Management System

This script drops all tables and recreates them with the current schema.
Use with caution as it will delete all data!

Usage: python reset_database.py
"""

import os
import sys
import logging

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_database():
    """Drop all tables and recreate them"""
    try:
        # Import app and db after setting environment variable
        from app import app, db
        
        logger.info("Resetting database...")
        
        with app.app_context():
            # Drop all tables
            db.drop_all()
            logger.info("All tables dropped successfully!")
            
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully!")
            
            # Check if tables were created successfully
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Created tables: {', '.join(tables)}")
            
            # Seed initial data if needed
            from scripts.database_setup import seed_sample_users, seed_sample_contracts
            users = seed_sample_users()
            if users:
                logger.info("Seeding sample contracts...")
                seed_sample_contracts(users)
            
            logger.info("Database reset complete!")
            return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

if __name__ == "__main__":
    # Skip confirmation in automated environment
    logger.warning("WARNING: Resetting database - all data will be deleted!")
    reset_database()