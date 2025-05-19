import os
import io
import logging
import tempfile
from werkzeug.utils import secure_filename
from paddleocr import PaddleOCR
import pdf2image
from PIL import Image

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, language='en'):
        """Initialize the OCR service with PaddleOCR"""
        self.ocr = PaddleOCR(use_angle_cls=True, lang=language)
        logger.info("PaddleOCR initialized")

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF using OCR
        Args:
            pdf_path: Path to the PDF file
        Returns:
            str: Extracted text
        """
        try:
            # Convert PDF to images
            logger.info(f"Converting PDF to images: {pdf_path}")
            images = pdf2image.convert_from_path(pdf_path)
            
            all_text = []
            
            # Process each page
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Process image with OCR
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                    temp.write(img_byte_arr)
                    temp_path = temp.name
                
                result = self.ocr.ocr(temp_path, cls=True)
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                # Extract text from result
                page_text = ""
                if result:
                    for line in result:
                        for word_info in line:
                            if isinstance(word_info, list) and len(word_info) >= 2:
                                page_text += word_info[1][0] + " "
                    
                    all_text.append(page_text.strip())
            
            # Combine text from all pages
            full_text = "\n\n".join(all_text)
            logger.info(f"Successfully extracted {len(all_text)} pages of text")
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def extract_text_from_image(self, image_path):
        """
        Extract text from an image using OCR
        Args:
            image_path: Path to the image file
        Returns:
            str: Extracted text
        """
        try:
            logger.info(f"Processing image: {image_path}")
            
            # Process image with OCR
            result = self.ocr.ocr(image_path, cls=True)
            
            # Extract text from result
            text = ""
            if result:
                for line in result:
                    for word_info in line:
                        if isinstance(word_info, list) and len(word_info) >= 2:
                            text += word_info[1][0] + " "
            
            logger.info(f"Successfully extracted text from image")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise

    def process_file(self, file_path):
        """
        Extract text from a file (PDF or image)
        Args:
            file_path: Path to the file
        Returns:
            str: Extracted text
        """
        filename = os.path.basename(file_path)
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
