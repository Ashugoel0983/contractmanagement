import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from models import Approval, Contract, User, ApprovalStatus, ApprovalLevel, ContractStatus, UserRole, NotificationType
from services.notification_service import NotificationService
from auth import requires_auth, requires_role, get_user_info
from config import Config

logger = logging.getLogger(__name__)

approvals_bp = Blueprint('approvals', __name__)

# Initialize notification service
notification_service = NotificationService()

@approvals_bp.route('/pending', methods=['GET'])
@requires_auth
@requires_role(['admin', 'manager'])
def get_pending_approvals():
    """Get contracts pending approval"""
    try:
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Build query
        query = Approval.query.filter_by(status=ApprovalStatus.PENDING)
        
        # Role-based access control
        if user.role != UserRole.ADMIN:
            # For managers, only show approvals they're assigned to
            query = query.filter_by(approver_id=user.id)
        
        # Apply pagination
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Fetch approvals with related contract data
        approvals = query.order_by(Approval.created_at.desc()).limit(limit).offset(offset).all()
        
        # Prepare response
        result = {
            'approvals': [approval.to_dict() for approval in approvals],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {str(e)}")
        return jsonify({'error': f"Failed to get pending approvals: {str(e)}"}), 500

@approvals_bp.route('/<int:contract_id>/approve', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def approve_contract(contract_id):
    """Approve a contract"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if contract exists
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Check if contract is pending approval
        if contract.status != ContractStatus.PENDING_APPROVAL:
            return jsonify({'error': 'Contract is not pending approval'}), 400
        
        # Get approval for this contract
        approval = Approval.query.filter_by(
            contract_id=contract_id,
            status=ApprovalStatus.PENDING
        ).first()
        
        if not approval:
            return jsonify({'error': 'No pending approval found for this contract'}), 404
        
        # Check if user is authorized to approve this level
        if user.role != UserRole.ADMIN and approval.approver_id != user.id:
            return jsonify({'error': 'Unauthorized to approve this contract'}), 403
        
        # Get comments from request
        data = request.get_json() or {}
        comments = data.get('comments', '')
        
        # Update approval status
        approval.status = ApprovalStatus.APPROVED
        approval.comments = comments
        approval.updated_at = datetime.utcnow()
        
        # Update contract status
        contract.status = ContractStatus.ACTIVE
        contract.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification for contract approval
        notification_service.notify_contract_approval(
            contract_id=contract_id,
            status='approved',
            approver_name=user.name
        )
        
        logger.info(f"Contract {contract_id} approved by user {user.id}")
        return jsonify({'message': 'Contract approved successfully', 'approval': approval.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to approve contract: {str(e)}"}), 500

@approvals_bp.route('/<int:contract_id>/reject', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def reject_contract(contract_id):
    """Reject a contract with remarks"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if contract exists
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Check if contract is pending approval
        if contract.status != ContractStatus.PENDING_APPROVAL:
            return jsonify({'error': 'Contract is not pending approval'}), 400
        
        # Get approval for this contract
        approval = Approval.query.filter_by(
            contract_id=contract_id,
            status=ApprovalStatus.PENDING
        ).first()
        
        if not approval:
            return jsonify({'error': 'No pending approval found for this contract'}), 404
        
        # Check if user is authorized to reject this level
        if user.role != UserRole.ADMIN and approval.approver_id != user.id:
            return jsonify({'error': 'Unauthorized to reject this contract'}), 403
        
        # Get required rejection comments from request
        data = request.get_json() or {}
        comments = data.get('comments')
        
        if not comments:
            return jsonify({'error': 'Rejection reason is required'}), 400
        
        # Update approval status
        approval.status = ApprovalStatus.REJECTED
        approval.comments = comments
        approval.updated_at = datetime.utcnow()
        
        # Update contract status
        contract.status = ContractStatus.REJECTED
        contract.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification for contract rejection
        notification_service.notify_contract_approval(
            contract_id=contract_id,
            status='rejected',
            approver_name=user.name
        )
        
        logger.info(f"Contract {contract_id} rejected by user {user.id}")
        return jsonify({'message': 'Contract rejected', 'approval': approval.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to reject contract: {str(e)}"}), 500

@approvals_bp.route('/<int:contract_id>/submit', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def submit_for_approval(contract_id):
    """Submit a contract for approval"""
    try:
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if contract exists
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Check if contract is in draft status
        if contract.status != ContractStatus.DRAFT:
            return jsonify({'error': 'Only draft contracts can be submitted for approval'}), 400
        
        # Determine approval level based on contract value
        approval_level = ApprovalLevel.LEVEL1
        contract_value = contract.value or 0
        
        if contract_value > Config.APPROVAL_THRESHOLDS['level3']:
            approval_level = ApprovalLevel.LEVEL4
        elif contract_value > Config.APPROVAL_THRESHOLDS['level2']:
            approval_level = ApprovalLevel.LEVEL3
        elif contract_value > Config.APPROVAL_THRESHOLDS['level1']:
            approval_level = ApprovalLevel.LEVEL2
        
        # Find appropriate approver based on level
        # For now, assign to any manager or admin
        approver = None
        if approval_level in [ApprovalLevel.LEVEL1, ApprovalLevel.LEVEL2]:
            # Find a manager
            approver = User.query.filter_by(role=UserRole.MANAGER).first()
        
        if not approver or approval_level in [ApprovalLevel.LEVEL3, ApprovalLevel.LEVEL4]:
            # For higher levels or if no manager found, assign to admin
            approver = User.query.filter_by(role=UserRole.ADMIN).first()
        
        if not approver:
            return jsonify({'error': 'No suitable approver found'}), 500
        
        # Create approval record
        approval = Approval(
            contract_id=contract_id,
            approver_id=approver.id,
            level=approval_level,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Update contract status
        contract.status = ContractStatus.PENDING_APPROVAL
        contract.updated_at = datetime.utcnow()
        
        db.session.add(approval)
        db.session.commit()
        
        # Create notification for the approver
        notification_service.create_notification(
            user_id=approver.id,
            message=f"New contract requiring approval: {contract.title}",
            notification_type=NotificationType.APPROVAL,
            contract_id=contract_id,
            action_link=f"/approvals/{approval.id}"
        )
        
        logger.info(f"Contract {contract_id} submitted for approval by user {user.id}")
        return jsonify({'message': 'Contract submitted for approval', 'approval': approval.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting contract {contract_id} for approval: {str(e)}")
        return jsonify({'error': f"Failed to submit contract for approval: {str(e)}"}), 500

@approvals_bp.route('/<int:approval_id>', methods=['GET'])
@requires_auth
@requires_role(['admin', 'manager'])
def get_approval(approval_id):
    """Get an approval by ID"""
    try:
        approval = Approval.query.get(approval_id)
        if not approval:
            return jsonify({'error': 'Approval not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user.role != UserRole.ADMIN and approval.approver_id != user.id:
            return jsonify({'error': 'Unauthorized access to approval'}), 403
        
        return jsonify(approval.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting approval {approval_id}: {str(e)}")
        return jsonify({'error': f"Failed to get approval: {str(e)}"}), 500
