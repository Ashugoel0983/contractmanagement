import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from models import Invoice, Contract, User, UserRole
from services.invoice_service import InvoiceService
from services.notification_service import NotificationService
from auth import requires_auth, requires_role, get_user_info
from utils.validators import validate_invoice_data

logger = logging.getLogger(__name__)

invoices_bp = Blueprint('invoices', __name__)

# Initialize services
invoice_service = InvoiceService()
notification_service = NotificationService()

@invoices_bp.route('', methods=['GET'])
@requires_auth
def get_invoices():
    """Get all invoices with optional filtering"""
    try:
        # Parse query parameters
        contract_id = request.args.get('contract_id')
        status = request.args.get('status')
        is_recurring = request.args.get('is_recurring')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Build query
        query = Invoice.query
        
        # Apply filters if provided
        if contract_id:
            query = query.filter(Invoice.contract_id == contract_id)
        
        if status:
            query = query.filter(Invoice.status == status)
        
        if is_recurring is not None:
            is_recurring_bool = is_recurring.lower() == 'true'
            query = query.filter(Invoice.is_recurring == is_recurring_bool)
        
        if start_date:
            query = query.filter(Invoice.issue_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            query = query.filter(Invoice.issue_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        
        # Role-based access control
        if user and user.role != UserRole.ADMIN:
            # For non-admins, join with Contract to filter by owner
            query = query.join(Contract).filter(Contract.owner_id == user.id)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        invoices = query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset).all()
        
        result = {
            'invoices': [invoice.to_dict() for invoice in invoices],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting invoices: {str(e)}")
        return jsonify({'error': f"Failed to get invoices: {str(e)}"}), 500

@invoices_bp.route('/configure', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def configure_invoice():
    """Configure invoice for a contract"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['contract_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Missing required field: {field}"}), 400
        
        # Validate invoice data
        validation_errors = validate_invoice_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400
        
        # Get contract and check if it exists
        contract = Contract.query.get(data['contract_id'])
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized to configure invoice for this contract'}), 403
        
        # Create the invoice
        is_recurring = data.get('is_recurring', False)
        result = invoice_service.create_invoice(
            contract_id=data['contract_id'],
            amount=float(data['amount']),
            currency=data.get('currency', 'USD'),
            is_recurring=is_recurring,
            frequency=data.get('frequency'),
            template_type=data.get('template_type', 'standard'),
            payment_method=data.get('payment_method'),
            payment_notes=data.get('payment_notes'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        
        # Create notification
        notification_service.create_notification(
            user_id=user.id,
            message=f"Invoice configured for contract: {contract.title}",
            notification_type="invoice",
            contract_id=contract.id,
            action_link=f"/invoices/{result.id}"
        )
        
        logger.info(f"Configured invoice for contract {data['contract_id']}")
        return jsonify(result.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error configuring invoice: {str(e)}")
        return jsonify({'error': f"Failed to configure invoice: {str(e)}"}), 500

@invoices_bp.route('/<int:invoice_id>', methods=['GET'])
@requires_auth
def get_invoice(invoice_id):
    """Get an invoice by ID"""
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Get the associated contract
        contract = Contract.query.get(invoice.contract_id)
        if not contract:
            return jsonify({'error': 'Associated contract not found'}), 404
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized access to invoice'}), 403
        
        return jsonify(invoice.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting invoice {invoice_id}: {str(e)}")
        return jsonify({'error': f"Failed to get invoice: {str(e)}"}), 500

@invoices_bp.route('/<int:invoice_id>/regenerate', methods=['PUT'])
@requires_auth
@requires_role(['admin', 'manager'])
def regenerate_invoice(invoice_id):
    """Regenerate an invoice PDF"""
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Get the associated contract
        contract = Contract.query.get(invoice.contract_id)
        if not contract:
            return jsonify({'error': 'Associated contract not found'}), 404
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized to regenerate this invoice'}), 403
        
        # Update invoice fields if provided in request
        data = request.get_json() or {}
        
        if 'amount' in data:
            invoice.amount = float(data['amount'])
        
        if 'currency' in data:
            invoice.currency = data['currency']
        
        if 'payment_method' in data:
            invoice.payment_method = data['payment_method']
        
        if 'payment_notes' in data:
            invoice.payment_notes = data['payment_notes']
        
        if 'template_type' in data:
            invoice.template_type = data['template_type']
        
        # Update status to regenerated
        invoice.status = 'draft'
        invoice.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Regenerated invoice {invoice_id}")
        return jsonify(invoice.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating invoice {invoice_id}: {str(e)}")
        return jsonify({'error': f"Failed to regenerate invoice: {str(e)}"}), 500

@invoices_bp.route('/<int:invoice_id>/status', methods=['PUT'])
@requires_auth
@requires_role(['admin', 'manager'])
def update_invoice_status(invoice_id):
    """Update the status of an invoice"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'No status provided'}), 400
        
        # Validate status
        status = data['status']
        if status not in ['draft', 'sent', 'paid', 'overdue']:
            return jsonify({'error': 'Invalid status. Allowed values: draft, sent, paid, overdue'}), 400
        
        # Update invoice status
        result = invoice_service.update_invoice_status(invoice_id, status)
        
        logger.info(f"Updated invoice {invoice_id} status to {status}")
        return jsonify(result.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating invoice status: {str(e)}")
        return jsonify({'error': f"Failed to update invoice status: {str(e)}"}), 500

@invoices_bp.route('/check-overdue', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def check_overdue_invoices():
    """Check for overdue invoices and update their status"""
    try:
        overdue_invoices = invoice_service.check_overdue_invoices()
        
        # Create notifications for overdue invoices
        notification_count = notification_service.check_overdue_invoices()
        
        result = {
            'overdue_invoices': len(overdue_invoices),
            'notifications_created': notification_count
        }
        
        logger.info(f"Checked for overdue invoices, found {len(overdue_invoices)}")
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error checking overdue invoices: {str(e)}")
        return jsonify({'error': f"Failed to check overdue invoices: {str(e)}"}), 500
