import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.exceptions import NotFound, BadRequest
from sqlalchemy import desc, func

from app import db
from models import Contract, ContractParty, ContractMetadata, ContractType, ContractStatus, User
from services.ocr_service import OCRService
from services.ai_service import AIService
from services.storage_service import StorageService
from auth import requires_auth, requires_role, get_user_info

logger = logging.getLogger(__name__)

# Initialize services
ocr_service = OCRService()
ai_service = AIService()
storage_service = StorageService()

# Create blueprint
contracts_bp = Blueprint('contracts', __name__)


@contracts_bp.route('', methods=['GET'])
@requires_auth
def get_contracts():
    """
    Get all contracts with optional filtering
    Query params:
        status: Filter by contract status
        type: Filter by contract type
        owner_id: Filter by owner ID
        search: Search in title and description
        tags: Filter by tags (comma-separated)
        sort_by: Field to sort by
        sort_order: asc or desc
        page: Page number (default: 1)
        per_page: Items per page (default: 20)
    """
    try:
        # Get query parameters
        status = request.args.get('status')
        contract_type = request.args.get('type')
        owner_id = request.args.get('owner_id')
        search_query = request.args.get('search')
        tags = request.args.get('tags')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Start query
        query = Contract.query
        
        # Apply filters
        if status:
            query = query.filter(Contract.status == ContractStatus(status))
        
        if contract_type:
            query = query.filter(Contract.contract_type == ContractType(contract_type))
        
        if owner_id:
            query = query.filter(Contract.owner_id == owner_id)
        
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                (Contract.title.ilike(search_term)) | 
                (Contract.description.ilike(search_term))
            )
        
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                query = query.filter(Contract.tags.contains([tag]))
        
        # Apply sorting
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(Contract, sort_by)))
        else:
            query = query.order_by(getattr(Contract, sort_by))
        
        # Apply pagination
        pagination = query.paginate(page=page, per_page=per_page)
        
        # Prepare response
        contracts = [contract.to_dict() for contract in pagination.items]
        
        response = {
            'contracts': contracts,
            'pagination': {
                'total': pagination.total,
                'pages': pagination.pages,
                'page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error getting contracts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('', methods=['POST'])
@requires_auth
def create_contract():
    """
    Create a new contract
    """
    try:
        # Get user info
        user_info = get_user_info()
        auth0_id = user_info.get('sub')
        
        # Find the user
        user = User.query.filter_by(auth0_id=auth0_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get request data
        data = request.form.to_dict()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        if not data.get('contract_type'):
            return jsonify({'error': 'Contract type is required'}), 400
        
        # Process contract document if provided
        file_path = None
        extracted_text = None
        if 'document' in request.files:
            document = request.files['document']
            if document.filename:
                # Save the file
                file_path = storage_service.save_file(
                    document, 
                    prefix='contracts',
                    allowed_extensions={'pdf', 'png', 'jpg', 'jpeg'}
                )
                
                # Extract text from the document
                if file_path.lower().endswith('.pdf'):
                    extracted_text = ocr_service.extract_text_from_pdf(file_path)
                else:
                    extracted_text = ocr_service.extract_text_from_image(file_path)
        
        # Generate contract number
        contract_number = f"CNT-{uuid.uuid4().hex[:8].upper()}"
        
        # Parse dates
        start_date = None
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        # Parse tags
        tags = None
        if data.get('tags'):
            tags = data['tags'].split(',')
        
        # Create contract
        contract = Contract(
            contract_number=contract_number,
            title=data['title'],
            contract_type=ContractType(data['contract_type']),
            status=ContractStatus.DRAFT,
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            value=float(data['value']) if data.get('value') else None,
            currency=data.get('currency', 'USD'),
            payment_terms=data.get('payment_terms'),
            owner_id=user.id,
            file_path=file_path,
            extracted_text=extracted_text,
            tags=tags
        )
        
        # Add to database
        db.session.add(contract)
        db.session.commit()
        
        # Create party information if provided
        if data.get('party_name'):
            party = ContractParty(
                contract_id=contract.id,
                party_type=data.get('party_type', 'client'),
                legal_name=data['party_name'],
                address=data.get('party_address'),
                contact_person=data.get('party_contact'),
                email=data.get('party_email'),
                phone=data.get('party_phone')
            )
            db.session.add(party)
            db.session.commit()
        
        return jsonify(contract.to_dict()), 201
    
    except Exception as e:
        logger.error(f"Error creating contract: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>', methods=['GET'])
@requires_auth
def get_contract(contract_id):
    """
    Get a contract by ID
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        # Get contract metadata
        contract_data = contract.to_dict()
        
        # Add parties and metadata
        if contract.parties:
            contract_data['parties'] = [party.to_dict() for party in contract.parties]
        
        if contract.contract_metadata:
            contract_data['metadata'] = contract.contract_metadata.to_dict()
        
        return jsonify(contract_data), 200
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting contract {contract_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>', methods=['PUT'])
@requires_auth
def update_contract(contract_id):
    """
    Update a contract by ID
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        # Get request data
        data = request.form.to_dict()
        
        # Update contract fields if provided
        if 'title' in data:
            contract.title = data['title']
        
        if 'contract_type' in data:
            contract.contract_type = ContractType(data['contract_type'])
        
        if 'status' in data:
            contract.status = ContractStatus(data['status'])
        
        if 'description' in data:
            contract.description = data['description']
        
        if 'start_date' in data:
            contract.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        
        if 'end_date' in data:
            contract.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        if 'value' in data:
            contract.value = float(data['value'])
        
        if 'currency' in data:
            contract.currency = data['currency']
        
        if 'payment_terms' in data:
            contract.payment_terms = data['payment_terms']
        
        if 'tags' in data and data['tags']:
            contract.tags = data['tags'].split(',')
        
        # Process contract document if provided
        if 'document' in request.files:
            document = request.files['document']
            if document.filename:
                # Delete old file if exists
                if contract.file_path:
                    storage_service.delete_file(contract.file_path)
                
                # Save the new file
                file_path = storage_service.save_file(
                    document, 
                    prefix='contracts',
                    allowed_extensions={'pdf', 'png', 'jpg', 'jpeg'}
                )
                
                # Extract text from the document
                if file_path.lower().endswith('.pdf'):
                    extracted_text = ocr_service.extract_text_from_pdf(file_path)
                else:
                    extracted_text = ocr_service.extract_text_from_image(file_path)
                
                contract.file_path = file_path
                contract.extracted_text = extracted_text
        
        # Update the contract
        db.session.commit()
        
        return jsonify(contract.to_dict()), 200
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>', methods=['DELETE'])
@requires_auth
def delete_contract(contract_id):
    """
    Delete a contract by ID
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        # Check if the contract has recurring invoices
        has_recurring_invoices = any(invoice.is_recurring for invoice in contract.invoices)
        if has_recurring_invoices:
            return jsonify({
                'error': 'Cannot delete a contract with recurring invoices', 
                'message': 'Please cancel all recurring invoices before deleting this contract'
            }), 400
        
        # Delete contract file if exists
        if contract.file_path:
            storage_service.delete_file(contract.file_path)
        
        # Delete contract from database (relationships will cascade)
        db.session.delete(contract)
        db.session.commit()
        
        return jsonify({'message': f'Contract {contract_id} successfully deleted'}), 200
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error deleting contract {contract_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>/extract', methods=['POST'])
@requires_auth
def extract_contract_data(contract_id):
    """
    Extract data from a contract using AI
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        if not contract.extracted_text:
            return jsonify({'error': 'No extracted text available for this contract'}), 400
        
        # Use AI to extract structured data
        extracted_data = ai_service.extract_contract_data(contract.extracted_text)
        
        # Create or update contract metadata
        metadata = contract.contract_metadata
        if not metadata:
            metadata = ContractMetadata(contract_id=contract.id)
            db.session.add(metadata)
        
        # Update metadata fields
        if 'jurisdiction' in extracted_data:
            metadata.jurisdiction = extracted_data.get('jurisdiction')
        
        if 'governing_law' in extracted_data:
            metadata.governing_law = extracted_data.get('governing_law')
        
        if 'termination_clause' in extracted_data:
            metadata.termination_clause = extracted_data.get('termination_clause')
        
        if 'confidentiality_clause' in extracted_data:
            metadata.confidentiality_clause = extracted_data.get('confidentiality_clause')
        
        if 'limitation_of_liability' in extracted_data:
            metadata.limitation_of_liability = extracted_data.get('limitation_of_liability')
        
        if 'force_majeure' in extracted_data:
            metadata.force_majeure = extracted_data.get('force_majeure')
        
        if 'indemnification' in extracted_data:
            metadata.indemnification = extracted_data.get('indemnification')
        
        # Update contract fields
        if 'title' in extracted_data and extracted_data.get('title'):
            contract.title = extracted_data.get('title')
        
        if 'contract_type' in extracted_data and extracted_data.get('contract_type'):
            # Try to match with enum values
            contract_type = extracted_data.get('contract_type')
            for ct in ContractType:
                if contract_type.lower() in ct.value.lower():
                    contract.contract_type = ct
                    break
        
        if 'start_date' in extracted_data and extracted_data.get('start_date'):
            try:
                contract.start_date = datetime.fromisoformat(extracted_data.get('start_date'))
            except ValueError:
                pass
        
        if 'end_date' in extracted_data and extracted_data.get('end_date'):
            try:
                contract.end_date = datetime.fromisoformat(extracted_data.get('end_date'))
            except ValueError:
                pass
        
        if 'payment_details' in extracted_data:
            payment_details = extracted_data.get('payment_details')
            if payment_details and isinstance(payment_details, dict):
                if 'amount' in payment_details:
                    try:
                        contract.value = float(payment_details.get('amount'))
                    except ValueError:
                        pass
                
                if 'currency' in payment_details:
                    contract.currency = payment_details.get('currency')
        
        if 'payment_terms' in extracted_data:
            contract.payment_terms = extracted_data.get('payment_terms')
        
        # Save changes
        db.session.commit()
        
        # Perform risk analysis
        risk_assessment = ai_service.calculate_risk_score(extracted_data)
        
        # Update metadata with risk assessment
        metadata.ai_confidence_score = risk_assessment.get('risk_score', 0) / 100
        metadata.risk_flags = {
            'risk_level': risk_assessment.get('risk_level', 'unknown'),
            'risk_factors': risk_assessment.get('risk_factors', []),
            'recommendations': risk_assessment.get('recommendations', [])
        }
        
        # Flag contract if high risk
        if risk_assessment.get('risk_level') == 'high':
            contract.status = ContractStatus.RISK_FLAGGED
        
        # Add parties if extracted
        if 'parties' in extracted_data and extracted_data.get('parties'):
            parties = extracted_data.get('parties')
            for party_data in parties:
                # Skip if no name
                if not party_data.get('name'):
                    continue
                
                # Check if party already exists
                existing_party = ContractParty.query.filter_by(
                    contract_id=contract.id,
                    legal_name=party_data.get('name')
                ).first()
                
                if not existing_party:
                    party = ContractParty(
                        contract_id=contract.id,
                        party_type=party_data.get('role', 'external'),
                        legal_name=party_data.get('name'),
                        address=party_data.get('address')
                    )
                    db.session.add(party)
        
        # Save all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contract data extracted successfully',
            'data': extracted_data,
            'risk_assessment': risk_assessment
        }), 200
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error extracting contract data for {contract_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>/data', methods=['GET'])
@requires_auth
def get_extracted_data(contract_id):
    """
    Get extracted structured data for a contract
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        metadata = contract.contract_metadata
        if not metadata:
            return jsonify({'error': 'No metadata available for this contract'}), 404
        
        # Compile extracted data
        extracted_data = {
            'contract_id': contract.id,
            'contract_number': contract.contract_number,
            'title': contract.title,
            'contract_type': contract.contract_type.value,
            'start_date': contract.start_date.isoformat() if hasattr(contract.start_date, 'isoformat') else None,
            'end_date': contract.end_date.isoformat() if hasattr(contract.end_date, 'isoformat') else None,
            'value': contract.value,
            'currency': contract.currency,
            'payment_terms': contract.payment_terms,
            'metadata': metadata.to_dict() if metadata else None,
            'parties': [party.to_dict() for party in contract.parties] if contract.parties else []
        }
        
        return jsonify(extracted_data), 200
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting extracted data for contract {contract_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@contracts_bp.route('/<int:contract_id>/document', methods=['GET'])
@requires_auth
def get_contract_document(contract_id):
    """
    Get the original contract document
    """
    try:
        contract = Contract.query.get(contract_id)
        
        if not contract:
            raise NotFound(f"Contract with ID {contract_id} not found")
        
        if not contract.file_path:
            return jsonify({'error': 'No document available for this contract'}), 404
        
        # Get the file
        file_content = storage_service.get_file(contract.file_path)
        
        # Determine file type
        file_ext = os.path.splitext(contract.file_path)[1].lower()
        if file_ext == '.pdf':
            mime_type = 'application/pdf'
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            mime_type = f'image/{file_ext[1:]}'
        else:
            mime_type = 'application/octet-stream'
        
        # Create response with file content
        from flask import send_file
        from io import BytesIO
        
        return send_file(
            BytesIO(file_content),
            mimetype=mime_type,
            as_attachment=True,
            download_name=f"contract_{contract.contract_number}{file_ext}"
        )
    
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting document for contract {contract_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Dashboard metrics
@contracts_bp.route('/metrics', methods=['GET'])
@requires_auth
def get_contract_metrics():
    """
    Get contract metrics for dashboard
    """
    try:
        # Get total contracts count
        total_contracts = Contract.query.count()
        
        # Get active contracts count
        active_contracts = Contract.query.filter_by(status=ContractStatus.ACTIVE).count()
        
        # Get contracts expiring in the next 30 days
        today = datetime.utcnow()
        expiring_soon = (
            Contract.query
            .filter(Contract.status == ContractStatus.ACTIVE)
            .filter(Contract.end_date >= today)
            .filter(Contract.end_date <= today.replace(day=today.day + 30))
            .count()
        )
        
        # Calculate renewal rate (contracts renewed / contracts expired) * 100
        renewed_contracts = (
            Contract.query
            .filter(Contract.status == ContractStatus.ACTIVE)
            .filter(Contract.end_date < today)
            .count()
        )
        
        expired_contracts = Contract.query.filter_by(status=ContractStatus.EXPIRED).count()
        
        renewal_rate = 0
        if expired_contracts + renewed_contracts > 0:
            renewal_rate = (renewed_contracts / (expired_contracts + renewed_contracts)) * 100
        
        # Get contracts by type
        contracts_by_type = {}
        for ct in ContractType:
            count = Contract.query.filter_by(contract_type=ct).count()
            contracts_by_type[ct.value] = count
        
        # Get contracts by status
        contracts_by_status = {}
        for cs in ContractStatus:
            count = Contract.query.filter_by(status=cs).count()
            contracts_by_status[cs.value] = count
        
        # Get total contract value
        total_value = db.session.query(func.sum(Contract.value)).scalar() or 0
        
        # Return metrics
        metrics = {
            'total_contracts': total_contracts,
            'active_contracts': active_contracts,
            'expiring_soon': expiring_soon,
            'renewal_rate': round(renewal_rate, 2),
            'contracts_by_type': contracts_by_type,
            'contracts_by_status': contracts_by_status,
            'total_value': total_value
        }
        
        return jsonify(metrics), 200
    
    except Exception as e:
        logger.error(f"Error getting contract metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500