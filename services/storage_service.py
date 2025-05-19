import os
import logging
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import uuid

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        """Initialize the storage service for handling file uploads"""
        self.upload_folder = os.environ.get("UPLOAD_FOLDER", "./uploads")
        self.use_s3 = os.environ.get("USE_S3", "False") == "True"
        
        # Create local upload folder if it doesn't exist
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
            logger.info(f"Created local upload folder: {self.upload_folder}")
        
        # Initialize S3 client if enabled
        if self.use_s3:
            self.s3_bucket = os.environ.get("S3_BUCKET")
            self.s3_region = os.environ.get("S3_REGION", "us-east-1")
            try:
                self.s3_client = boto3.client('s3', region_name=self.s3_region)
                logger.info(f"Initialized S3 storage with bucket: {self.s3_bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                self.use_s3 = False
        else:
            logger.info("Using local file storage")
    
    def save_file(self, file, prefix="contracts", allowed_extensions=None):
        """
        Save a file to storage (local or S3)
        Args:
            file: File object from request
            prefix: Directory prefix for organizing files
            allowed_extensions: Set of allowed file extensions
        Returns:
            str: File path or S3 URL
        """
        if allowed_extensions is None:
            allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        
        try:
            # Validate file extension
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            if ext not in allowed_extensions:
                raise ValueError(f"File extension '{ext}' not allowed")
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            if self.use_s3:
                # Upload to S3
                s3_key = f"{prefix}/{unique_filename}"
                self.s3_client.upload_fileobj(file, self.s3_bucket, s3_key)
                file_path = f"s3://{self.s3_bucket}/{s3_key}"
                logger.info(f"File uploaded to S3: {file_path}")
            else:
                # Save to local storage
                prefix_path = os.path.join(self.upload_folder, prefix)
                if not os.path.exists(prefix_path):
                    os.makedirs(prefix_path)
                
                file_path = os.path.join(prefix_path, unique_filename)
                file.save(file_path)
                logger.info(f"File saved locally: {file_path}")
            
            return file_path
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def get_file(self, file_path):
        """
        Get a file from storage (local or S3)
        Args:
            file_path: Path or URL to the file
        Returns:
            bytes: File content
        """
        try:
            if file_path.startswith('s3://'):
                # Parse S3 URL
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Download from S3
                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                file_content = response['Body'].read()
                logger.info(f"File retrieved from S3: {file_path}")
            else:
                # Read from local storage
                with open(file_path, 'rb') as file:
                    file_content = file.read()
                logger.info(f"File retrieved from local storage: {file_path}")
            
            return file_content
        
        except Exception as e:
            logger.error(f"Error retrieving file: {str(e)}")
            raise
    
    def delete_file(self, file_path):
        """
        Delete a file from storage (local or S3)
        Args:
            file_path: Path or URL to the file
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if file_path.startswith('s3://'):
                # Parse S3 URL
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Delete from S3
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                logger.info(f"File deleted from S3: {file_path}")
            else:
                # Delete from local storage
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"File deleted from local storage: {file_path}")
                else:
                    logger.warning(f"File not found for deletion: {file_path}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False