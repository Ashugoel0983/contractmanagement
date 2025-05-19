#!/usr/bin/env python3
"""
Script to test contract upload functionality
"""

import os
import sys
import json
import logging
import requests
from werkzeug.security import generate_password_hash

# Add the parent directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, UserRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test server URL
BASE_URL = 'http://localhost:5000/v1'

def create_test_user():
    """Create test user for authentication"""
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

def get_auth_token():
    """Get authentication token"""
    login_data = {
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    response = requests.post(f'{BASE_URL}/auth/login', json=login_data)
    
    if response.status_code != 200:
        logger.error(f"Login failed: {response.text}")
        return None
    
    data = response.json()
    return data['token']

def test_contract_upload(token, contract_file_path):
    """Test contract upload endpoint"""
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # Prepare form data
    data = {
        'title': 'Test Contract',
        'contract_type': 'Service Agreement'
    }
    
    # Prepare file
    with open(contract_file_path, 'rb') as f:
        files = {
            'file': (os.path.basename(contract_file_path), f, 'application/pdf')
        }
        
        # Upload contract
        response = requests.post(
            f'{BASE_URL}/uploads',
            headers=headers,
            data=data,
            files=files
        )
    
    # Log response
    if response.status_code == 201:
        logger.info("Contract upload successful")
        logger.info(json.dumps(response.json(), indent=2))
    else:
        logger.error(f"Contract upload failed: {response.text}")
    
    return response.json() if response.status_code == 201 else None

if __name__ == "__main__":
    # Check for sample contract file path
    if len(sys.argv) > 1:
        contract_file_path = sys.argv[1]
    else:
        contract_file_path = 'sample_contract.pdf'
    
    # Check if file exists
    if not os.path.exists(contract_file_path):
        logger.error(f"Contract file not found: {contract_file_path}")
        sys.exit(1)
    
    # Create test user
    create_test_user()
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        logger.error("Failed to get authentication token")
        sys.exit(1)
    
    # Test contract upload
    logger.info(f"Uploading contract: {contract_file_path}")
    result = test_contract_upload(token, contract_file_path)
    
    if result:
        logger.info("Contract upload test completed successfully")
    else:
        logger.error("Contract upload test failed")
        sys.exit(1)