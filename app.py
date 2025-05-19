import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    pass


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)

# Configure Flask app
app.config.from_object('config.Config')
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))

# Set up upload folder and allowed extensions
app.config['UPLOAD_FOLDER'] = os.environ.get("UPLOAD_FOLDER", "uploads")
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Enable CORS
CORS(app, supports_credentials=True)

# Configure proxy fix for proper URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize the database with the app
db.init_app(app)

# Initialize services for global use
from services.storage_service import StorageService
from services.ocr_service import OCRService
from services.ai_service import AIService

storage_service = StorageService()
ocr_service = OCRService()
ai_service = AIService()

# Import and register API blueprints
with app.app_context():
    # Import models for table creation
    from models import User, Contract, ContractParty, ContractMetadata, Invoice, Approval, Notification

    # Import API blueprints
    from api.auth import auth_bp
    from api.uploads import upload_bp
    from api.contracts import contracts_bp
    
    # Register API blueprints
    app.register_blueprint(auth_bp, url_prefix='/v1/auth')
    app.register_blueprint(upload_bp, url_prefix='/v1/uploads')
    app.register_blueprint(contracts_bp, url_prefix='/v1/contracts')

    # Create all database tables
    db.create_all()

    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# Health check endpoint
@app.route('/v1/health', methods=['GET'])
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
