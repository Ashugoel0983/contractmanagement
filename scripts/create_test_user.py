#!/usr/bin/env python3
"""
Script to create a test user for the Contract Management System
This is useful for testing and development
"""

import os
import sys
import logging
from werkzeug.security import generate_password_hash

# Add the parent directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, UserRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_user():
    """Create a test user for the Contract Management System"""
    with app.app_context():
        # Check if test user already exists
        test_user = User.query.filter_by(email="test@example.com").first()
        
        if test_user:
            logger.info("Test user already exists")
            return test_user
        
        # Create test user
        test_user = User()
        test_user.email = "test@example.com"
        test_user.name = "Test User"
        test_user.password_hash = generate_password_hash("password123")
        test_user.role = UserRole.ADMIN
        test_user.auth0_id = "local|test@example.com"
        test_user.is_active = True
        
        # Add and commit to database
        db.session.add(test_user)
        db.session.commit()
        
        logger.info(f"Created test user: {test_user.email}")
        return test_user

if __name__ == "__main__":
    create_test_user()