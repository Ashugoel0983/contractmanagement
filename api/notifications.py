import logging
from flask import Blueprint, request, jsonify
from app import db
from models import Notification, User, NotificationType
from services.notification_service import NotificationService
from auth import requires_auth, get_user_info

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__)

# Initialize notification service
notification_service = NotificationService()

@notifications_bp.route('', methods=['GET'])
@requires_auth
def get_notifications():
    """Get notifications for the current user"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse query parameters
        notification_type = request.args.get('type')
        if notification_type:
            try:
                notification_type = NotificationType(notification_type)
            except ValueError:
                return jsonify({'error': f"Invalid notification type: {notification_type}"}), 400
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get notifications for user
        notifications = notification_service.get_notifications_for_user(
            user_id=user.id,
            notification_type=notification_type,
            limit=limit,
            offset=offset
        )
        
        # Count total unread notifications
        unread_count = Notification.query.filter_by(
            user_id=user.id,
            is_read=False
        ).count()
        
        result = {
            'notifications': [notification.to_dict() for notification in notifications],
            'unread_count': unread_count,
            'pagination': {
                'limit': limit,
                'offset': offset
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'error': f"Failed to get notifications: {str(e)}"}), 500

@notifications_bp.route('/mark-read/<int:notification_id>', methods=['PUT'])
@requires_auth
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Mark notification as read
        result = notification_service.mark_as_read(notification_id, user.id)
        
        if result:
            return jsonify({'message': 'Notification marked as read'}), 200
        else:
            return jsonify({'error': 'Failed to mark notification as read'}), 400
        
    except ValueError as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return jsonify({'error': f"Failed to mark notification as read: {str(e)}"}), 500

@notifications_bp.route('/mark-all-read', methods=['PUT'])
@requires_auth
def mark_all_notifications_read():
    """Mark all notifications for the current user as read"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Mark all notifications as read
        count = notification_service.mark_all_as_read(user.id)
        
        return jsonify({'message': f"Marked {count} notifications as read"}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({'error': f"Failed to mark all notifications as read: {str(e)}"}), 500

@notifications_bp.route('/check-expiring-contracts', methods=['POST'])
@requires_auth
def check_expiring_contracts():
    """Check for contracts expiring soon and create notifications"""
    try:
        # Get threshold from request or use default
        data = request.get_json() or {}
        days_threshold = int(data.get('days_threshold', 30))
        
        # Check for expiring contracts
        count = notification_service.check_expiring_contracts(days_threshold)
        
        return jsonify({
            'message': f"Checked for expiring contracts",
            'notifications_created': count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error checking expiring contracts: {str(e)}")
        return jsonify({'error': f"Failed to check expiring contracts: {str(e)}"}), 500

@notifications_bp.route('', methods=['POST'])
@requires_auth
def create_notification():
    """Create a new notification (for testing purposes)"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get notification data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['message', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Missing required field: {field}"}), 400
        
        # Create notification
        notification = notification_service.create_notification(
            user_id=user.id,
            message=data['message'],
            notification_type=NotificationType(data['type']),
            contract_id=data.get('contract_id'),
            action_link=data.get('action_link')
        )
        
        return jsonify(notification.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notification: {str(e)}")
        return jsonify({'error': f"Failed to create notification: {str(e)}"}), 500
