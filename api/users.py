import logging
from flask import Blueprint, request, jsonify
from app import db
from models import User, UserRole
from auth import requires_auth, requires_role, get_user_info

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

@users_bp.route('', methods=['GET'])
@requires_auth
@requires_role(['admin'])
def get_users():
    """Get all users with optional filtering"""
    try:
        # Parse query parameters
        role = request.args.get('role')
        is_active = request.args.get('is_active')
        search = request.args.get('search')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = User.query
        
        # Apply filters if provided
        if role:
            query = query.filter(User.role == UserRole(role))
        
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            query = query.filter(User.is_active == is_active_bool)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        users = query.order_by(User.name).limit(limit).offset(offset).all()
        
        result = {
            'users': [user.to_dict() for user in users],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': f"Failed to get users: {str(e)}"}), 500

@users_bp.route('', methods=['POST'])
@requires_auth
@requires_role(['admin'])
def create_user():
    """Create a new user"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['auth0_id', 'email', 'name', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Missing required field: {field}"}), 400
        
        # Check if user already exists
        existing_user = User.query.filter(
            db.or_(
                User.auth0_id == data['auth0_id'],
                User.email == data['email']
            )
        ).first()
        
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create the user
        user = User(
            auth0_id=data['auth0_id'],
            email=data['email'],
            name=data['name'],
            role=UserRole(data['role']),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created user {user.id}: {user.name}")
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': f"Failed to create user: {str(e)}"}), 500

@users_bp.route('/<int:user_id>', methods=['GET'])
@requires_auth
def get_user(user_id):
    """Get a user by ID"""
    try:
        # Get user info for authorization check
        user_info = get_user_info()
        current_user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            return jsonify({'error': 'Unauthorized access to user details'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({'error': f"Failed to get user: {str(e)}"}), 500

@users_bp.route('/<int:user_id>', methods=['PATCH'])
@requires_auth
@requires_role(['admin'])
def update_user(user_id):
    """Update a user by ID"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user fields
        if 'name' in data:
            user.name = data['name']
        
        if 'email' in data:
            # Check if email is already taken
            existing_user = User.query.filter(User.email == data['email']).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email is already in use'}), 409
            user.email = data['email']
        
        if 'role' in data:
            user.role = UserRole(data['role'])
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        db.session.commit()
        
        logger.info(f"Updated user {user_id}")
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({'error': f"Failed to update user: {str(e)}"}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@requires_auth
@requires_role(['admin'])
def delete_user(user_id):
    """Soft delete a user by ID"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Soft delete by setting is_active to False
        user.is_active = False
        db.session.commit()
        
        logger.info(f"Soft deleted user {user_id}")
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({'error': f"Failed to delete user: {str(e)}"}), 500

@users_bp.route('/me', methods=['GET'])
@requires_auth
def get_current_user():
    """Get the current user's information"""
    try:
        # Get user info from token
        user_info = get_user_info()
        
        # Find user in database
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            # User doesn't exist in the database, but we have Auth0 info
            return jsonify({
                'auth0_id': user_info.get('sub'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'exists_in_db': False
            }), 200
        
        # Return user data
        user_data = user.to_dict()
        user_data['exists_in_db'] = True
        
        return jsonify(user_data), 200
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({'error': f"Failed to get current user: {str(e)}"}), 500
