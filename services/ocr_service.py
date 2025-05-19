"""
OCR Service for Contract Management System
"""

import os
import logging
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class OCRService:
    """
    OCR Service for extracting text from documents
    Uses pytesseract for OCR processing
    """
    
    def __init__(self):
        """Initialize OCR service"""
        # Check if pytesseract is installed and available
        try:
            pytesseract.get_tesseract_version()
            logger.info("OCR Service initialized with pytesseract")
        except Exception as e:
            logger.error(f"Failed to initialize OCR Service: {str(e)}")
    
    def _process_image(self, image):
        """
        Process a single image with OCR
        
        Args:
            image: PIL Image to process
            
        Returns:
            str: Extracted text
        """
        try:
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            return ""
    
    def _process_pdf(self, file_path):
        """
        Process a PDF file with OCR
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        try:
            # Convert PDF to images
            pages = convert_from_path(file_path)
            
            if not pages:
                logger.error(f"Failed to convert PDF to images: {file_path}")
                return ""
            
            # Process each page with OCR
            texts = []
            for i, page in enumerate(pages):
                logger.info(f"Processing page {i+1}/{len(pages)}")
                text = self._process_image(page)
                texts.append(text)
            
            # Join all extracted text
            full_text = "\n\n".join(texts)
            return full_text
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return ""
    
    def _process_image_file(self, file_path):
        """
        Process an image file with OCR
        
        Args:
            file_path: Path to image file
            
        Returns:
            str: Extracted text
        """
        try:
            # Open image file
            image = Image.open(file_path)
            
            # Process image with OCR
            text = self._process_image(image)
            return text
        except Exception as e:
            logger.error(f"Error processing image file: {str(e)}")
            return ""
    
    def extract_text(self, file_path):
        """
        Extract text from a document file
        
        Args:
            file_path: Path to document file (PDF or image)
            
        Returns:
            str: Extracted text
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return ""
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Process file based on extension
            if file_ext == '.pdf':
                return self._process_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
                return self._process_image_file(file_path)
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""