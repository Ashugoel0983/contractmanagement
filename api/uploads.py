"""
File upload API for Contract Management System
"""

import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app import db, storage_service, ocr_service, ai_service
from models import Contract, ContractMetadata, ContractParty, ContractStatus, ContractType
from auth import requires_auth, get_user_info

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
upload_bp = Blueprint('uploads', __name__)

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@upload_bp.route('', methods=['POST'])
@requires_auth
def upload_file():
    """
    Upload a contract file
    
    Request:
        - file: File to upload
        - contract_type: Type of contract (optional)
        - title: Contract title (optional)
        
    Returns:
        JSON response with upload status and contract ID
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file part in the request'
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        # Check if file extension is allowed
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': f'File type not allowed. Allowed types: {", ".join(current_app.config["ALLOWED_EXTENSIONS"])}'
            }), 400
        
        # Get user info
        user_info = get_user_info()
        user_id = user_info.get('sub')
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # Get form data
        title = request.form.get('title', 'Untitled Contract')
        
        contract_type_str = request.form.get('contract_type', 'Other')
        contract_type = None
        try:
            # Convert to enum
            contract_type = getattr(ContractType, contract_type_str.upper().replace(' ', '_'))
        except (AttributeError, ValueError):
            # Default to OTHER if type not found
            contract_type = ContractType.OTHER
        
        # Save file to storage
        file_path = storage_service.save_file(file, unique_filename)
        
        # Extract text from document
        logger.info("Extracting text from document")
        extracted_text = ocr_service.extract_text(file_path)
        
        if not extracted_text:
            return jsonify({
                'success': False,
                'message': 'Failed to extract text from document'
            }), 500
        
        # Analyze document with AI
        logger.info("Analyzing document with AI")
        analysis_result = ai_service.analyze_contract(extracted_text)
        
        if not analysis_result:
            analysis_result = {
                'title': title,
                'contract_type': contract_type_str,
                'parties': [],
                'metadata': {},
                'confidence': 0.0
            }
        
        # Create contract in database
        contract = Contract()
        contract.contract_number = f"CMS-{uuid.uuid4().hex[:8].upper()}"
        contract.title = analysis_result.get('title', title)
        contract.contract_type = contract_type
        contract.status = ContractStatus.DRAFT
        contract.description = analysis_result.get('description', '')
        contract.owner_id = user_id
        contract.file_path = file_path
        contract.extracted_text = extracted_text
        
        # Set dates if available
        if 'start_date' in analysis_result and analysis_result['start_date']:
            try:
                contract.start_date = datetime.fromisoformat(analysis_result['start_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        if 'end_date' in analysis_result and analysis_result['end_date']:
            try:
                contract.end_date = datetime.fromisoformat(analysis_result['end_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        # Set payment terms if available
        if 'value' in analysis_result:
            try:
                contract.value = float(analysis_result['value'])
            except (ValueError, TypeError):
                pass
        
        if 'currency' in analysis_result:
            contract.currency = analysis_result['currency']
        
        if 'payment_terms' in analysis_result:
            contract.payment_terms = analysis_result['payment_terms']
        
        if 'tags' in analysis_result:
            contract.tags = analysis_result['tags']
        
        # Save contract to database
        db.session.add(contract)
        db.session.flush()  # Get ID without committing
        
        # Create contract metadata
        metadata = ContractMetadata()
        metadata.contract_id = contract.id
        
        # Set default values for invoice configuration
        metadata.invoice_required = False
        
        # Set contract metadata from AI analysis
        meta_dict = analysis_result.get('metadata', {})
        
        if 'jurisdiction' in meta_dict:
            metadata.jurisdiction = meta_dict['jurisdiction']
        
        if 'governing_law' in meta_dict:
            metadata.governing_law = meta_dict['governing_law']
        
        if 'dispute_resolution' in meta_dict:
            metadata.dispute_resolution = meta_dict['dispute_resolution']
        
        if 'termination_clause' in meta_dict:
            metadata.termination_clause = meta_dict['termination_clause']
        
        if 'confidentiality_clause' in meta_dict:
            metadata.confidentiality_clause = meta_dict['confidentiality_clause']
        
        if 'limitation_of_liability' in meta_dict:
            metadata.limitation_of_liability = meta_dict['limitation_of_liability']
        
        if 'force_majeure' in meta_dict:
            metadata.force_majeure = meta_dict['force_majeure']
        
        if 'indemnification' in meta_dict:
            metadata.indemnification = meta_dict['indemnification']
        
        # Set AI confidence score
        metadata.ai_confidence_score = analysis_result.get('confidence', 0.0)
        
        # Add risk flags if available
        if 'risk_flags' in analysis_result:
            metadata.risk_flags = analysis_result['risk_flags']
        
        # Add metadata to database
        db.session.add(metadata)
        
        # Create contract parties
        for party_data in analysis_result.get('parties', []):
            party = ContractParty()
            party.contract_id = contract.id
            party.party_type = party_data.get('party_type', 'other')
            party.legal_name = party_data.get('legal_name', '')
            party.address = party_data.get('address', '')
            party.contact_person = party_data.get('contact_person', '')
            party.email = party_data.get('email', '')
            party.phone = party_data.get('phone', '')
            
            db.session.add(party)
        
        # Commit all changes
        db.session.commit()
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Contract uploaded successfully',
            'contract_id': contract.id,
            'contract_number': contract.contract_number,
            'ai_confidence': metadata.ai_confidence_score
        }), 201
    
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        
        logger.error(f"Error uploading contract: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error uploading contract: {str(e)}'
        }), 500