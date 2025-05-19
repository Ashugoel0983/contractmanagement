"""
Authentication utilities for Contract Management System
"""

import json
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
import jwt

# Set up logging
logger = logging.getLogger(__name__)

def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header"""
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    
    parts = auth.split()
    
    if parts[0].lower() != "bearer":
        return None
    
    elif len(parts) == 1:
        return None
    
    elif len(parts) > 2:
        return None
    
    token = parts[1]
    return token

def requires_auth(f):
    """Determines if the Access Token is valid"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        if not token:
            return jsonify({
                "success": False,
                "message": "Authorization header is required"
            }), 401
        
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired"
            }), 401
        except Exception:
            return jsonify({
                "success": False,
                "message": "Invalid token"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated

def requires_role(role):
    """Determines if the user has the required role"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            if not token:
                return jsonify({
                    "success": False,
                    "message": "Authorization header is required"
                }), 401
            
            try:
                payload = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )
            except jwt.ExpiredSignatureError:
                return jsonify({
                    "success": False,
                    "message": "Token has expired"
                }), 401
            except Exception:
                return jsonify({
                    "success": False,
                    "message": "Invalid token"
                }), 401
            
            # Check if user has required role
            user_role = payload.get("role")
            if not user_role or user_role != role:
                return jsonify({
                    "success": False,
                    "message": f"Role '{role}' is required to access this resource"
                }), 403
            
            return f(*args, **kwargs)
        
        return wrapper
    
    return decorator

def get_user_info():
    """Get the current user information from the JWT token"""
    token = get_token_auth_header()
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"]
        )
        return payload
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return None

def generate_token(user_data, expiration=3600):
    """
    Generate a JWT token
    
    Args:
        user_data: Dict containing user information
        expiration: Token expiration time in seconds (default: 1 hour)
    
    Returns:
        str: JWT token
    """
    try:
        # Set token expiration time
        exp = datetime.utcnow() + timedelta(seconds=expiration)
        
        # Create token payload
        payload = {
            **user_data,
            'exp': exp
        }
        
        # Generate token
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return token
    
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return None