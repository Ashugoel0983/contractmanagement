from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON, ARRAY
import enum


class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class ContractStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    RISK_FLAGGED = "risk_flagged"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"


class ContractType(enum.Enum):
    SERVICE_AGREEMENT = "Service Agreement"
    VENDOR_CONTRACT = "Vendor Contract"
    LEASE_AGREEMENT = "Lease Agreement"
    LICENSE_AGREEMENT = "License Agreement"
    NDA = "NDA"
    EMPLOYMENT = "Employment"
    OTHER = "Other"


class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalLevel(enum.Enum):
    LEVEL1 = "level1"
    LEVEL2 = "level2"
    LEVEL3 = "level3"
    LEVEL4 = "level4"


class NotificationType(enum.Enum):
    EXPIRY = "expiry"
    INVOICE = "invoice"
    APPROVAL = "approval"
    SYSTEM = "system"


class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    auth0_id = Column(String(128), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    name = Column(String(128))
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contracts = relationship("Contract", back_populates="owner")
    approvals = relationship("Approval", back_populates="approver")
    
    def __repr__(self):
        return f"<User {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "auth0_id": self.auth0_id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Contract(db.Model):
    __tablename__ = 'contracts'
    
    id = Column(Integer, primary_key=True)
    contract_number = Column(String(128), unique=True)
    title = Column(String(256), nullable=False)
    contract_type = Column(Enum(ContractType), nullable=False)
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT)
    description = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    value = Column(Float)
    currency = Column(String(3), default="USD")
    payment_terms = Column(String(128))
    owner_id = Column(Integer, ForeignKey('users.id'))
    file_path = Column(String(512))
    extracted_text = Column(Text)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="contracts")
    parties = relationship("ContractParty", back_populates="contract", cascade="all, delete-orphan")
    metadata = relationship("ContractMetadata", back_populates="contract", uselist=False, cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="contract", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="contract", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="contract", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contract {self.title}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "contract_number": self.contract_number,
            "title": self.title,
            "contract_type": self.contract_type.value,
            "status": self.status.value,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "value": self.value,
            "currency": self.currency,
            "payment_terms": self.payment_terms,
            "owner_id": self.owner_id,
            "owner": self.owner.name if self.owner else None,
            "file_path": self.file_path,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "parties": [party.to_dict() for party in self.parties] if self.parties else [],
            "has_invoices": bool(self.invoices)
        }


class ContractParty(db.Model):
    __tablename__ = 'contract_parties'
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False)
    party_type = Column(String(128))  # 'our_company', 'client', 'vendor', etc.
    legal_name = Column(String(256), nullable=False)
    address = Column(String(512))
    contact_person = Column(String(256))
    email = Column(String(128))
    phone = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="parties")
    
    def __repr__(self):
        return f"<ContractParty {self.legal_name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "party_type": self.party_type,
            "legal_name": self.legal_name,
            "address": self.address,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ContractMetadata(db.Model):
    __tablename__ = 'contract_metadata'
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False, unique=True)
    invoice_required = Column(Boolean, default=False)
    jurisdiction = Column(String(128))
    governing_law = Column(String(128))
    dispute_resolution = Column(String(512))
    termination_clause = Column(Text)
    confidentiality_clause = Column(Text)
    limitation_of_liability = Column(Text)
    force_majeure = Column(Text)
    indemnification = Column(Text)
    ai_confidence_score = Column(Float, default=0.0)
    risk_flags = Column(JSON)  # Store flags like {'missing_clauses': [...], 'risky_clauses': [...]}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="metadata")
    
    def __repr__(self):
        return f"<ContractMetadata for contract {self.contract_id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "invoice_required": self.invoice_required,
            "jurisdiction": self.jurisdiction,
            "governing_law": self.governing_law,
            "dispute_resolution": self.dispute_resolution,
            "termination_clause": self.termination_clause,
            "confidentiality_clause": self.confidentiality_clause,
            "limitation_of_liability": self.limitation_of_liability,
            "force_majeure": self.force_majeure,
            "indemnification": self.indemnification,
            "ai_confidence_score": self.ai_confidence_score,
            "risk_flags": self.risk_flags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(128), unique=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    due_date = Column(DateTime)
    issue_date = Column(DateTime, default=datetime.utcnow)
    is_recurring = Column(Boolean, default=False)
    frequency = Column(String(64))  # monthly, quarterly, etc.
    template_type = Column(String(64), default="standard")  # standard, detailed, minimal
    status = Column(String(64), default="draft")  # draft, sent, paid, overdue
    payment_method = Column(String(64))
    payment_notes = Column(Text)
    file_path = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="invoices")
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "contract_id": self.contract_id,
            "contract_title": self.contract.title if self.contract else None,
            "amount": self.amount,
            "currency": self.currency,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "is_recurring": self.is_recurring,
            "frequency": self.frequency,
            "template_type": self.template_type,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_notes": self.payment_notes,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Approval(db.Model):
    __tablename__ = 'approvals'
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'))
    level = Column(Enum(ApprovalLevel), nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")
    
    def __repr__(self):
        return f"<Approval for contract {self.contract_id} by {self.approver_id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "contract_title": self.contract.title if self.contract else None,
            "approver_id": self.approver_id,
            "approver_name": self.approver.name if self.approver else None,
            "level": self.level.value,
            "status": self.status.value,
            "comments": self.comments,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=True)
    type = Column(Enum(NotificationType))
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    action_link = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification {self.id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "contract_id": self.contract_id,
            "contract_title": self.contract.title if self.contract else None,
            "type": self.type.value,
            "message": self.message,
            "is_read": self.is_read,
            "action_link": self.action_link,
            "created_at": self.created_at.isoformat()
        }
