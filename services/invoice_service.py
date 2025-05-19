import os
import uuid
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from models import Invoice
from app import db

logger = logging.getLogger(__name__)

class InvoiceService:
    def __init__(self):
        """Initialize the invoice service"""
        logger.info("Invoice service initialized")

    def generate_invoice_number(self):
        """
        Generate a unique invoice number
        Returns:
            str: Unique invoice number
        """
        # Format: INV-YYYYMMDD-XXXX where XXXX is a unique ID
        date_part = datetime.utcnow().strftime("%Y%m%d")
        unique_part = str(uuid.uuid4())[:4].upper()
        return f"INV-{date_part}-{unique_part}"

    def create_invoice(self, contract_id, amount, currency="USD", is_recurring=False, 
                     frequency=None, template_type="standard", payment_method=None, 
                     payment_notes=None, start_date=None, end_date=None):
        """
        Create a new invoice for a contract
        Args:
            contract_id: ID of the contract
            amount: Invoice amount
            currency: Currency code (default: USD)
            is_recurring: Whether this is a recurring invoice
            frequency: Recurrence frequency (monthly, quarterly, etc.)
            template_type: Invoice template type
            payment_method: Payment method
            payment_notes: Additional payment notes
            start_date: Start date for recurring invoices
            end_date: End date for recurring invoices
        Returns:
            Invoice: The created invoice object
        """
        try:
            invoice_number = self.generate_invoice_number()
            issue_date = datetime.utcnow()
            
            # Set due date based on payment terms (default to 30 days)
            due_date = issue_date + timedelta(days=30)
            
            # Create the invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                contract_id=contract_id,
                amount=amount,
                currency=currency,
                issue_date=issue_date,
                due_date=due_date,
                is_recurring=is_recurring,
                frequency=frequency,
                template_type=template_type,
                status="draft",
                payment_method=payment_method,
                payment_notes=payment_notes
            )
            
            db.session.add(invoice)
            db.session.commit()
            
            logger.info(f"Created invoice {invoice_number} for contract {contract_id}")
            
            # If recurring, schedule future invoices
            if is_recurring and frequency and start_date and end_date:
                self.schedule_recurring_invoices(
                    contract_id=contract_id,
                    amount=amount,
                    currency=currency,
                    frequency=frequency,
                    template_type=template_type,
                    payment_method=payment_method,
                    payment_notes=payment_notes,
                    start_date=start_date,
                    end_date=end_date
                )
            
            return invoice
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating invoice: {str(e)}")
            raise

    def schedule_recurring_invoices(self, contract_id, amount, currency, frequency, 
                                 template_type, payment_method, payment_notes, 
                                 start_date, end_date):
        """
        Schedule recurring invoices for a contract
        Args:
            contract_id: ID of the contract
            amount: Invoice amount
            currency: Currency code
            frequency: Recurrence frequency (monthly, quarterly, etc.)
            template_type: Invoice template type
            payment_method: Payment method
            payment_notes: Additional payment notes
            start_date: Start date for recurring invoices
            end_date: End date for recurring invoices
        """
        try:
            logger.info(f"Scheduling recurring invoices for contract {contract_id}")
            
            # Parse dates
            start = datetime.strptime(start_date, "%Y-%m-%d") if isinstance(start_date, str) else start_date
            end = datetime.strptime(end_date, "%Y-%m-%d") if isinstance(end_date, str) else end_date
            
            # Define frequency increments
            increments = {
                "monthly": relativedelta(months=1),
                "quarterly": relativedelta(months=3),
                "biannually": relativedelta(months=6),
                "annually": relativedelta(years=1)
            }
            
            if frequency not in increments:
                raise ValueError(f"Unsupported frequency: {frequency}")
            
            increment = increments[frequency]
            current_date = start
            
            # Schedule invoices from start_date to end_date
            while current_date <= end:
                invoice_number = self.generate_invoice_number()
                due_date = current_date + timedelta(days=30)
                
                invoice = Invoice(
                    invoice_number=invoice_number,
                    contract_id=contract_id,
                    amount=amount,
                    currency=currency,
                    issue_date=current_date,
                    due_date=due_date,
                    is_recurring=True,
                    frequency=frequency,
                    template_type=template_type,
                    status="scheduled",
                    payment_method=payment_method,
                    payment_notes=payment_notes
                )
                
                db.session.add(invoice)
                current_date += increment
            
            db.session.commit()
            logger.info(f"Scheduled recurring invoices for contract {contract_id}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error scheduling recurring invoices: {str(e)}")
            raise

    def update_invoice_status(self, invoice_id, status):
        """
        Update the status of an invoice
        Args:
            invoice_id: ID of the invoice
            status: New status (draft, sent, paid, overdue)
        Returns:
            Invoice: The updated invoice object
        """
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice not found: {invoice_id}")
            
            invoice.status = status
            invoice.updated_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated invoice {invoice.invoice_number} status to {status}")
            
            return invoice
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating invoice status: {str(e)}")
            raise

    def delete_invoice(self, invoice_id):
        """
        Delete an invoice
        Args:
            invoice_id: ID of the invoice
        Returns:
            bool: True if deletion was successful
        """
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice not found: {invoice_id}")
            
            db.session.delete(invoice)
            db.session.commit()
            
            logger.info(f"Deleted invoice {invoice.invoice_number}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting invoice: {str(e)}")
            raise

    def check_overdue_invoices(self):
        """
        Check for overdue invoices and update their status
        Returns:
            list: List of invoices that were marked as overdue
        """
        try:
            today = datetime.utcnow().date()
            
            # Find invoices that are past due and not marked as overdue
            overdue_invoices = Invoice.query.filter(
                Invoice.due_date < today,
                Invoice.status.in_(["draft", "sent"])
            ).all()
            
            # Update status to overdue
            for invoice in overdue_invoices:
                invoice.status = "overdue"
                invoice.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Marked {len(overdue_invoices)} invoices as overdue")
            return overdue_invoices
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error checking overdue invoices: {str(e)}")
            raise
