import logging
from flask import Blueprint, request, jsonify
from app import db
from models import User, UserRole
from auth import requires_auth, requires_role, get_user_info

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)

# Default role access matrix
DEFAULT_ROLE_MATRIX = {
    'admin': {
        'contracts': ['view', 'create', 'edit', 'delete', 'approve'],
        'invoices': ['view', 'create', 'edit', 'delete'],
        'users': ['view', 'create', 'edit', 'delete'],
        'approvals': ['view', 'approve', 'reject'],
        'settings': ['view', 'edit']
    },
    'manager': {
        'contracts': ['view', 'create', 'edit', 'approve'],
        'invoices': ['view', 'create', 'edit'],
        'users': ['view'],
        'approvals': ['view', 'approve', 'reject'],
        'settings': ['view']
    },
    'user': {
        'contracts': ['view'],
        'invoices': ['view'],
        'users': [],
        'approvals': [],
        'settings': []
    }
}

@settings_bp.route('/roles', methods=['GET'])
@requires_auth
@requires_role(['admin'])
def get_role_access_matrix():
    """Get the role access matrix"""
    try:
        # For now, return the default role matrix
        # In a real implementation, this could be stored in the database
        return jsonify(DEFAULT_ROLE_MATRIX), 200
        
    except Exception as e:
        logger.error(f"Error getting role access matrix: {str(e)}")
        return jsonify({'error': f"Failed to get role access matrix: {str(e)}"}), 500

@settings_bp.route('/roles', methods=['PUT'])
@requires_auth
@requires_role(['admin'])
def update_role_matrix():
    """Update the role access matrix"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate role matrix structure
        required_roles = ['admin', 'manager', 'user']
        for role in required_roles:
            if role not in data:
                return jsonify({'error': f"Missing required role: {role}"}), 400
        
        # In a real implementation, update the role matrix in the database
        # For now, just acknowledge the update
        return jsonify({
            'message': 'Role access matrix updated successfully',
            'updated_matrix': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating role access matrix: {str(e)}")
        return jsonify({'error': f"Failed to update role access matrix: {str(e)}"}), 500

@settings_bp.route('/user-preferences', methods=['GET'])
@requires_auth
def get_user_preferences():
    """Get the current user's preferences"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # In a real implementation, get preferences from database
        # For now, return default preferences
        preferences = {
            'notifications': {
                'email': True,
                'in_app': True
            },
            'ui': {
                'theme': 'light',
                'language': 'en',
                'dashboard_widgets': ['contracts', 'invoices', 'approvals']
            }
        }
        
        return jsonify(preferences), 200
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {str(e)}")
        return jsonify({'error': f"Failed to get user preferences: {str(e)}"}), 500

@settings_bp.route('/user-preferences', methods=['PUT'])
@requires_auth
def update_user_preferences():
    """Update the current user's preferences"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # In a real implementation, update preferences in database
        # For now, just acknowledge the update
        return jsonify({
            'message': 'User preferences updated successfully',
            'updated_preferences': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        return jsonify({'error': f"Failed to update user preferences: {str(e)}"}), 500

@settings_bp.route('/organization', methods=['GET'])
@requires_auth
@requires_role(['admin'])
def get_organization_settings():
    """Get organization settings"""
    try:
        # In a real implementation, get organization settings from database
        # For now, return default settings
        settings = {
            'organization_name': 'Febi',
            'logo_url': '/assets/logo.svg',
            'primary_color': '#5664d2',
            'date_format': 'YYYY-MM-DD',
            'currency': 'USD',
            'invoice_prefix': 'INV-',
            'contract_prefix': 'CONT-',
            'fiscal_year_start': '01-01',
            'default_payment_terms': 'Net 30'
        }
        
        return jsonify(settings), 200
        
    except Exception as e:
        logger.error(f"Error getting organization settings: {str(e)}")
        return jsonify({'error': f"Failed to get organization settings: {str(e)}"}), 500

@settings_bp.route('/organization', methods=['PUT'])
@requires_auth
@requires_role(['admin'])
def update_organization_settings():
    """Update organization settings"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # In a real implementation, update settings in database
        # For now, just acknowledge the update
        return jsonify({
            'message': 'Organization settings updated successfully',
            'updated_settings': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating organization settings: {str(e)}")
        return jsonify({'error': f"Failed to update organization settings: {str(e)}"}), 500
