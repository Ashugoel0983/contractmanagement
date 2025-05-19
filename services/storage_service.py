"""
Storage Service for Contract Management System
"""

import os
import logging
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

# Set up logging
logger = logging.getLogger(__name__)

class StorageService:
    """
    Storage Service for managing file uploads and retrievals
    Supports both local file storage and S3 storage (when configured)
    """
    
    def __init__(self):
        """Initialize storage service"""
        # Check if using S3 or local storage
        self.use_s3 = os.environ.get("USE_S3", "False").lower() == "true"
        
        if self.use_s3:
            # Import boto3 only if using S3
            import boto3
            
            # Initialize S3 client
            self.s3_bucket = os.environ.get("S3_BUCKET")
            self.s3_region = os.environ.get("S3_REGION", "us-east-1")
            
            if not self.s3_bucket:
                logger.warning("S3_BUCKET not found in environment variables")
            
            self.s3_client = boto3.client('s3', region_name=self.s3_region)
            logger.info(f"Using S3 storage with bucket: {self.s3_bucket}")
        else:
            # Using local file storage
            self.upload_folder = os.environ.get("UPLOAD_FOLDER", "uploads")
            
            # Ensure upload folder exists
            if not os.path.exists(self.upload_folder):
                os.makedirs(self.upload_folder)
            
            logger.info("Using local file storage")
    
    def save_file(self, file, filename=None):
        """
        Save a file to storage
        
        Args:
            file: File object to save
            filename: Optional filename to use (if None, generate a unique name)
            
        Returns:
            str: Path or URL to the saved file
        """
        try:
            # Get secure filename
            if filename is None:
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                filename = f"{uuid.uuid4().hex}.{file_ext}" if file_ext else f"{uuid.uuid4().hex}"
            
            if self.use_s3:
                # Save to S3
                self.s3_client.upload_fileobj(
                    file,
                    self.s3_bucket,
                    filename
                )
                
                # Return S3 path
                return f"s3://{self.s3_bucket}/{filename}"
            else:
                # Save to local file system
                file_path = os.path.join(self.upload_folder, filename)
                file.save(file_path)
                
                # Return local path
                return file_path
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def get_file(self, file_path):
        """
        Get a file from storage
        
        Args:
            file_path: Path or URL to the file
            
        Returns:
            bytes: File content
        """
        try:
            if file_path.startswith('s3://'):
                # Parse S3 path
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Get from S3
                response = self.s3_client.get_object(
                    Bucket=bucket,
                    Key=key
                )
                
                # Return file content
                return response['Body'].read()
            else:
                # Get from local file system
                with open(file_path, 'rb') as f:
                    return f.read()
        
        except Exception as e:
            logger.error(f"Error getting file: {str(e)}")
            raise
    
    def delete_file(self, file_path):
        """
        Delete a file from storage
        
        Args:
            file_path: Path or URL to the file
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            if file_path.startswith('s3://'):
                # Parse S3 path
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Delete from S3
                self.s3_client.delete_object(
                    Bucket=bucket,
                    Key=key
                )
                
                return True
            else:
                # Delete from local file system
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                
                return False
        
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    def get_file_url(self, file_path, expiration=3600):
        """
        Get a temporary URL for a file
        
        Args:
            file_path: Path or URL to the file
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Temporary URL to access the file
        """
        try:
            if file_path.startswith('s3://'):
                # Parse S3 path
                parts = file_path.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Generate presigned URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket,
                        'Key': key
                    },
                    ExpiresIn=expiration
                )
                
                return url
            else:
                # For local files, return a relative URL
                # This assumes the file is accessible via a static route
                base_url = current_app.config.get('BASE_URL', '')
                rel_path = os.path.relpath(file_path, self.upload_folder)
                return f"{base_url}/uploads/{rel_path}"
        
        except Exception as e:
            logger.error(f"Error generating file URL: {str(e)}")
            return None