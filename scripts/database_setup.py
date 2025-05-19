#!/usr/bin/env python3
"""
Database Setup and Maintenance Script for Contract Management System

This script provides utilities for:
1. Initializing the database tables
2. Seeding the database with sample data
3. Cleaning the database for testing
4. Creating backup of the database

Usage: python database_setup.py [operation]
Operations:
  - init      : Initialize database tables
  - seed      : Seed database with sample data
  - clean     : Clean all data from database
  - backup    : Create database backup
"""

import os
import sys
import logging
import uuid
import json
from datetime import datetime, timedelta
import argparse

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import (
    User, Contract, ContractParty, ContractMetadata, 
    Invoice, Approval, Notification,
    UserRole, ContractType, ContractStatus, 
    ApprovalStatus, ApprovalLevel, NotificationType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database tables"""
    try:
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully!")
            
            # Show created tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Created tables: {', '.join(tables)}")
            
            return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False


def seed_sample_users():
    """Seed database with sample users"""
    try:
        with app.app_context():
            logger.info("Seeding sample users...")
            
            # Check if users already exist
            if User.query.count() > 0:
                logger.info("Users already exist, skipping user seeding")
                return True
            
            # Sample users data
            users_data = [
                {
                    "auth0_id": f"auth0|{uuid.uuid4()}",
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "role": UserRole.ADMIN
                },
                {
                    "auth0_id": f"auth0|{uuid.uuid4()}",
                    "email": "manager@example.com",
                    "name": "Manager User",
                    "role": UserRole.MANAGER
                },
                {
                    "auth0_id": f"auth0|{uuid.uuid4()}",
                    "email": "user@example.com",
                    "name": "Regular User",
                    "role": UserRole.USER
                }
            ]
            
            # Create users
            users = []
            for user_data in users_data:
                user = User()
                user.auth0_id = user_data["auth0_id"]
                user.email = user_data["email"]
                user.name = user_data["name"]
                user.role = user_data["role"]
                user.is_active = True
                
                db.session.add(user)
                users.append(user)
            
            db.session.commit()
            logger.info(f"Added {len(users)} sample users")
            
            return users
    except Exception as e:
        logger.error(f"Error seeding sample users: {str(e)}")
        db.session.rollback()
        return False


def seed_sample_contracts(users):
    """Seed database with sample contracts"""
    try:
        with app.app_context():
            logger.info("Seeding sample contracts...")
            
            # Check if contracts already exist
            if Contract.query.count() > 0:
                logger.info("Contracts already exist, skipping contract seeding")
                return True
            
            # Sample contracts data
            contracts_data = [
                {
                    "title": "Software Development Agreement",
                    "contract_type": ContractType.SERVICE_AGREEMENT,
                    "status": ContractStatus.ACTIVE,
                    "description": "Agreement for custom software development services",
                    "start_date": datetime.utcnow() - timedelta(days=30),
                    "end_date": datetime.utcnow() + timedelta(days=335),
                    "value": 75000.00,
                    "currency": "USD",
                    "payment_terms": "Monthly invoicing with Net-30 payment terms",
                    "tags": ["software", "development", "services"]
                },
                {
                    "title": "Office Lease Agreement",
                    "contract_type": ContractType.LEASE_AGREEMENT,
                    "status": ContractStatus.ACTIVE,
                    "description": "Lease agreement for office space",
                    "start_date": datetime.utcnow() - timedelta(days=60),
                    "end_date": datetime.utcnow() + timedelta(days=305),
                    "value": 60000.00,
                    "currency": "USD",
                    "payment_terms": "Monthly payment due on the 1st",
                    "tags": ["lease", "office", "real-estate"]
                },
                {
                    "title": "IT Support Services Agreement",
                    "contract_type": ContractType.SERVICE_AGREEMENT,
                    "status": ContractStatus.DRAFT,
                    "description": "Agreement for ongoing IT support and maintenance",
                    "start_date": datetime.utcnow() + timedelta(days=15),
                    "end_date": datetime.utcnow() + timedelta(days=380),
                    "value": 48000.00,
                    "currency": "USD",
                    "payment_terms": "Quarterly invoicing with Net-15 payment terms",
                    "tags": ["it", "support", "maintenance"]
                },
                {
                    "title": "Software License Agreement",
                    "contract_type": ContractType.LICENSE_AGREEMENT,
                    "status": ContractStatus.EXPIRED,
                    "description": "License agreement for enterprise software suite",
                    "start_date": datetime.utcnow() - timedelta(days=400),
                    "end_date": datetime.utcnow() - timedelta(days=35),
                    "value": 120000.00,
                    "currency": "USD",
                    "payment_terms": "Annual payment in advance",
                    "tags": ["software", "license", "enterprise"]
                },
                {
                    "title": "Marketing Services Contract",
                    "contract_type": ContractType.SERVICE_AGREEMENT,
                    "status": ContractStatus.PENDING_APPROVAL,
                    "description": "Contract for marketing services including branding and digital marketing",
                    "start_date": datetime.utcnow() + timedelta(days=10),
                    "end_date": datetime.utcnow() + timedelta(days=375),
                    "value": 85000.00,
                    "currency": "USD",
                    "payment_terms": "Monthly invoicing with performance bonuses",
                    "tags": ["marketing", "branding", "digital"]
                }
            ]
            
            # Create contracts and associate with users
            contracts = []
            for i, contract_data in enumerate(contracts_data):
                # Rotate through users for ownership
                owner = users[i % len(users)]
                
                # Generate contract number
                contract_number = f"CNT-{uuid.uuid4().hex[:8].upper()}"
                
                contract = Contract()
                contract.contract_number = contract_number
                contract.title = contract_data["title"]
                contract.contract_type = contract_data["contract_type"]
                contract.status = contract_data["status"]
                contract.description = contract_data["description"]
                contract.start_date = contract_data["start_date"]
                contract.end_date = contract_data["end_date"]
                contract.value = contract_data["value"]
                contract.currency = contract_data["currency"]
                contract.payment_terms = contract_data["payment_terms"]
                contract.owner_id = owner.id
                contract.tags = contract_data["tags"]
                
                db.session.add(contract)
                db.session.flush()  # Get ID before commit
                
                # Add a contract party
                party = ContractParty()
                party.contract_id = contract.id
                party.party_type = "client"
                party.legal_name = f"Client Company {i+1}"
                party.address = f"123 Business St, Suite {i+100}, Business City, 90210"
                party.contact_person = f"Contact Person {i+1}"
                party.email = f"contact{i+1}@client{i+1}.com"
                party.phone = f"555-{100+i}-{1000+i}"
                db.session.add(party)
                
                # Add contract metadata
                metadata = ContractMetadata()
                metadata.contract_id = contract.id
                metadata.invoice_required = True if i % 2 == 0 else False
                metadata.jurisdiction = "California, USA"
                metadata.governing_law = "California Law"
                metadata.dispute_resolution = "Arbitration in San Francisco, CA"
                metadata.ai_confidence_score = 0.85
                db.session.add(metadata)
                
                # Add an invoice if required
                if metadata.invoice_required:
                    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
                    invoice = Invoice()
                    invoice.invoice_number = invoice_number
                    invoice.contract_id = contract.id
                    invoice.amount = contract_data["value"] / 12  # Monthly amount
                    invoice.currency = contract_data["currency"]
                    invoice.due_date = datetime.utcnow() + timedelta(days=15)
                    invoice.issue_date = datetime.utcnow()
                    invoice.is_recurring = True if i % 2 == 0 else False
                    invoice.frequency = "monthly" if i % 2 == 0 else None
                    invoice.template_type = "standard"
                    invoice.status = "draft"
                    db.session.add(invoice)
                
                # Add approval if pending
                if contract_data["status"] == ContractStatus.PENDING_APPROVAL:
                    approval = Approval()
                    approval.contract_id = contract.id
                    approval.approver_id = users[0].id  # Admin user is approver
                    approval.level = ApprovalLevel.LEVEL1
                    approval.status = ApprovalStatus.PENDING
                    db.session.add(approval)
                
                # Add a notification
                notification = Notification()
                notification.user_id = owner.id
                notification.contract_id = contract.id
                notification.type = NotificationType.SYSTEM
                notification.message = f"New {contract_data['contract_type'].value} contract created: {contract_data['title']}"
                notification.is_read = False
                notification.action_link = f"/contracts/{contract.id}"
                db.session.add(notification)
                
                contracts.append(contract)
            
            db.session.commit()
            logger.info(f"Added {len(contracts)} sample contracts with associated data")
            
            return True
    except Exception as e:
        logger.error(f"Error seeding sample contracts: {str(e)}")
        db.session.rollback()
        return False


def seed_db():
    """Seed the database with sample data"""
    try:
        with app.app_context():
            users = seed_sample_users()
            if users:
                seed_sample_contracts(users)
            return True
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        return False


def clean_db():
    """Clean all data from database"""
    try:
        with app.app_context():
            logger.info("Cleaning database...")
            
            # Delete all data, respecting foreign key constraints
            Notification.query.delete()
            Approval.query.delete()
            Invoice.query.delete()
            ContractMetadata.query.delete()
            ContractParty.query.delete()
            Contract.query.delete()
            User.query.delete()
            
            db.session.commit()
            logger.info("Database cleaned successfully!")
            
            return True
    except Exception as e:
        logger.error(f"Error cleaning database: {str(e)}")
        db.session.rollback()
        return False


def backup_db():
    """Create database backup"""
    try:
        with app.app_context():
            logger.info("Creating database backup...")
            
            # Export data tables to JSON
            backup_data = {
                "users": [],
                "contracts": [],
                "contract_parties": [],
                "contract_metadata": [],
                "invoices": [],
                "approvals": [],
                "notifications": []
            }
            
            # Export users
            users = User.query.all()
            for user in users:
                user_data = user.to_dict()
                user_data["role"] = user.role.value
                backup_data["users"].append(user_data)
            
            # Export contracts
            contracts = Contract.query.all()
            for contract in contracts:
                contract_data = contract.to_dict()
                contract_data["contract_type"] = contract.contract_type.value
                contract_data["status"] = contract.status.value
                backup_data["contracts"].append(contract_data)
            
            # Export contract parties
            parties = ContractParty.query.all()
            for party in parties:
                backup_data["contract_parties"].append(party.to_dict())
            
            # Export contract metadata
            metadata_records = ContractMetadata.query.all()
            for metadata in metadata_records:
                backup_data["contract_metadata"].append(metadata.to_dict())
            
            # Export invoices
            invoices = Invoice.query.all()
            for invoice in invoices:
                backup_data["invoices"].append(invoice.to_dict())
            
            # Export approvals
            approvals = Approval.query.all()
            for approval in approvals:
                approval_data = approval.to_dict()
                approval_data["status"] = approval.status.value
                approval_data["level"] = approval.level.value
                backup_data["approvals"].append(approval_data)
            
            # Export notifications
            notifications = Notification.query.all()
            for notification in notifications:
                notification_data = notification.to_dict()
                notification_data["type"] = notification.type.value
                backup_data["notifications"].append(notification_data)
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Save backup to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"database_backup_{timestamp}.json")
            
            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Database backup created: {backup_file}")
            
            return True
    except Exception as e:
        logger.error(f"Error creating database backup: {str(e)}")
        return False


def main():
    """Main function to handle script arguments"""
    parser = argparse.ArgumentParser(description="Database setup and maintenance script")
    parser.add_argument("operation", choices=["init", "seed", "clean", "backup"], 
                       help="Operation to perform on the database")
    
    args = parser.parse_args()
    
    if args.operation == "init":
        init_db()
    elif args.operation == "seed":
        seed_db()
    elif args.operation == "clean":
        clean_db()
    elif args.operation == "backup":
        backup_db()


if __name__ == "__main__":
    main()