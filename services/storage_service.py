import os
import uuid
import boto3
import logging
from werkzeug.utils import secure_filename
from config import Config

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        """Initialize the storage service for file handling"""
        self.upload_folder = Config.UPLOAD_FOLDER
        self.use_s3 = Config.USE_S3
        self.s3_bucket = Config.S3_BUCKET
        self.s3_region = Config.S3_REGION
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        
        # Create upload folder if it doesn't exist
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
            
        # Initialize S3 client if using S3
        if self.use_s3:
            self.s3_client = boto3.client('s3', region_name=self.s3_region)
            logger.info(f"S3 storage initialized with bucket: {self.s3_bucket}")
        else:
            logger.info(f"Local storage initialized with folder: {self.upload_folder}")

    def allowed_file(self, filename):
        """
        Check if the file extension is allowed
        Args:
            filename: The filename to check
        Returns:
            bool: True if file extension is allowed, False otherwise
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def save_file(self, file, contract_id=None):
        """
        Save an uploaded file to local storage or S3
        Args:
            file: File object from request
            contract_id: Optional contract ID to associate with the file
        Returns:
            str: Path to the saved file
        """
        try:
            if not file:
                raise ValueError("No file provided")
            
            if not self.allowed_file(file.filename):
                raise ValueError(f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}")
            
            # Generate a unique filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create subfolder for contract if contract_id is provided
            subfolder = f"contract_{contract_id}" if contract_id else "unassigned"
            
            if self.use_s3:
                # Save to S3
                logger.info(f"Saving file to S3: {unique_filename}")
                s3_path = f"{subfolder}/{unique_filename}"
                
                self.s3_client.upload_fileobj(
                    file,
                    self.s3_bucket,
                    s3_path
                )
                
                # Generate S3 URL
                file_path = f"s3://{self.s3_bucket}/{s3_path}"
                logger.info(f"File saved to S3: {file_path}")
                return file_path
            else:
                # Save to local storage
                folder_path = os.path.join(self.upload_folder, subfolder)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    
                file_path = os.path.join(folder_path, unique_filename)
                file.save(file_path)
                
                logger.info(f"File saved locally: {file_path}")
                return file_path
                
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise

    def get_file(self, file_path):
        """
        Retrieve a file from local storage or S3
        Args:
            file_path: Path to the file
        Returns:
            bytes: File content
        """
        try:
            if file_path.startswith('s3://'):
                if not self.use_s3:
                    raise ValueError("S3 storage is not enabled")
                
                # Parse S3 path
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Get file from S3
                logger.info(f"Getting file from S3: {file_path}")
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                return response['Body'].read()
            else:
                # Get file from local storage
                logger.info(f"Getting file from local storage: {file_path}")
                with open(file_path, 'rb') as f:
                    return f.read()
                
        except Exception as e:
            logger.error(f"Error getting file: {str(e)}")
            raise

    def delete_file(self, file_path):
        """
        Delete a file from local storage or S3
        Args:
            file_path: Path to the file
        Returns:
            bool: True if deletion was successful
        """
        try:
            if file_path.startswith('s3://'):
                if not self.use_s3:
                    raise ValueError("S3 storage is not enabled")
                
                # Parse S3 path
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Delete file from S3
                logger.info(f"Deleting file from S3: {file_path}")
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                return True
            else:
                # Delete file from local storage
                logger.info(f"Deleting file from local storage: {file_path}")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                else:
                    logger.warning(f"File not found: {file_path}")
                    return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise
