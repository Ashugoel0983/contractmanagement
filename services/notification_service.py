import logging
from datetime import datetime, timedelta
from models import Notification, Contract, Invoice, User, NotificationType
from app import db

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        """Initialize the notification service"""
        logger.info("Notification service initialized")

    def create_notification(self, user_id, message, notification_type, contract_id=None, action_link=None):
        """
        Create a new notification
        Args:
            user_id: ID of the user
            message: Notification message
            notification_type: Type of notification (enum value)
            contract_id: Optional contract ID
            action_link: Optional action link
        Returns:
            Notification: The created notification object
        """
        try:
            notification = Notification(
                user_id=user_id,
                message=message,
                type=notification_type,
                contract_id=contract_id,
                action_link=action_link,
                is_read=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Created notification for user {user_id}: {message}")
            return notification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating notification: {str(e)}")
            raise

    def mark_as_read(self, notification_id, user_id):
        """
        Mark a notification as read
        Args:
            notification_id: ID of the notification
            user_id: ID of the user
        Returns:
            bool: True if successful
        """
        try:
            notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
            if not notification:
                raise ValueError(f"Notification not found or not owned by user")
            
            notification.is_read = True
            db.session.commit()
            
            logger.info(f"Marked notification {notification_id} as read")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking notification as read: {str(e)}")
            raise

    def mark_all_as_read(self, user_id):
        """
        Mark all notifications for a user as read
        Args:
            user_id: ID of the user
        Returns:
            int: Number of notifications marked as read
        """
        try:
            result = db.session.query(Notification).filter_by(
                user_id=user_id, is_read=False
            ).update({Notification.is_read: True})
            
            db.session.commit()
            
            logger.info(f"Marked {result} notifications as read for user {user_id}")
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking all notifications as read: {str(e)}")
            raise

    def get_notifications_for_user(self, user_id, notification_type=None, limit=50, offset=0):
        """
        Get notifications for a user
        Args:
            user_id: ID of the user
            notification_type: Optional filter by notification type
            limit: Max number of notifications to return
            offset: Offset for pagination
        Returns:
            list: List of notifications
        """
        try:
            query = Notification.query.filter_by(user_id=user_id)
            
            if notification_type:
                query = query.filter_by(type=notification_type)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset).all()
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            raise

    def check_expiring_contracts(self, days_threshold=30):
        """
        Check for contracts expiring within the threshold and create notifications
        Args:
            days_threshold: Days before expiry to send notification
        Returns:
            int: Number of notifications created
        """
        try:
            today = datetime.utcnow().date()
            threshold_date = today + timedelta(days=days_threshold)
            
            # Find contracts expiring soon
            expiring_contracts = Contract.query.filter(
                Contract.end_date <= threshold_date,
                Contract.end_date >= today
            ).all()
            
            notification_count = 0
            
            for contract in expiring_contracts:
                # Check if notification already exists
                existing = Notification.query.filter_by(
                    contract_id=contract.id,
                    type=NotificationType.EXPIRY
                ).filter(
                    Notification.created_at >= datetime.utcnow() - timedelta(days=7)
                ).first()
                
                if existing:
                    continue
                
                # Find users who should be notified (owner and admins/managers)
                users_to_notify = [contract.owner]
                admin_users = User.query.filter(User.role.in_(['admin', 'manager'])).all()
                users_to_notify.extend(admin_users)
                
                # Remove duplicates
                users_to_notify = list(set(users_to_notify))
                
                # Calculate days until expiry
                days_until_expiry = (contract.end_date - today).days
                
                # Create notification for each user
                for user in users_to_notify:
                    if not user:
                        continue
                        
                    message = f"Contract Expiring Soon: {contract.title} expires in {days_until_expiry} days"
                    self.create_notification(
                        user_id=user.id,
                        message=message,
                        notification_type=NotificationType.EXPIRY,
                        contract_id=contract.id,
                        action_link=f"/contracts/{contract.id}"
                    )
                    notification_count += 1
            
            logger.info(f"Created {notification_count} contract expiry notifications")
            return notification_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error checking expiring contracts: {str(e)}")
            raise

    def check_overdue_invoices(self):
        """
        Check for overdue invoices and create notifications
        Returns:
            int: Number of notifications created
        """
        try:
            today = datetime.utcnow().date()
            
            # Find overdue invoices
            overdue_invoices = Invoice.query.filter(
                Invoice.status.in_(["sent", "draft"]),
                Invoice.due_date < today
            ).all()
            
            notification_count = 0
            
            for invoice in overdue_invoices:
                # Check if notification already exists
                existing = Notification.query.filter_by(
                    contract_id=invoice.contract_id,
                    type=NotificationType.INVOICE
                ).filter(
                    Notification.created_at >= datetime.utcnow() - timedelta(days=2)
                ).first()
                
                if existing:
                    continue
                
                # Find users who should be notified
                contract = Contract.query.get(invoice.contract_id)
                if not contract:
                    continue
                    
                users_to_notify = [contract.owner]
                admin_users = User.query.filter(User.role.in_(['admin', 'manager'])).all()
                users_to_notify.extend(admin_users)
                
                # Remove duplicates
                users_to_notify = list(set(users_to_notify))
                
                # Calculate days overdue
                days_overdue = (today - invoice.due_date).days
                
                # Create notification for each user
                for user in users_to_notify:
                    if not user:
                        continue
                        
                    message = f"Invoice Overdue: Payment for {invoice.invoice_number} is {days_overdue} days overdue"
                    self.create_notification(
                        user_id=user.id,
                        message=message,
                        notification_type=NotificationType.INVOICE,
                        contract_id=invoice.contract_id,
                        action_link=f"/invoices/{invoice.id}"
                    )
                    notification_count += 1
            
            logger.info(f"Created {notification_count} overdue invoice notifications")
            return notification_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error checking overdue invoices: {str(e)}")
            raise

    def notify_contract_approval(self, contract_id, status, approver_name):
        """
        Create notification for contract approval status change
        Args:
            contract_id: ID of the contract
            status: Approval status (approved, rejected)
            approver_name: Name of the approver
        Returns:
            int: Number of notifications created
        """
        try:
            contract = Contract.query.get(contract_id)
            if not contract:
                raise ValueError(f"Contract not found: {contract_id}")
            
            # Find users who should be notified
            users_to_notify = [contract.owner]
            admin_users = User.query.filter(User.role.in_(['admin', 'manager'])).all()
            users_to_notify.extend(admin_users)
            
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            
            notification_count = 0
            
            # Create notification for each user
            for user in users_to_notify:
                if not user:
                    continue
                    
                message = f"Contract {status.capitalize()}: {contract.title} has been {status} by {approver_name}"
                self.create_notification(
                    user_id=user.id,
                    message=message,
                    notification_type=NotificationType.APPROVAL,
                    contract_id=contract.id,
                    action_link=f"/contracts/{contract.id}"
                )
                notification_count += 1
            
            logger.info(f"Created {notification_count} contract approval notifications")
            return notification_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating approval notifications: {str(e)}")
            raise
