import logging
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from models import Contract, ContractStatus
from services.ocr_service import OCRService
from services.ai_service import AIService
from services.storage_service import StorageService
from auth import requires_auth, requires_role

logger = logging.getLogger(__name__)

# Initialize services
ocr_service = OCRService()
ai_service = AIService()
storage_service = StorageService()

# Create blueprint
ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/extract-document', methods=['POST'])
@requires_auth
def extract_document():
    """
    Extract structured data from a document using OCR and AI
    """
    try:
        # Check if file was uploaded
        if 'document' not in request.files:
            return jsonify({'error': 'No document provided'}), 400
        
        document = request.files['document']
        if not document.filename:
            return jsonify({'error': 'No document selected'}), 400
        
        # Save the file
        file_path = storage_service.save_file(
            document,
            prefix='temp',
            allowed_extensions={'pdf', 'png', 'jpg', 'jpeg'}
        )
        
        # Extract text from the document
        extracted_text = ""
        if file_path.lower().endswith('.pdf'):
            extracted_text = ocr_service.extract_text_from_pdf(file_path)
        else:
            extracted_text = ocr_service.extract_text_from_image(file_path)
        
        # Process the document type
        doc_type = request.form.get('doc_type', 'contract')
        
        # Use AI to extract structured data
        extracted_data = ai_service.extract_contract_data(extracted_text, doc_type)
        
        # Clean up temporary file
        storage_service.delete_file(file_path)
        
        return jsonify({
            'success': True,
            'text': extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            'data': extracted_data
        }), 200
    
    except Exception as e:
        logger.error(f"Error extracting document data: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/analyze-clauses', methods=['POST'])
@requires_auth
def analyze_clauses():
    """
    Analyze contract clauses for quality and missing important clauses
    """
    try:
        # Get clauses from request
        data = request.json
        if not data or 'clauses' not in data:
            return jsonify({'error': 'No clauses provided'}), 400
        
        clauses = data['clauses']
        if not isinstance(clauses, dict):
            return jsonify({'error': 'Clauses must be provided as a dictionary'}), 400
        
        # Use AI to analyze clauses
        analysis = ai_service.analyze_clauses(clauses)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
    
    except Exception as e:
        logger.error(f"Error analyzing clauses: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/analyze-risk', methods=['POST'])
@requires_auth
def analyze_risk():
    """
    Calculate risk score for a contract based on extracted data
    """
    try:
        # Get contract data from request
        data = request.json
        if not data or 'contract_data' not in data:
            return jsonify({'error': 'No contract data provided'}), 400
        
        contract_data = data['contract_data']
        
        # Use AI to calculate risk score
        risk_assessment = ai_service.calculate_risk_score(contract_data)
        
        # If contract ID is provided, update its status if high risk
        contract_id = data.get('contract_id')
        if contract_id and risk_assessment.get('risk_level') == 'high':
            from app import db
            contract = Contract.query.get(contract_id)
            if contract:
                contract.status = ContractStatus.RISK_FLAGGED
                db.session.commit()
                logger.info(f"Contract {contract_id} flagged as high risk")
        
        return jsonify({
            'success': True,
            'risk_assessment': risk_assessment
        }), 200
    
    except Exception as e:
        logger.error(f"Error analyzing risk: {str(e)}")
        return jsonify({'error': str(e)}), 500