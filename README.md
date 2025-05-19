# AI-Powered Contract Management System

## Overview
This is a backend system for an AI-powered contract management platform that automates the extraction, analysis, and management of contracts. The system uses OCR and OpenAI to process contract documents, extract key information, analyze risks, and streamline contract workflows.

## Features

### Contract Management
- Create, view, update, and delete contracts
- Repository of all contracts with filtering and search capabilities
- Document storage and retrieval
- Contract lifecycle management (draft, active, expired, etc.)

### AI-Powered Document Processing
- Automated text extraction from PDFs and images using OCR
- Structured data extraction using OpenAI integration
- Risk assessment and scoring of contracts
- Analysis of contract clauses for completeness and quality

### Approval Workflow
- Multi-level approval process
- Role-based permissions
- Status tracking and notifications

### Invoice Management
- Invoice generation from contract data
- Support for recurring invoices
- Payment tracking

### Dashboard and Analytics
- Contract metrics and KPIs
- Expiring contracts alerts
- Renewal rate tracking

## Technical Architecture

### Backend Stack
- **Framework**: Flask (Python)
- **Database**: PostgreSQL
- **Authentication**: JWT-based authentication
- **OCR Engine**: pytesseract
- **AI Integration**: OpenAI (model: gpt-4o-mini-2024-07-18)
- **File Storage**: Local storage with S3 compatibility

### Core Components

#### API Endpoints
The system provides RESTful API endpoints for:
- `/v1/contracts`: Contract CRUD operations
- `/v1/ai`: AI processing endpoints
- `/v1/invoices`: Invoice management
- `/v1/approvals`: Approval workflow
- `/v1/notifications`: User notifications
- `/v1/settings`: System settings
- `/v1/contracts/search`: Advanced search

#### Services
- **OCR Service**: Extracts text from documents
- **AI Service**: Processes extracted text using OpenAI
- **Storage Service**: Manages file uploads and retrieval
- **Invoice Service**: Handles invoice generation and management
- **Notification Service**: Manages user notifications

#### Database Models
- `User`: User accounts and roles
- `Contract`: Core contract information
- `ContractParty`: Parties involved in contracts
- `ContractMetadata`: Extracted metadata and AI analysis
- `Invoice`: Invoice information
- `Approval`: Approval workflow status
- `Notification`: User notifications

## Setup and Usage

### Requirements
- Python 3.10+
- PostgreSQL
- OpenAI API key

### Environment Variables
- `DATABASE_URL`: PostgreSQL database URL
- `OPENAI_API_KEY`: OpenAI API key
- `SESSION_SECRET`: Secret key for session management

### Database Setup
Initialize and seed the database with sample data:

```bash
# Initialize the database
python scripts/database_setup.py init

# Seed sample data
python scripts/database_setup.py seed
```

### Running the Application
Start the application with:

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## API Documentation

### Contract Endpoints

#### Get All Contracts
```
GET /v1/contracts
```
Query parameters:
- `status`: Filter by contract status
- `type`: Filter by contract type
- `search`: Search in title and description
- `tags`: Filter by tags (comma-separated)
- `sort_by`: Field to sort by
- `page`: Page number

#### Create a Contract
```
POST /v1/contracts
```
Form data:
- `title`: Contract title (required)
- `contract_type`: Type of contract (required)
- `description`: Contract description
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)
- `value`: Contract value
- `currency`: Currency code (default: USD)
- `payment_terms`: Payment terms
- `tags`: Comma-separated tags
- `document`: Contract document file

#### Get Contract by ID
```
GET /v1/contracts/{contract_id}
```

#### Update Contract
```
PUT /v1/contracts/{contract_id}
```

#### Delete Contract
```
DELETE /v1/contracts/{contract_id}
```

#### Extract Contract Data
```
POST /v1/contracts/{contract_id}/extract
```
Extracts data from uploaded contract using AI.

### AI Endpoints

#### Extract Document
```
POST /v1/ai/extract-document
```
Extracts structured data from a document using OCR and AI.

#### Analyze Clauses
```
POST /v1/ai/analyze-clauses
```
Analyzes contract clauses for quality and missing important clauses.

#### Analyze Risk
```
POST /v1/ai/analyze-risk
```
Calculates risk score for a contract based on extracted data.

### Dashboard Metrics
```
GET /v1/contracts/metrics
```
Returns contract metrics for dashboard:
- Total contracts count
- Active contracts count
- Contracts expiring soon
- Renewal rate
- Contracts by type and status
- Total contract value

## Business Rules
- Contracts with recurring invoices cannot be deleted
- Contracts with high risk scores are automatically flagged
- Contracts above certain value thresholds require multi-level approval

## Future Enhancements
- Document comparison and versioning
- Template generation for new contracts
- Advanced clause extraction and negotiation assistance
- Integration with e-signature providers
- Performance optimization for large document processing

## License
Proprietary - All rights reserved