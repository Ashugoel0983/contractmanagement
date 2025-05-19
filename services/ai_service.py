"""
AI Service for Contract Management System using OpenAI
"""

import os
import json
import logging
from datetime import datetime
import openai

# Set up logging
logger = logging.getLogger(__name__)

class AIService:
    """
    AI Service for analyzing contracts using OpenAI's API
    """
    
    def __init__(self):
        """Initialize AI service"""
        # Initialize OpenAI API client
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        # Set the API key for OpenAI
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Set default model
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini-2024-07-18")
        logger.info(f"AI Service initialized with model: {self.model}")
    
    def analyze_contract(self, text):
        """
        Analyze contract text and extract structured data
        
        Args:
            text: Contract text to analyze
            
        Returns:
            dict: Extracted contract data
        """
        if not text:
            logger.error("No text provided for analysis")
            return None
        
        try:
            # Create a prompt for the AI to analyze the contract
            prompt = f"""
You are a contract analysis expert. Analyze the following contract text and extract key information in JSON format.

CONTRACT TEXT:
{text[:8000]}  # Limit text to avoid token limits

Extract the following information and return as JSON:
1. title - The title or name of the contract
2. contract_type - Type of contract (e.g., "Service Agreement", "NDA", "Employment", etc.)
3. description - Brief description of the contract's purpose
4. parties - Array of parties involved, each with:
   - party_type: "client", "vendor", "employer", "employee", etc.
   - legal_name: Full legal name
   - address: Full address if available
   - contact_person: Name of contact person if available
   - email: Email address if available
   - phone: Phone number if available
5. start_date - Start date in ISO format (YYYY-MM-DD)
6. end_date - End date in ISO format (YYYY-MM-DD)
7. value - Monetary value of the contract (numeric only)
8. currency - Currency code (e.g., USD, EUR)
9. payment_terms - Payment terms description
10. tags - Array of relevant tags (e.g., ["legal", "finance", "IT"])
11. metadata - Object containing:
    - jurisdiction: Governing jurisdiction
    - governing_law: Applicable law
    - dispute_resolution: How disputes will be resolved
    - termination_clause: Summary of termination provisions
    - confidentiality_clause: Summary of confidentiality provisions
    - limitation_of_liability: Summary of liability limitations
    - force_majeure: Summary of force majeure provisions
    - indemnification: Summary of indemnification provisions
12. risk_flags - Object containing:
    - missing_clauses: Array of important missing clauses
    - risky_clauses: Array of potentially risky clauses
    - ambiguous_terms: Array of ambiguous or unclear terms
13. confidence - Confidence score from 0.0 to 1.0 representing confidence in extraction accuracy

Return only the JSON object with no additional text.
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a contract analysis expert that extracts structured data from contracts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic responses
                max_tokens=2048,
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Get response text
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            analysis_result = json.loads(response_text)
            
            return analysis_result
        
        except Exception as e:
            logger.error(f"Error analyzing contract: {str(e)}")
            return None
    
    def analyze_risk(self, contract_data):
        """
        Calculate risk score and identify risk factors in a contract
        
        Args:
            contract_data: Contract data to analyze
            
        Returns:
            dict: Risk analysis result
        """
        if not contract_data:
            logger.error("No contract data provided for risk analysis")
            return None
        
        try:
            # Extract relevant text for risk analysis
            risk_text = json.dumps(contract_data, indent=2)
            
            # Create a prompt for the AI to analyze risks
            prompt = f"""
You are a contract risk assessment expert. Analyze the following contract data and calculate an overall risk score.

CONTRACT DATA:
{risk_text}

Assess the risk level of this contract by checking for the following risk factors:
1. Missing critical clauses (e.g., termination, liability, confidentiality)
2. Ambiguous or unclear terms
3. Potentially unfavorable terms
4. High liability or financial risk
5. Regulatory compliance issues
6. Inadequate protections

Provide a risk score from 0.0 (minimal risk) to 1.0 (extreme risk) and explain the risk factors.

Return the analysis in JSON format:
{
  "risk_score": 0.0 to 1.0,
  "risk_level": "Low", "Medium", "High", or "Critical",
  "risk_factors": ["list of specific risk factors identified"],
  "missing_clauses": ["list of important missing clauses"],
  "recommendations": ["list of recommendations to mitigate risks"]
}

Return only the JSON object with no additional text.
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a contract risk assessment expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic responses
                max_tokens=1024,
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Get response text
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            risk_analysis = json.loads(response_text)
            
            return risk_analysis
        
        except Exception as e:
            logger.error(f"Error analyzing contract risk: {str(e)}")
            return None
    
    def analyze_clauses(self, contract_text):
        """
        Analyze contract clauses for quality and missing important clauses
        
        Args:
            contract_text: Contract text to analyze
            
        Returns:
            dict: Clause analysis result
        """
        if not contract_text:
            logger.error("No text provided for clause analysis")
            return None
        
        try:
            # Create a prompt for the AI to analyze clauses
            prompt = f"""
You are a contract clause analysis expert. Analyze the following contract text and extract key clauses.

CONTRACT TEXT:
{contract_text[:8000]}  # Limit text to avoid token limits

Extract the following important clauses and provisions:
1. Termination clause
2. Liability clause
3. Confidentiality clause
4. Intellectual property clause
5. Dispute resolution clause
6. Force majeure clause
7. Indemnification clause
8. Payment terms
9. Term and renewal
10. Governing law

For each clause found, provide:
- The clause name
- A brief summary of the clause
- An assessment of the clause quality (Strong, Adequate, Weak, or Missing)
- Recommendations for improvement if the clause is weak or missing

Return the analysis in JSON format:
{{
  "clauses": [
    {{
      "name": "Clause name",
      "summary": "Brief summary",
      "quality": "Strong/Adequate/Weak/Missing",
      "recommendations": "Recommendations for improvement"
    }},
    ...
  ],
  "missing_clauses": ["List of missing important clauses"],
  "overall_assessment": "Brief overall assessment of the contract's clause quality"
}}

Return only the JSON object with no additional text.
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a contract clause analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic responses
                max_tokens=2048,
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Get response text
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            clause_analysis = json.loads(response_text)
            
            return clause_analysis
        
        except Exception as e:
            logger.error(f"Error analyzing contract clauses: {str(e)}")
            return None
    
    def generate_summary(self, contract_data):
        """
        Generate a concise summary of a contract
        
        Args:
            contract_data: Contract data to summarize
            
        Returns:
            str: Contract summary
        """
        if not contract_data:
            logger.error("No contract data provided for summary generation")
            return None
        
        try:
            # Extract relevant data for summary
            summary_data = json.dumps(contract_data, indent=2)
            
            # Create a prompt for the AI to generate a summary
            prompt = f"""
Summarize the following contract data in a clear, concise format:

CONTRACT DATA:
{summary_data}

Generate a business-friendly executive summary of this contract that highlights:
1. Contract type and purpose
2. Key parties involved
3. Important dates (start, end, key milestones)
4. Financial terms
5. Key obligations for each party
6. Notable risks or special provisions

The summary should be 3-5 paragraphs, professional in tone, and focused on the most important business aspects of the contract.
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a contract summary expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Slightly higher temperature for more natural language
                max_tokens=1024
            )
            
            # Get response text
            summary = response.choices[0].message.content
            
            return summary
        
        except Exception as e:
            logger.error(f"Error generating contract summary: {str(e)}")
            return None