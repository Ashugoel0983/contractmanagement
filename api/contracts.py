import os
import logging
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from app import db
from models import Contract, ContractParty, ContractMetadata, ContractStatus, ContractType, Invoice, User, UserRole
from services.ocr_service import OCRService
from services.ai_service import AIService
from services.storage_service import StorageService
from services.notification_service import NotificationService
from auth import requires_auth, requires_role, get_user_info
from utils.validators import validate_contract_data
from utils.helpers import generate_contract_number, parse_date

logger = logging.getLogger(__name__)

contracts_bp = Blueprint('contracts', __name__)

# Initialize services
ocr_service = OCRService()
ai_service = AIService()
storage_service = StorageService()
notification_service = NotificationService()

@contracts_bp.route('', methods=['GET'])
@requires_auth
def get_contracts():
    """Get all contracts with optional filtering"""
    try:
        # Parse query parameters
        status = request.args.get('status')
        contract_type = request.args.get('contract_type')
        owner_id = request.args.get('owner_id')
        search = request.args.get('search')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Build query
        query = Contract.query
        
        # Apply filters if provided
        if status:
            query = query.filter(Contract.status == ContractStatus(status))
        
        if contract_type:
            query = query.filter(Contract.contract_type == ContractType(contract_type))
        
        if owner_id:
            query = query.filter(Contract.owner_id == owner_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Contract.title.ilike(search_term),
                    Contract.description.ilike(search_term),
                    Contract.contract_number.ilike(search_term)
                )
            )
        
        # Role-based access control
        if user and user.role != UserRole.ADMIN:
            # Non-admins can only see contracts they own
            query = query.filter(Contract.owner_id == user.id)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        contracts = query.order_by(Contract.created_at.desc()).limit(limit).offset(offset).all()
        
        result = {
            'contracts': [contract.to_dict() for contract in contracts],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting contracts: {str(e)}")
        return jsonify({'error': f"Failed to get contracts: {str(e)}"}), 500

@contracts_bp.route('', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def create_contract():
    """Create a new contract"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get contract data from form
        contract_data = {
            'title': request.form.get('title'),
            'contract_type': request.form.get('contract_type'),
            'description': request.form.get('description'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'value': request.form.get('value'),
            'currency': request.form.get('currency', 'USD'),
            'payment_terms': request.form.get('payment_terms'),
            'tags': request.form.get('tags', '').split(',') if request.form.get('tags') else []
        }
        
        # Validate contract data
        validation_errors = validate_contract_data(contract_data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400
        
        # Get user info
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Save the file
        file_path = storage_service.save_file(file)
        
        # Process the file with OCR
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.seek(0)
            temp_file.write(file.read())
            temp_file_path = temp_file.name
        
        try:
            extracted_text = ocr_service.process_file(temp_file_path)
        finally:
            os.unlink(temp_file_path)
        
        # Create the contract
        contract = Contract(
            contract_number=generate_contract_number(),
            title=contract_data['title'],
            contract_type=ContractType(contract_data['contract_type']),
            status=ContractStatus.DRAFT,
            description=contract_data['description'],
            start_date=parse_date(contract_data['start_date']),
            end_date=parse_date(contract_data['end_date']),
            value=float(contract_data['value']) if contract_data['value'] else None,
            currency=contract_data['currency'],
            payment_terms=contract_data['payment_terms'],
            owner_id=user.id,
            file_path=file_path,
            extracted_text=extracted_text,
            tags=contract_data['tags'],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(contract)
        db.session.commit()
        
        # Create contract metadata
        metadata = ContractMetadata(
            contract_id=contract.id,
            invoice_required=request.form.get('invoice_required') == 'true',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(metadata)
        db.session.commit()
        
        logger.info(f"Created contract {contract.id}: {contract.title}")
        return jsonify(contract.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating contract: {str(e)}")
        return jsonify({'error': f"Failed to create contract: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>', methods=['GET'])
@requires_auth
def get_contract(contract_id):
    """Get a contract by ID"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user and user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized access to contract'}), 403
        
        # Get contract metadata
        metadata = ContractMetadata.query.filter_by(contract_id=contract_id).first()
        
        # Get contract parties
        parties = ContractParty.query.filter_by(contract_id=contract_id).all()
        
        # Get invoices
        invoices = Invoice.query.filter_by(contract_id=contract_id).order_by(Invoice.created_at.desc()).all()
        
        result = contract.to_dict()
        result['metadata'] = metadata.to_dict() if metadata else {}
        result['parties'] = [party.to_dict() for party in parties]
        result['invoices'] = [invoice.to_dict() for invoice in invoices]
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to get contract: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>', methods=['PUT'])
@requires_auth
@requires_role(['admin', 'manager'])
def update_contract(contract_id):
    """Update a contract by ID"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate contract data
        validation_errors = validate_contract_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized to update this contract'}), 403
        
        # Update contract fields
        if 'title' in data:
            contract.title = data['title']
        
        if 'contract_type' in data:
            contract.contract_type = ContractType(data['contract_type'])
        
        if 'description' in data:
            contract.description = data['description']
        
        if 'start_date' in data:
            contract.start_date = parse_date(data['start_date'])
        
        if 'end_date' in data:
            contract.end_date = parse_date(data['end_date'])
        
        if 'value' in data:
            contract.value = float(data['value']) if data['value'] else None
        
        if 'currency' in data:
            contract.currency = data['currency']
        
        if 'payment_terms' in data:
            contract.payment_terms = data['payment_terms']
        
        if 'tags' in data:
            contract.tags = data['tags']
        
        if 'status' in data:
            contract.status = ContractStatus(data['status'])
        
        contract.updated_at = datetime.utcnow()
        
        # Update metadata if provided
        if 'metadata' in data:
            metadata = ContractMetadata.query.filter_by(contract_id=contract_id).first()
            if metadata:
                # Update existing metadata fields
                if 'invoice_required' in data['metadata']:
                    metadata.invoice_required = data['metadata']['invoice_required']
                
                if 'jurisdiction' in data['metadata']:
                    metadata.jurisdiction = data['metadata']['jurisdiction']
                
                if 'governing_law' in data['metadata']:
                    metadata.governing_law = data['metadata']['governing_law']
                
                if 'dispute_resolution' in data['metadata']:
                    metadata.dispute_resolution = data['metadata']['dispute_resolution']
                
                if 'termination_clause' in data['metadata']:
                    metadata.termination_clause = data['metadata']['termination_clause']
                
                if 'confidentiality_clause' in data['metadata']:
                    metadata.confidentiality_clause = data['metadata']['confidentiality_clause']
                
                if 'limitation_of_liability' in data['metadata']:
                    metadata.limitation_of_liability = data['metadata']['limitation_of_liability']
                
                if 'force_majeure' in data['metadata']:
                    metadata.force_majeure = data['metadata']['force_majeure']
                
                if 'indemnification' in data['metadata']:
                    metadata.indemnification = data['metadata']['indemnification']
                
                metadata.updated_at = datetime.utcnow()
            else:
                # Create new metadata if it doesn't exist
                metadata = ContractMetadata(
                    contract_id=contract_id,
                    invoice_required=data['metadata'].get('invoice_required', False),
                    jurisdiction=data['metadata'].get('jurisdiction'),
                    governing_law=data['metadata'].get('governing_law'),
                    dispute_resolution=data['metadata'].get('dispute_resolution'),
                    termination_clause=data['metadata'].get('termination_clause'),
                    confidentiality_clause=data['metadata'].get('confidentiality_clause'),
                    limitation_of_liability=data['metadata'].get('limitation_of_liability'),
                    force_majeure=data['metadata'].get('force_majeure'),
                    indemnification=data['metadata'].get('indemnification'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(metadata)
        
        # Update parties if provided
        if 'parties' in data:
            # Delete existing parties
            ContractParty.query.filter_by(contract_id=contract_id).delete()
            
            # Add new parties
            for party_data in data['parties']:
                party = ContractParty(
                    contract_id=contract_id,
                    party_type=party_data.get('party_type'),
                    legal_name=party_data.get('legal_name'),
                    address=party_data.get('address'),
                    contact_person=party_data.get('contact_person'),
                    email=party_data.get('email'),
                    phone=party_data.get('phone'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(party)
        
        db.session.commit()
        logger.info(f"Updated contract {contract_id}")
        
        return jsonify(contract.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to update contract: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>', methods=['DELETE'])
@requires_auth
@requires_role(['admin'])
def delete_contract(contract_id):
    """Delete a contract by ID"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Check if contract has invoices
        invoices = Invoice.query.filter_by(contract_id=contract_id).first()
        if invoices:
            return jsonify({'error': 'Cannot delete contract with associated invoices'}), 400
        
        # Delete the contract file
        if contract.file_path:
            storage_service.delete_file(contract.file_path)
        
        # Delete the contract
        db.session.delete(contract)
        db.session.commit()
        
        logger.info(f"Deleted contract {contract_id}")
        return jsonify({'message': 'Contract deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to delete contract: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>/extract', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def extract_contract_data(contract_id):
    """Extract data from a contract using AI"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        if not contract.extracted_text:
            return jsonify({'error': 'No extracted text available for this contract'}), 400
        
        # Extract data from the contract text using AI
        extracted_data = ai_service.extract_contract_data(contract.extracted_text)
        
        # Calculate risk score
        risk_score = ai_service.calculate_risk_score(extracted_data)
        
        # Update contract with extracted data
        if extracted_data.get('contract_title'):
            contract.title = extracted_data['contract_title']
        
        if extracted_data.get('contract_type'):
            try:
                contract.contract_type = ContractType(extracted_data['contract_type'])
            except ValueError:
                # Use default if type is not recognized
                pass
        
        if extracted_data.get('start_date'):
            contract.start_date = parse_date(extracted_data['start_date'])
        
        if extracted_data.get('end_date'):
            contract.end_date = parse_date(extracted_data['end_date'])
        
        if extracted_data.get('total_value'):
            contract.value = extracted_data['total_value']
        
        if extracted_data.get('payment_terms'):
            contract.payment_terms = extracted_data['payment_terms']
        
        # Update contract metadata
        metadata = ContractMetadata.query.filter_by(contract_id=contract_id).first()
        if not metadata:
            metadata = ContractMetadata(
                contract_id=contract_id,
                created_at=datetime.utcnow()
            )
            db.session.add(metadata)
        
        # Add clauses and risk flags to metadata
        if extracted_data.get('clauses'):
            metadata.termination_clause = extracted_data['clauses'].get('termination')
            metadata.confidentiality_clause = extracted_data['clauses'].get('confidentiality')
            metadata.limitation_of_liability = extracted_data['clauses'].get('limitation_of_liability')
            metadata.force_majeure = extracted_data['clauses'].get('force_majeure')
            metadata.indemnification = extracted_data['clauses'].get('indemnification')
            
            if extracted_data['clauses'].get('jurisdiction'):
                metadata.jurisdiction = extracted_data['clauses']['jurisdiction']
            
            if extracted_data['clauses'].get('governing_law'):
                metadata.governing_law = extracted_data['clauses']['governing_law']
        
        # Add risk flags
        if extracted_data.get('risk_flags'):
            metadata.risk_flags = {'flags': extracted_data['risk_flags']}
            
            # If high risk, update contract status
            if risk_score > 70:
                contract.status = ContractStatus.RISK_FLAGGED
        
        metadata.ai_confidence_score = risk_score / 100.0  # Convert to 0-1 scale
        metadata.updated_at = datetime.utcnow()
        
        # Add parties if found
        if extracted_data.get('parties'):
            # Clear existing parties
            ContractParty.query.filter_by(contract_id=contract_id).delete()
            
            for i, party_name in enumerate(extracted_data['parties']):
                party = ContractParty(
                    contract_id=contract_id,
                    party_type='our_company' if i == 0 else 'counterparty',
                    legal_name=party_name,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(party)
        
        contract.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Extracted data for contract {contract_id}")
        
        # Return the extracted data and confidence score
        result = {
            'extracted_data': extracted_data,
            'confidence_score': metadata.ai_confidence_score,
            'risk_score': risk_score
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error extracting data for contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to extract contract data: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>/extracted', methods=['GET'])
@requires_auth
def get_extracted_data(contract_id):
    """Get extracted structured data for a contract"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized access to contract'}), 403
        
        # Get contract metadata
        metadata = ContractMetadata.query.filter_by(contract_id=contract_id).first()
        if not metadata:
            return jsonify({'error': 'Contract metadata not found'}), 404
        
        # Get contract parties
        parties = ContractParty.query.filter_by(contract_id=contract_id).all()
        
        # Construct response
        result = {
            'contract_data': {
                'contract_title': contract.title,
                'contract_type': contract.contract_type.value,
                'start_date': contract.start_date.isoformat() if contract.start_date else None,
                'end_date': contract.end_date.isoformat() if contract.end_date else None,
                'total_value': contract.value,
                'payment_terms': contract.payment_terms,
                'parties': [party.legal_name for party in parties],
            },
            'clauses': {
                'termination': metadata.termination_clause,
                'confidentiality': metadata.confidentiality_clause,
                'limitation_of_liability': metadata.limitation_of_liability,
                'force_majeure': metadata.force_majeure,
                'indemnification': metadata.indemnification,
                'jurisdiction': metadata.jurisdiction,
                'governing_law': metadata.governing_law
            },
            'risk_flags': metadata.risk_flags.get('flags', []) if metadata.risk_flags else [],
            'confidence_score': metadata.ai_confidence_score
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting extracted data for contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to get extracted data: {str(e)}"}), 500

@contracts_bp.route('/<int:contract_id>/document', methods=['GET'])
@requires_auth
def get_contract_document(contract_id):
    """Get the original contract document"""
    try:
        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({'error': 'Contract not found'}), 404
        
        if not contract.file_path:
            return jsonify({'error': 'No document available for this contract'}), 404
        
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        # Role-based access control
        if user.role != UserRole.ADMIN and contract.owner_id != user.id:
            return jsonify({'error': 'Unauthorized access to contract document'}), 403
        
        # Get the file
        try:
            file_content = storage_service.get_file(contract.file_path)
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Get the original filename
            original_filename = os.path.basename(contract.file_path)
            
            # Send the file
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=original_filename,
                mimetype='application/pdf'  # Assuming PDF, adjust as needed
            )
            
        finally:
            # Clean up the temporary file
            try:
                if temp_file_path:
                    os.unlink(temp_file_path)
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"Error getting document for contract {contract_id}: {str(e)}")
        return jsonify({'error': f"Failed to get contract document: {str(e)}"}), 500
