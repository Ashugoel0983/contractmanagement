"""
Authentication API endpoints for Contract Management System
"""

import os
import logging
import json
import requests
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import cross_origin
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import jwt

from app import db
from models import User, UserRole
from auth import get_token_auth_header, requires_auth

# Configure logging
logger = logging.getLogger(__name__)

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    """
    Login endpoint for email/password authentication
    """
    try:
        # Get login data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body'
            }), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Missing email or password'
            }), 400
            
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
            
        # Check password
        if not check_password_hash(user.password_hash, password):
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
            
        # Generate JWT token
        payload = {
            'sub': user.auth0_id or str(user.id),
            'email': user.email,
            'name': user.name,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during login'
        }), 500


@auth_bp.route('/signup', methods=['POST'])
@cross_origin(supports_credentials=True)
def signup():
    """
    Signup endpoint for creating new accounts
    """
    try:
        # Get signup data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body'
            }), 400
            
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Missing email or password'
            }), 400
            
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'User with this email already exists'
            }), 409
            
        # Create new user
        new_user = User()
        new_user.email = email
        new_user.name = name
        new_user.role = UserRole.USER
        new_user.password_hash = generate_password_hash(password)
        
        # Generate a local auth0_id if using local auth
        new_user.auth0_id = f"local|{email}"
        
        # Add user to database
        db.session.add(new_user)
        db.session.commit()
        
        # Generate JWT token
        payload = {
            'sub': new_user.auth0_id,
            'email': new_user.email,
            'name': new_user.name,
            'role': new_user.role.value if hasattr(new_user.role, 'value') else new_user.role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'user': new_user.to_dict()
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during signup: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error during signup'
        }), 500
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during signup'
        }), 500


@auth_bp.route('/social-login', methods=['POST'])
@cross_origin(supports_credentials=True)
def social_login():
    """
    Social login endpoint for Google and Microsoft authentication
    """
    try:
        # Get token from social login
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body'
            }), 400
            
        provider = data.get('provider')  # 'google' or 'microsoft'
        token = data.get('token')
        
        if not provider or not token:
            return jsonify({
                'success': False,
                'error': 'Missing provider or token'
            }), 400
            
        # Verify token with the provider
        user_info = None
        if provider == 'google':
            user_info = verify_google_token(token)
        elif provider == 'microsoft':
            user_info = verify_microsoft_token(token)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid provider'
            }), 400
            
        if not user_info or 'email' not in user_info:
            return jsonify({
                'success': False, 
                'error': 'Invalid token'
            }), 401
            
        # Find or create user
        email = user_info['email']
        name = user_info.get('name', '')
        provider_id = user_info.get('sub') or user_info.get('id')
        auth0_id = f"{provider}|{provider_id}"
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            user = User()
            user.email = email
            user.name = name
            user.role = UserRole.USER
            user.auth0_id = auth0_id
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user with provider info if needed
            if not user.auth0_id:
                user.auth0_id = auth0_id
                db.session.commit()
                
        # Generate JWT token
        payload = {
            'sub': user.auth0_id,
            'email': user.email,
            'name': user.name,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Social login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during social login'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@cross_origin(supports_credentials=True)
@requires_auth
def get_user_profile():
    """Get current user profile"""
    try:
        # User info should be in g.current_user from requires_auth decorator
        user_id = g.current_user.get('sub')
        
        # Extract user ID from auth0_id if needed
        if '|' in user_id:
            user_id = user_id.split('|')[1]
            
        # Get user from database
        user = User.query.filter(
            (User.auth0_id == g.current_user.get('sub')) | 
            (User.id == user_id)
        ).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
            
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while retrieving user profile'
        }), 500


@auth_bp.route('/forgot-password', methods=['POST'])
@cross_origin(supports_credentials=True)
def forgot_password():
    """
    Forgot password endpoint to send password reset email
    """
    try:
        # Get email from request
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'Email address is required'
            }), 400
            
        email = data.get('email')
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # We don't want to reveal whether a user exists or not
            return jsonify({
                'success': True,
                'message': 'If your email is registered, you will receive a password reset link'
            }), 200
            
        # In a real implementation, you would:
        # 1. Generate a secure reset token
        # 2. Store it in the database with an expiry
        # 3. Send an email with a reset link
        
        # For now, we'll just simulate success
        logger.info(f"Password reset requested for {email}")
        
        return jsonify({
            'success': True,
            'message': 'If your email is registered, you will receive a password reset link'
        }), 200
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred processing your request'
        }), 500


def verify_google_token(token):
    """
    Verify Google OAuth token
    Returns user info if valid, None if invalid
    """
    try:
        # Google's token info endpoint
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}')
        
        if response.status_code != 200:
            logger.error(f"Google token verification failed: {response.text}")
            return None
            
        return response.json()
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
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Microsoft token verification failed: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        logger.error(f"Error verifying Microsoft token: {str(e)}")
        return None