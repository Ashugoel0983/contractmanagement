"""
Authentication API endpoints for Contract Management System
"""

import logging
import re
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import requests

from app import db
from models import User, UserRole
from auth import generate_token

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint for email/password authentication
    
    Request:
        - email: User email
        - password: User password
        
    Returns:
        JSON response with login status and token
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is inactive'
            }), 403
        
        # Check password
        if not check_password_hash(user.password_hash, data['password']):
            return jsonify({
                'success': False,
                'message': 'Invalid password'
            }), 401
        
        # Generate token
        user_data = {
            'sub': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role.value
        }
        
        token = generate_token(user_data)
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Failed to generate token'
            }), 500
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role.value
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Signup endpoint for creating new accounts
    
    Request:
        - email: User email
        - password: User password
        - name: User name
        
    Returns:
        JSON response with signup status and token
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Validate password strength
        if len(data['password']) < 8:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters long'
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'Email already in use'
            }), 409
        
        # Create new user
        new_user = User()
        new_user.email = data['email']
        new_user.name = data['name']
        new_user.password_hash = generate_password_hash(data['password'])
        new_user.role = UserRole.USER
        new_user.auth0_id = f"local|{data['email']}"
        new_user.is_active = True
        
        # Add and commit to database
        db.session.add(new_user)
        db.session.commit()
        
        # Generate token
        user_data = {
            'sub': new_user.id,
            'email': new_user.email,
            'name': new_user.name,
            'role': new_user.role.value
        }
        
        token = generate_token(user_data)
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Failed to generate token'
            }), 500
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Signup successful',
            'token': token,
            'user': {
                'id': new_user.id,
                'email': new_user.email,
                'name': new_user.name,
                'role': new_user.role.value
            }
        }), 201
    
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        
        logger.error(f"Signup error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Signup failed: {str(e)}'
        }), 500

@auth_bp.route('/social-login', methods=['POST'])
def social_login():
    """
    Social login endpoint for Google and Microsoft authentication
    
    Request:
        - provider: Authentication provider (google, microsoft)
        - token: OAuth token from provider
        
    Returns:
        JSON response with login status and token
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['provider', 'token']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get provider and token
        provider = data['provider'].lower()
        token = data['token']
        
        # Verify token with provider
        user_info = None
        
        if provider == 'google':
            user_info = verify_google_token(token)
        elif provider == 'microsoft':
            user_info = verify_microsoft_token(token)
        else:
            return jsonify({
                'success': False,
                'message': f'Unsupported provider: {provider}'
            }), 400
        
        if not user_info:
            return jsonify({
                'success': False,
                'message': f'Failed to verify {provider} token'
            }), 401
        
        # Get or create user
        auth_id = f"{provider}|{user_info['sub']}"
        user = User.query.filter_by(auth0_id=auth_id).first()
        
        if not user:
            # Check if email is already in use
            existing_user = User.query.filter_by(email=user_info['email']).first()
            
            if existing_user:
                # Link existing account to social provider
                existing_user.auth0_id = auth_id
                db.session.commit()
                user = existing_user
            else:
                # Create new user
                user = User()
                user.auth0_id = auth_id
                user.email = user_info['email']
                user.name = user_info['name']
                user.role = UserRole.USER
                user.is_active = True
                
                db.session.add(user)
                db.session.commit()
        
        # Generate token
        user_data = {
            'sub': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role.value
        }
        
        jwt_token = generate_token(user_data)
        
        if not jwt_token:
            return jsonify({
                'success': False,
                'message': 'Failed to generate token'
            }), 500
        
        # Return success response
        return jsonify({
            'success': True,
            'message': f'{provider.capitalize()} login successful',
            'token': jwt_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role.value
            }
        }), 200
    
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        
        logger.error(f"Social login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Social login failed: {str(e)}'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
def get_user_profile():
    """
    Get current user profile
    
    Returns:
        JSON response with user profile
    """
    from auth import requires_auth, get_user_info
    
    @requires_auth
    def get_profile():
        try:
            # Get user info from token
            user_info = get_user_info()
            
            if not user_info:
                return jsonify({
                    'success': False,
                    'message': 'Failed to get user information'
                }), 500
            
            # Get user ID from token
            user_id = user_info.get('sub')
            
            # Get user from database
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 404
            
            # Return user profile
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role.value
                }
            }), 200
        
        except Exception as e:
            logger.error(f"Get profile error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get profile: {str(e)}'
            }), 500
    
    return get_profile()

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Forgot password endpoint to send password reset email
    
    Request:
        - email: User email
        
    Returns:
        JSON response with status
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        if 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            # Don't reveal that the user doesn't exist
            return jsonify({
                'success': True,
                'message': 'If the email exists, a password reset link will be sent'
            }), 200
        
        # In a real application, send password reset email here
        # For now, just return success
        
        return jsonify({
            'success': True,
            'message': 'If the email exists, a password reset link will be sent'
        }), 200
    
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process request: {str(e)}'
        }), 500

def verify_google_token(token):
    """
    Verify Google OAuth token
    Returns user info if valid, None if invalid
    """
    try:
        # Google token info endpoint
        response = requests.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
        )
        
        if response.status_code != 200:
            logger.error(f"Google token verification failed: {response.text}")
            return None
        
        # Get user info
        user_info = response.json()
        
        # Verify issuer
        if user_info.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.error(f"Invalid token issuer: {user_info.get('iss')}")
            return None
        
        # Verify email
        if not user_info.get('email_verified', False):
            logger.error("Email not verified by Google")
            return None
        
        # Return user info
        return {
            'sub': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name', '')
        }
    
    except Exception as e:
        logger.error(f"Error verifying Google token: {str(e)}")
        return None

def verify_microsoft_token(token):
    """
    Verify Microsoft OAuth token
    Returns user info if valid, None if invalid
    """
    try:
        # Microsoft Graph API endpoint
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            logger.error(f"Microsoft token verification failed: {response.text}")
            return None
        
        # Get user info
        user_info = response.json()
        
        # Return user info
        return {
            'sub': user_info.get('id'),
            'email': user_info.get('userPrincipalName'),
            'name': user_info.get('displayName', '')
        }
    
    except Exception as e:
        logger.error(f"Error verifying Microsoft token: {str(e)}")
        return None