import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SESSION_SECRET", os.urandom(24))
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"
    
    # Database Configuration
    # Support multiple database types based on environment variable
    DB_TYPE = os.environ.get("DB_TYPE", "postgresql")  # Options: postgresql, mysql, sqlite
    
    # Default database URIs based on type
    if DB_TYPE == "mysql":
        DEFAULT_DB_URI = "mysql+pymysql://root:password@localhost:3306/contractdb"
    elif DB_TYPE == "sqlite":
        DEFAULT_DB_URI = "sqlite:///contracts.db"
    else:  # Default to PostgreSQL
        DEFAULT_DB_URI = "postgresql://postgres:postgres@localhost:5432/contractdb"
    
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_DB_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Auth0 Configuration
    AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "your-tenant.auth0.com")
    AUTH0_ALGORITHMS = ['RS256']
    AUTH0_API_AUDIENCE = os.environ.get("AUTH0_API_AUDIENCE", "https://api.febi.com")
    
    # File Storage Configuration
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    # S3 Storage Configuration (optional)
    USE_S3 = os.environ.get("USE_S3", "False") == "True"
    S3_BUCKET = os.environ.get("S3_BUCKET", "febi-contracts")
    S3_REGION = os.environ.get("S3_REGION", "us-east-1")
    
    # AI and OCR Configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    USE_GEMINI = os.environ.get("USE_GEMINI", "False") == "True"
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # App Business Rules
    APPROVAL_THRESHOLDS = {
        "level1": 50000,
        "level2": 100000,
        "level3": 500000,
        "level4": float('inf')
    }
