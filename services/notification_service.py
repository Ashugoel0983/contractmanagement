"""
Notification Service for Contract Management System
Handles creating and managing notifications for contracts, users, and system events
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        """Initialize notification service"""
        logger.info("Notification service initialized")
    
    def create_notification(self, user_id, message, notification_type, contract_id=None, action_link=None):
        """
        Create a new notification
        Args:
            user_id: ID of the user to notify
            message: Notification message
            notification_type: Type of notification (expiry, invoice, approval, system)
            contract_id: Optional contract ID associated with notification
            action_link: Optional link for the user to take action
        Returns:
            dict: Created notification
        """
        try:
            from app import db
            from models import Notification, NotificationType
            
            # Create notification object
            notification = Notification(
                user_id=user_id,
                contract_id=contract_id,
                type=getattr(NotificationType, notification_type.upper(), NotificationType.SYSTEM),
                message=message,
                is_read=False,
                action_link=action_link,
                created_at=datetime.utcnow()
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Created notification for user {user_id}: {message}")
            return notification.to_dict()
        
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            # Don't raise the exception, as notifications are not critical
            return None
    
    def mark_as_read(self, notification_id):
        """
        Mark a notification as read
        Args:
            notification_id: ID of the notification to mark as read
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from app import db
            from models import Notification
            
            notification = Notification.query.get(notification_id)
            if not notification:
                logger.warning(f"Notification not found: {notification_id}")
                return False
            
            notification.is_read = True
            db.session.commit()
            
            logger.info(f"Marked notification {notification_id} as read")
            return True
        
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    def mark_all_as_read(self, user_id):
        """
        Mark all notifications for a user as read
        Args:
            user_id: ID of the user
        Returns:
            int: Number of notifications marked as read
        """
        try:
            from app import db
            from models import Notification
            
            # Find all unread notifications for the user
            notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
            
            # Mark each as read
            count = 0
            for notification in notifications:
                notification.is_read = True
                count += 1
            
            db.session.commit()
            
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
        
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0
    
    def get_user_notifications(self, user_id, limit=50, include_read=False):
        """
        Get notifications for a user
        Args:
            user_id: ID of the user
            limit: Maximum number of notifications to return
            include_read: Whether to include read notifications
        Returns:
            list: List of notifications
        """
        try:
            from models import Notification
            
            # Query notifications
            query = Notification.query.filter_by(user_id=user_id)
            
            if not include_read:
                query = query.filter_by(is_read=False)
            
            # Order by created_at descending (newest first)
            query = query.order_by(Notification.created_at.desc())
            
            # Limit the number of results
            query = query.limit(limit)
            
            # Execute query
            notifications = query.all()
            
            # Convert to dictionaries
            result = [notification.to_dict() for notification in notifications]
            
            logger.info(f"Retrieved {len(result)} notifications for user {user_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []
    
    def delete_notification(self, notification_id):
        """
        Delete a notification
        Args:
            notification_id: ID of the notification to delete
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from app import db
            from models import Notification
            
            notification = Notification.query.get(notification_id)
            if not notification:
                logger.warning(f"Notification not found: {notification_id}")
                return False
            
            db.session.delete(notification)
            db.session.commit()
            
            logger.info(f"Deleted notification {notification_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return False
    
    def check_expiring_contracts(self, days_threshold=30):
        """
        Check for contracts expiring soon and create notifications
        Args:
            days_threshold: Number of days before expiry to create notifications
        Returns:
            int: Number of notifications created
        """
        try:
            from app import db
            from models import Contract, ContractStatus, Notification, NotificationType
            
            # Calculate the date threshold
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            # Find active contracts expiring before the threshold
            expiring_contracts = Contract.query.filter(
                Contract.status == ContractStatus.ACTIVE,
                Contract.end_date <= threshold_date,
                Contract.end_date > datetime.utcnow()
            ).all()
            
            count = 0
            for contract in expiring_contracts:
                # Check if notification already exists
                existing = Notification.query.filter_by(
                    contract_id=contract.id,
                    type=NotificationType.EXPIRY,
                    is_read=False
                ).first()
                
                if not existing:
                    # Create new notification
                    days_remaining = (contract.end_date - datetime.utcnow()).days
                    message = f"Contract '{contract.title}' is expiring in {days_remaining} days"
                    
                    notification = Notification(
                        user_id=contract.owner_id,
                        contract_id=contract.id,
                        type=NotificationType.EXPIRY,
                        message=message,
                        is_read=False,
                        action_link=f"/contracts/{contract.id}",
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(notification)
                    count += 1
            
            if count > 0:
                db.session.commit()
                logger.info(f"Created {count} contract expiry notifications")
            
            return count
        
        except Exception as e:
            logger.error(f"Error checking expiring contracts: {str(e)}")
            return 0
    
    def check_overdue_invoices(self):
        """
        Check for overdue invoices and create notifications
        Returns:
            int: Number of notifications created
        """
        try:
            from app import db
            from models import Invoice, Contract, Notification, NotificationType
            
            # Find invoices that are overdue but not marked as such
            overdue_invoices = Invoice.query.filter(
                Invoice.status != 'overdue',
                Invoice.due_date < datetime.utcnow()
            ).all()
            
            count = 0
            for invoice in overdue_invoices:
                # Update invoice status
                invoice.status = 'overdue'
                
                # Get the contract for the invoice
                contract = Contract.query.get(invoice.contract_id)
                if not contract:
                    continue
                
                # Create notification for contract owner
                message = f"Invoice #{invoice.invoice_number} for contract '{contract.title}' is overdue"
                
                notification = Notification(
                    user_id=contract.owner_id,
                    contract_id=contract.id,
                    type=NotificationType.INVOICE,
                    message=message,
                    is_read=False,
                    action_link=f"/invoices/{invoice.id}",
                    created_at=datetime.utcnow()
                )
                
                db.session.add(notification)
                count += 1
            
            if count > 0:
                db.session.commit()
                logger.info(f"Created {count} overdue invoice notifications")
            
            return count
        
        except Exception as e:
            logger.error(f"Error checking overdue invoices: {str(e)}")
            return 0
    
    def create_approval_notification(self, approval):
        """
        Create a notification for a new approval request
        Args:
            approval: The approval object
        Returns:
            dict: Created notification or None
        """
        try:
            from app import db
            from models import Contract, Notification, NotificationType
            
            # Get the contract
            contract = Contract.query.get(approval.contract_id)
            if not contract:
                logger.warning(f"Contract not found for approval: {approval.id}")
                return None
            
            # Create notification message
            message = f"New approval request for contract '{contract.title}'"
            
            # Create notification for the approver
            notification = Notification(
                user_id=approval.approver_id,
                contract_id=contract.id,
                type=NotificationType.APPROVAL,
                message=message,
                is_read=False,
                action_link=f"/approvals/{approval.id}",
                created_at=datetime.utcnow()
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Created approval notification for user {approval.approver_id}")
            return notification.to_dict()
        
        except Exception as e:
            logger.error(f"Error creating approval notification: {str(e)}")
            return None
    
    def create_approval_status_notification(self, approval):
        """
        Create a notification for an approval status change
        Args:
            approval: The approval object
        Returns:
            dict: Created notification or None
        """
        try:
            from app import db
            from models import Contract, Notification, NotificationType, ApprovalStatus
            
            # Get the contract
            contract = Contract.query.get(approval.contract_id)
            if not contract:
                logger.warning(f"Contract not found for approval: {approval.id}")
                return None
            
            # Only create notifications for approved or rejected statuses
            if approval.status not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
                return None
            
            # Create notification message
            status_text = "approved" if approval.status == ApprovalStatus.APPROVED else "rejected"
            message = f"Contract '{contract.title}' has been {status_text}"
            if approval.comments:
                message += f". Comments: {approval.comments}"
            
            # Create notification for the contract owner
            notification = Notification(
                user_id=contract.owner_id,
                contract_id=contract.id,
                type=NotificationType.APPROVAL,
                message=message,
                is_read=False,
                action_link=f"/contracts/{contract.id}",
                created_at=datetime.utcnow()
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Created approval status notification for user {contract.owner_id}")
            return notification.to_dict()
        
        except Exception as e:
            logger.error(f"Error creating approval status notification: {str(e)}")
            return None