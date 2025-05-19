import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """Initialize the AI service with OpenAI"""
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        self.model = "gpt-4o-mini-2024-07-18"  # the newest OpenAI model specified for this project
        self.client = OpenAI(api_key=self.openai_api_key)
        logger.info(f"AI Service initialized with model: {self.model}")
    
    def extract_contract_data(self, text, doc_type="contract"):
        """
        Extract structured data from contract text using AI
        Args:
            text: The OCR-extracted text
            doc_type: Type of document (contract, invoice, etc.)
        Returns:
            dict: Structured contract data
        """
        try:
            logger.debug(f"Extracting data from {doc_type} with {len(text)} characters")
            
            # Create a prompt based on document type
            if doc_type == "contract":
                prompt = self._create_contract_extraction_prompt(text)
            elif doc_type == "invoice":
                prompt = self._create_invoice_extraction_prompt(text)
            else:
                prompt = self._create_generic_extraction_prompt(text, doc_type)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in document analysis and data extraction."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse and return the extracted data
            content = response.choices[0].message.content
            if content is not None:
                extracted_data = json.loads(content)
                logger.info(f"Successfully extracted data from {doc_type}")
                return extracted_data
            else:
                logger.warning("Empty response content received from OpenAI API")
                return {}
        
        except Exception as e:
            logger.error(f"Error extracting data from document: {str(e)}")
            raise
    
    def analyze_clauses(self, clauses):
        """
        Analyze contract clauses for quality and identify missing important clauses
        Args:
            clauses: Dict of contract clauses
        Returns:
            dict: Analysis results
        """
        try:
            logger.debug(f"Analyzing {len(clauses)} contract clauses")
            
            # Convert clauses to a formatted string for the prompt
            clauses_text = ""
            for key, value in clauses.items():
                clauses_text += f"{key}: {value}\n\n"
            
            # Create the analysis prompt
            prompt = (
                "Analyze the following contract clauses for quality and completeness. "
                "Identify any missing important clauses, vague language, or potential risks. "
                "Return a JSON with these keys: 'analysis', 'missing_clauses', 'risk_score', and 'recommendations'.\n\n"
                f"CLAUSES TO ANALYZE:\n{clauses_text}"
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal expert specializing in contract analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse and return the analysis
            content = response.choices[0].message.content
            if content:
                analysis = json.loads(content)
                logger.info(f"Successfully analyzed contract clauses")
                return analysis
            else:
                logger.warning("Empty response content received from OpenAI API")
                return {}
        
        except Exception as e:
            logger.error(f"Error analyzing contract clauses: {str(e)}")
            raise
    
    def calculate_risk_score(self, contract_data):
        """
        Calculate a risk score for the contract based on extracted data
        Args:
            contract_data: The extracted contract data
        Returns:
            dict: Risk assessment with score and flags
        """
        try:
            logger.debug("Calculating risk score for contract")
            
            # Format contract data for the prompt
            contract_json = json.dumps(contract_data, indent=2)
            
            # Create the risk assessment prompt
            prompt = (
                "Assess the risk level of this contract based on the provided data. "
                "Consider factors like payment terms, duration, termination clauses, liability, and governing law. "
                "Return a JSON with these keys: 'risk_score' (0-100, higher means riskier), 'risk_level' (low/medium/high), "
                "'risk_factors' (array of risk factors), and 'recommendations' (array of risk mitigation suggestions).\n\n"
                f"CONTRACT DATA:\n{contract_json}"
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a risk assessment expert specializing in contract analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse and return the risk assessment
            content = response.choices[0].message.content
            if content:
                risk_assessment = json.loads(content)
                logger.info(f"Successfully calculated risk score: {risk_assessment.get('risk_score', 'N/A')}")
                return risk_assessment
            else:
                logger.warning("Empty response content received from OpenAI API")
                return {}
        
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            raise
    
    def _create_contract_extraction_prompt(self, text):
        """Create prompt for contract data extraction"""
        return (
            "Extract the following information from this contract text and return as JSON. "
            "Include only the fields that are present in the document. "
            "Response should be a valid JSON object with these fields:\n"
            "- title: Contract title\n"
            "- contract_type: Type of contract (Service Agreement, NDA, etc.)\n"
            "- parties: Array of parties (with name, address, role if available)\n"
            "- start_date: Start date in ISO format (YYYY-MM-DD)\n"
            "- end_date: End date in ISO format (YYYY-MM-DD)\n"
            "- payment_details: Payment amount, currency, schedule if available\n"
            "- payment_terms: Payment terms description\n"
            "- jurisdiction: Governing law jurisdiction\n"
            "- termination_clause: Summary of termination conditions\n"
            "- confidentiality_clause: Summary of confidentiality terms\n"
            "- limitation_of_liability: Summary of liability limitations\n"
            "- force_majeure: Summary of force majeure clause\n"
            "- indemnification: Summary of indemnification terms\n\n"
            f"CONTRACT TEXT:\n{text}"
        )
    
    def _create_invoice_extraction_prompt(self, text):
        """Create prompt for invoice data extraction"""
        return (
            "Extract the following information from this invoice text and return as JSON. "
            "Include only the fields that are present in the document. "
            "Response should be a valid JSON object with these fields:\n"
            "- invoice_number: Invoice identifier\n"
            "- issue_date: Issue date in ISO format (YYYY-MM-DD)\n"
            "- due_date: Due date in ISO format (YYYY-MM-DD)\n"
            "- vendor: Company issuing the invoice\n"
            "- client: Company receiving the invoice\n"
            "- line_items: Array of items with description, quantity, unit_price, amount\n"
            "- subtotal: Subtotal amount\n"
            "- tax: Tax amount\n"
            "- total: Total amount\n"
            "- currency: Currency code (USD, EUR, etc.)\n"
            "- payment_terms: Terms of payment\n"
            "- payment_instructions: Instructions for payment\n\n"
            f"INVOICE TEXT:\n{text}"
        )
    
    def _create_generic_extraction_prompt(self, text, doc_type):
        """Create prompt for generic document data extraction"""
        return (
            f"Extract key information from this {doc_type} text and return as JSON. "
            "Identify the main entities, dates, amounts, terms, and other relevant information. "
            "Structure your response as a meaningful JSON object with appropriate field names. "
            "For dates, use ISO format (YYYY-MM-DD) when possible.\n\n"
            f"DOCUMENT TEXT:\n{text}"
        )