import os
import json
import logging
from datetime import datetime
import openai
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """Initialize the AI service with OpenAI or Google Gemini"""
        self.api_key = Config.OPENAI_API_KEY
        self.use_gemini = Config.USE_GEMINI
        self.gemini_api_key = Config.GEMINI_API_KEY
        
        if not self.use_gemini:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized")
        else:
            # Gemini initialization would go here
            logger.info("Gemini client initialized")

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
            if not self.use_gemini:
                logger.info(f"Processing {doc_type} text with OpenAI")
                
                system_prompt = f"""
                You are an expert contract analyst. Extract the following information from the {doc_type} text:
                1. Contract title
                2. Contract type (Service Agreement, Vendor Contract, Lease Agreement, License Agreement, NDA, Employment, Other)
                3. Parties involved (company names)
                4. Start date and end date (in YYYY-MM-DD format)
                5. Contract value (numeric amount)
                6. Payment terms (e.g., Net 30, Monthly, etc.)
                7. Key clauses (termination, confidentiality, indemnity, jurisdiction, limitation of liability, force majeure)
                8. Risk flags (any missing important clauses or concerning terms)
                
                Format your response as a JSON object with these fields:
                - contract_title (string)
                - contract_type (string)
                - parties (array of strings)
                - start_date (string, YYYY-MM-DD)
                - end_date (string, YYYY-MM-DD)
                - total_value (number)
                - payment_terms (string)
                - clauses (object with clause names as keys and clause text as values)
                - risk_flags (array of strings describing risks)
                
                For each field, include a confidence score between 0 and 1 indicating your certainty.
                For dates you can't determine, use null. For numeric values you can't determine, use null.
                """
                
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.info("Successfully extracted contract data using OpenAI")
                return result
            else:
                # Gemini implementation would go here
                logger.info("Gemini AI extraction not implemented yet")
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting data with AI: {str(e)}")
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
            if not self.use_gemini:
                logger.info("Analyzing contract clauses with OpenAI")
                
                system_prompt = """
                You are a legal expert specializing in contract analysis. Review the provided contract clauses and:
                1. Identify any missing critical clauses from this list:
                   - Termination
                   - Confidentiality
                   - Indemnification
                   - Limitation of Liability
                   - Governing Law/Jurisdiction
                   - Force Majeure
                   - Non-solicitation
                   - Assignment
                   - Severability
                
                2. For each provided clause, assess its quality and flag any potential issues.
                
                Format your response as a JSON object with:
                - missing_clauses: array of strings naming missing critical clauses
                - clause_analysis: object with clause names as keys and objects containing:
                  - status: "present", "missing", or "present_but_vague"
                  - quality: score from 1-5
                  - issues: array of identified issues
                  - recommendations: array of suggested improvements
                """
                
                clauses_text = json.dumps(clauses, indent=2)
                
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Here are the contract clauses to analyze:\n{clauses_text}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.info("Successfully analyzed contract clauses using OpenAI")
                return result
            else:
                # Gemini implementation would go here
                logger.info("Gemini clause analysis not implemented yet")
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing clauses with AI: {str(e)}")
            raise

    def calculate_risk_score(self, contract_data):
        """
        Calculate a risk score for the contract based on extracted data
        Args:
            contract_data: The extracted contract data
        Returns:
            float: Risk score (0-100, higher means riskier)
        """
        try:
            # Initialize risk score
            risk_score = 0
            
            # Check for missing critical clauses
            critical_clauses = [
                "termination", "confidentiality", "indemnification", 
                "limitation_of_liability", "governing_law", "force_majeure"
            ]
            
            clauses = contract_data.get('clauses', {})
            missing_clauses = [clause for clause in critical_clauses if clause not in clauses]
            
            # Add 10 points for each missing critical clause
            risk_score += len(missing_clauses) * 10
            
            # Check for short contract duration
            start_date = contract_data.get('start_date')
            end_date = contract_data.get('end_date')
            
            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    duration_days = (end - start).days
                    
                    # Add risk points for short contracts (less than 6 months)
                    if duration_days < 180:
                        risk_score += 15
                except ValueError:
                    # If date parsing fails, add some risk
                    risk_score += 5
            
            # Check for high value
            total_value = contract_data.get('total_value')
            if isinstance(total_value, (int, float)) and total_value > 100000:
                risk_score += 10
            
            # Add points for explicit risk flags
            risk_flags = contract_data.get('risk_flags', [])
            risk_score += len(risk_flags) * 5
            
            # Cap at 100
            return min(risk_score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 50  # Return a moderate risk score on error
