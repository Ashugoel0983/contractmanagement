import os
import logging
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.ocr_service import OCRService
from services.ai_service import AIService
from services.storage_service import StorageService
from auth import requires_auth, requires_role
from config import Config

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

# Initialize services
ocr_service = OCRService()
ai_service = AIService()
storage_service = StorageService()

@ai_bp.route('/extract', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def extract_document():
    """
    Extract structured data from a document using OCR and AI
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get document type from form
        doc_type = request.form.get('doc_type', 'contract')
        
        # Check if file type is allowed
        filename = secure_filename(file.filename)
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension not in ['.pdf', '.png', '.jpg', '.jpeg']:
            return jsonify({'error': 'File type not allowed. Allowed types: .pdf, .png, .jpg, .jpeg'}), 400
        
        # Save the file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Extract text using OCR
            logger.info(f"Processing file: {filename}")
            extracted_text = ocr_service.process_file(temp_file_path)
            
            # Extract structured data using AI
            extracted_data = ai_service.extract_contract_data(extracted_text, doc_type)
            
            # Calculate confidence metrics
            if doc_type == 'contract':
                clauses = extracted_data.get('clauses', {})
                clause_analysis = ai_service.analyze_clauses(clauses)
                risk_score = ai_service.calculate_risk_score(extracted_data)
                
                result = {
                    'extracted_data': extracted_data,
                    'clause_analysis': clause_analysis,
                    'risk_score': risk_score
                }
            else:
                result = {
                    'extracted_data': extracted_data
                }
            
            logger.info(f"Successfully extracted data from {filename}")
            return jsonify(result), 200
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error extracting document data: {str(e)}")
        return jsonify({'error': f"Failed to extract document data: {str(e)}"}), 500

@ai_bp.route('/analyze/clauses', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def analyze_clauses():
    """
    Analyze contract clauses for quality and missing important clauses
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data or 'clauses' not in data:
            return jsonify({'error': 'No clause data provided'}), 400
        
        # Analyze clauses using AI
        clauses = data['clauses']
        analysis = ai_service.analyze_clauses(clauses)
        
        logger.info("Successfully analyzed contract clauses")
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Error analyzing clauses: {str(e)}")
        return jsonify({'error': f"Failed to analyze clauses: {str(e)}"}), 500

@ai_bp.route('/analyze/risk', methods=['POST'])
@requires_auth
@requires_role(['admin', 'manager'])
def analyze_risk():
    """
    Calculate risk score for a contract based on extracted data
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No contract data provided'}), 400
        
        # Calculate risk score using AI
        risk_score = ai_service.calculate_risk_score(data)
        
        # Determine risk level
        risk_level = "low"
        if risk_score > 70:
            risk_level = "high"
        elif risk_score > 40:
            risk_level = "medium"
        
        result = {
            'risk_score': risk_score,
            'risk_level': risk_level
        }
        
        logger.info("Successfully calculated contract risk score")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error analyzing risk: {str(e)}")
        return jsonify({'error': f"Failed to analyze risk: {str(e)}"}), 500
