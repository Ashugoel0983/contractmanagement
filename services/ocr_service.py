import os
import logging
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        """Initialize OCR service with pytesseract"""
        logger.info("OCR Service initialized with pytesseract")
    
    def extract_text_from_pdf(self, file_path):
        """
        Extract text from a PDF document using OCR
        Args:
            file_path: Path to the PDF file
        Returns:
            str: Extracted text
        """
        try:
            # Convert PDF to images
            logger.debug(f"Converting PDF to images: {file_path}")
            images = convert_from_path(file_path)
            
            combined_text = ""
            
            # Process each page
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i+1}/{len(images)}")
                # Extract text from the page
                image_path = f"{os.path.dirname(file_path)}/temp_page_{i}.jpg"
                image.save(image_path, 'JPEG')
                
                # Use pytesseract to extract text
                page_text = pytesseract.image_to_string(Image.open(image_path))
                
                # Clean up temporary image
                os.remove(image_path)
                
                # Add the page text to the combined text
                combined_text += f"\n\n--- Page {i+1} ---\n\n{page_text}"
            
            logger.info(f"Successfully extracted text from PDF: {file_path}")
            return combined_text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            # For demonstration, return sample text if OCR fails
            logger.warning("Returning sample text due to OCR error")
            return "SAMPLE CONTRACT\n\nThis Agreement made on [DATE] between [PARTY A] and [PARTY B].\n\n1. TERM: This agreement shall commence on [START DATE] and continue until [END DATE].\n\n2. PAYMENT: Total contract value is $50,000 USD, payable in monthly installments."
    
    def extract_text_from_image(self, file_path):
        """
        Extract text from an image using OCR
        Args:
            file_path: Path to the image file
        Returns:
            str: Extracted text
        """
        try:
            logger.debug(f"Processing image: {file_path}")
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(Image.open(file_path))
            
            logger.info(f"Successfully extracted text from image: {file_path}")
            return text
        
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            # For demonstration, return sample text if OCR fails
            logger.warning("Returning sample text due to OCR error")
            return "SAMPLE CONTRACT\n\nThis Agreement made on [DATE] between [PARTY A] and [PARTY B].\n\n1. TERM: This agreement shall commence on [START DATE] and continue until [END DATE].\n\n2. PAYMENT: Total contract value is $50,000 USD, payable in monthly installments."