#!/usr/bin/env python3
"""
Database Connection Test Script

This script tests the database connection and verifies table structure
to ensure the MySQL compatibility changes are working correctly.
"""

import os
import sys
import logging

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Test database connection and verify tables"""
    try:
        # Set MySQL as database type
        os.environ["DB_TYPE"] = "mysql"
        
        # Import app and db
        from app import app, db
        
        with app.app_context():
            # Import models
            from models import User, Contract, ContractParty, ContractMetadata, Invoice, Approval, Notification
            
            # Test connection with a simple query
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1")).scalar()
            logger.info(f"Database connection test: {result == 1}")
            
            # Check table structure
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # Get all tables
            tables = inspector.get_table_names()
            logger.info(f"Available tables: {', '.join(tables)}")
            
            # Check contract table columns to verify our changes
            columns = inspector.get_columns('contracts')
            column_names = [col['name'] for col in columns]
            logger.info(f"Contract table columns: {', '.join(column_names)}")
            
            # Verify tags_json field exists (our MySQL compatibility change)
            if 'tags_json' in column_names:
                logger.info("✓ MySQL compatibility change verified: tags_json field exists")
            else:
                logger.error("✗ MySQL compatibility issue: tags_json field missing")
            
            # Create a test user
            test_user = User()
            test_user.auth0_id = "test-auth0-id"
            test_user.email = "test@example.com"
            test_user.name = "Test User"
            test_user.role = UserRole.USER
            
            # Create a test contract with tags
            test_contract = Contract()
            test_contract.contract_number = "TEST-001"
            test_contract.title = "Test Contract"
            test_contract.contract_type = ContractType.SERVICE_AGREEMENT
            test_contract.description = "Test contract for database verification"
            test_contract.tags = ["test", "verification", "mysql"]
            
            # Add to session but don't commit to avoid changing the database
            db.session.add(test_user)
            db.session.add(test_contract)
            
            # Verify tags are serialized correctly
            logger.info(f"Tags serialization test: {test_contract.tags_json}")
            
            # Rollback to avoid making changes
            db.session.rollback()
            
            logger.info("Database connection and structure verification complete!")
            return True
            
    except Exception as e:
        logger.error(f"Error testing database connection: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()