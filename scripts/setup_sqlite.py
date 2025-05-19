#!/usr/bin/env python3
"""
SQLite Database Setup Script for Contract Management System

This script sets up a local SQLite database for development
and testing purposes.

Usage: python setup_sqlite.py
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

def setup_sqlite():
    """Set up SQLite database"""
    try:
        # Set environment variable for SQLite
        os.environ["DB_TYPE"] = "sqlite"
        
        # Import app and db after setting environment variable
        from app import app, db
        
        logger.info("Setting up SQLite database...")
        
        with app.app_context():
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
                seed_sample_contracts(users)
            
            logger.info("SQLite database setup complete!")
            return True
    except Exception as e:
        logger.error(f"Error setting up SQLite database: {str(e)}")
        return False

if __name__ == "__main__":
    setup_sqlite()