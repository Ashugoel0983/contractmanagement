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

# Enable CORS
CORS(app, supports_credentials=True)

# Configure proxy fix for proper URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize the database with the app
db.init_app(app)

# Import and register API blueprints
with app.app_context():
    # Import models for table creation
    from models import User, Contract, ContractParty, ContractMetadata, Invoice, Approval, Notification

    # Import API blueprints
    from api.contracts import contracts_bp
    from api.users import users_bp
    from api.ai import ai_bp
    from api.invoices import invoices_bp
    from api.approvals import approvals_bp
    from api.notifications import notifications_bp
    from api.settings import settings_bp
    from api.search import search_bp

    # Register API blueprints
    app.register_blueprint(contracts_bp, url_prefix='/v1/contracts')
    app.register_blueprint(users_bp, url_prefix='/v1/users')
    app.register_blueprint(ai_bp, url_prefix='/v1/ai')
    app.register_blueprint(invoices_bp, url_prefix='/v1/invoices')
    app.register_blueprint(approvals_bp, url_prefix='/v1/approvals')
    app.register_blueprint(notifications_bp, url_prefix='/v1/notifications')
    app.register_blueprint(settings_bp, url_prefix='/v1/settings')
    app.register_blueprint(search_bp, url_prefix='/v1/contracts/search')

    # Create all database tables
    db.create_all()

# Health check endpoint
@app.route('/v1/health', methods=['GET'])
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
