"""
Invoice Service for Contract Management System
Handles generating and managing contract invoices
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from services.storage_service import StorageService

logger = logging.getLogger(__name__)

class InvoiceService:
    def __init__(self):
        """Initialize invoice service"""
        self.storage = StorageService()
        logger.info("Invoice service initialized")
    
    def generate_invoice_pdf(self, invoice_data, template_type="standard"):
        """
        Generate a PDF invoice based on invoice data
        Args:
            invoice_data: Dict containing invoice information
            template_type: Type of template to use (standard, detailed, minimal)
        Returns:
            str: Path to the generated PDF file
        """
        try:
            logger.debug(f"Generating {template_type} invoice PDF")
            
            # Create a unique filename
            filename = f"invoice_{invoice_data.get('invoice_number', str(uuid.uuid4()))}.pdf"
            temp_path = os.path.join(os.environ.get("UPLOAD_FOLDER", "uploads"), filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Generate PDF based on template type
            if template_type == "detailed":
                self._generate_detailed_invoice(invoice_data, temp_path)
            elif template_type == "minimal":
                self._generate_minimal_invoice(invoice_data, temp_path)
            else:
                # Default to standard
                self._generate_standard_invoice(invoice_data, temp_path)
            
            logger.info(f"Invoice PDF generated: {temp_path}")
            return temp_path
        
        except Exception as e:
            logger.error(f"Error generating invoice PDF: {str(e)}")
            raise
    
    def calculate_payment_schedule(self, contract_data, invoice_config):
        """
        Calculate payment schedule based on contract and invoice configuration
        Args:
            contract_data: Contract information
            invoice_config: Invoice configuration with frequency
        Returns:
            list: List of invoice dates and amounts
        """
        try:
            logger.debug("Calculating payment schedule")
            
            payment_schedule = []
            start_date = contract_data.get('start_date')
            end_date = contract_data.get('end_date')
            total_value = contract_data.get('value', 0)
            frequency = invoice_config.get('frequency', 'monthly')
            
            if not start_date or not end_date:
                logger.warning("Missing start_date or end_date for payment schedule")
                return []
            
            # Convert dates if they are strings
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Calculate duration
            duration = (end_date - start_date).days
            
            # Calculate payment amounts based on frequency
            if frequency == 'monthly':
                num_payments = (duration // 30) + 1  # Approximate number of months
                payment_amount = total_value / num_payments if num_payments > 0 else total_value
                
                for i in range(num_payments):
                    payment_date = start_date + timedelta(days=i * 30)  # Approximate month
                    if payment_date <= end_date:
                        payment_schedule.append({
                            'date': payment_date,
                            'amount': payment_amount,
                            'description': f"Payment {i+1} of {num_payments}"
                        })
            
            elif frequency == 'quarterly':
                num_payments = (duration // 90) + 1  # Approximate number of quarters
                payment_amount = total_value / num_payments if num_payments > 0 else total_value
                
                for i in range(num_payments):
                    payment_date = start_date + timedelta(days=i * 90)  # Approximate quarter
                    if payment_date <= end_date:
                        payment_schedule.append({
                            'date': payment_date,
                            'amount': payment_amount,
                            'description': f"Payment {i+1} of {num_payments}"
                        })
            
            elif frequency == 'annual':
                num_payments = (duration // 365) + 1  # Approximate number of years
                payment_amount = total_value / num_payments if num_payments > 0 else total_value
                
                for i in range(num_payments):
                    payment_date = start_date + timedelta(days=i * 365)  # Approximate year
                    if payment_date <= end_date:
                        payment_schedule.append({
                            'date': payment_date,
                            'amount': payment_amount,
                            'description': f"Payment {i+1} of {num_payments}"
                        })
            
            elif frequency == 'upfront':
                payment_schedule.append({
                    'date': start_date,
                    'amount': total_value,
                    'description': "Full upfront payment"
                })
            
            elif frequency == 'milestone':
                # For milestone-based, we just estimate equal milestones
                milestones = invoice_config.get('milestones', 3)
                payment_amount = total_value / milestones
                
                for i in range(milestones):
                    milestone_date = start_date + timedelta(days=(duration * (i / milestones)))
                    payment_schedule.append({
                        'date': milestone_date,
                        'amount': payment_amount,
                        'description': f"Milestone {i+1}: {invoice_config.get('milestone_descriptions', [])[i] if i < len(invoice_config.get('milestone_descriptions', [])) else 'Payment'}"
                    })
            
            logger.info(f"Generated payment schedule with {len(payment_schedule)} payments")
            return payment_schedule
        
        except Exception as e:
            logger.error(f"Error calculating payment schedule: {str(e)}")
            return []
    
    def _generate_standard_invoice(self, invoice_data, output_path):
        """Generate a standard invoice template"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create content elements
        elements = []
        
        # Company header
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=0.2 * inch
        )
        company_name = invoice_data.get('company_name', 'Your Company Name')
        elements.append(Paragraph(company_name, header_style))
        
        # Invoice title
        title_text = f"INVOICE #{invoice_data.get('invoice_number', '')}"
        elements.append(Paragraph(title_text, styles['Heading1']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Date and client info
        date_issued = invoice_data.get('issue_date', datetime.now().strftime('%Y-%m-%d'))
        due_date = invoice_data.get('due_date', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        
        info_data = [
            ["Date:", date_issued],
            ["Due Date:", due_date],
            ["Invoice #:", invoice_data.get('invoice_number', '')],
            ["Contract #:", invoice_data.get('contract_number', '')],
            ["", ""],
            ["Bill To:", invoice_data.get('client_name', 'Client Name')],
            ["", invoice_data.get('client_address', 'Client Address')],
        ]
        
        info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # Line items
        item_data = [["Description", "Quantity", "Unit Price", "Amount"]]
        
        line_items = invoice_data.get('line_items', [])
        if not line_items:
            # Create a default line item if none provided
            line_items = [{
                'description': invoice_data.get('description', 'Professional Services'),
                'quantity': 1,
                'unit_price': invoice_data.get('amount', 0),
                'amount': invoice_data.get('amount', 0)
            }]
        
        for item in line_items:
            item_data.append([
                item.get('description', ''),
                str(item.get('quantity', 1)),
                f"{item.get('unit_price', 0):.2f}",
                f"{item.get('amount', 0):.2f}"
            ])
        
        # Add subtotal, tax, total
        subtotal = sum(item.get('amount', 0) for item in line_items)
        tax_rate = invoice_data.get('tax_rate', 0)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Add empty row
        item_data.append(["", "", "", ""])
        # Add subtotal
        item_data.append(["", "", "Subtotal:", f"{subtotal:.2f}"])
        # Add tax if applicable
        if tax_rate > 0:
            item_data.append(["", "", f"Tax ({tax_rate*100:.2f}%):", f"{tax_amount:.2f}"])
        # Add total
        item_data.append(["", "", "Total:", f"{total:.2f}"])
        
        line_item_table = Table(item_data, colWidths=[3.5 * inch, 1 * inch, 1.25 * inch, 1.25 * inch])
        line_item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -2), 0.25, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(line_item_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # Payment information
        payment_info = invoice_data.get('payment_info', '')
        payment_terms = invoice_data.get('payment_terms', 'Net 30')
        
        elements.append(Paragraph("<b>Payment Terms:</b> " + payment_terms, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("<b>Payment Information:</b>", styles['Normal']))
        elements.append(Paragraph(payment_info, styles['Normal']))
        
        # Build the PDF
        doc.build(elements)
        
        # Save the PDF to the specified path
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
    
    def _generate_detailed_invoice(self, invoice_data, output_path):
        """Generate a detailed invoice template with more information"""
        # Similar to standard but with more sections like contract details
        # Implementation similar to _generate_standard_invoice
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create content elements (more detailed than standard)
        elements = []
        
        # Company header with logo placeholder
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=0.2 * inch
        )
        company_name = invoice_data.get('company_name', 'Your Company Name')
        elements.append(Paragraph(company_name, header_style))
        
        # Company details
        company_details = invoice_data.get('company_address', 'Company Address') + "<br/>"
        company_details += invoice_data.get('company_phone', 'Phone') + " | "
        company_details += invoice_data.get('company_email', 'Email')
        elements.append(Paragraph(company_details, styles['Normal']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Invoice title
        title_text = f"INVOICE #{invoice_data.get('invoice_number', '')}"
        elements.append(Paragraph(title_text, styles['Heading1']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # More detailed date and client info
        date_issued = invoice_data.get('issue_date', datetime.now().strftime('%Y-%m-%d'))
        due_date = invoice_data.get('due_date', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        
        info_data = [
            ["Date:", date_issued],
            ["Due Date:", due_date],
            ["Invoice #:", invoice_data.get('invoice_number', '')],
            ["Contract #:", invoice_data.get('contract_number', '')],
            ["PO #:", invoice_data.get('purchase_order', '')],
            ["Contract Date:", invoice_data.get('contract_date', '')],
            ["", ""],
            ["Bill To:", invoice_data.get('client_name', 'Client Name')],
            ["", invoice_data.get('client_address', 'Client Address')],
            ["", invoice_data.get('client_email', '')],
            ["", invoice_data.get('client_phone', '')],
        ]
        
        info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # Contract summary
        elements.append(Paragraph("Contract Summary", styles['Heading2']))
        contract_summary = invoice_data.get('contract_summary', '')
        elements.append(Paragraph(contract_summary, styles['Normal']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Line items (same as standard)
        elements.append(Paragraph("Invoice Details", styles['Heading2']))
        item_data = [["Description", "Quantity", "Unit Price", "Amount"]]
        
        line_items = invoice_data.get('line_items', [])
        if not line_items:
            # Create a default line item if none provided
            line_items = [{
                'description': invoice_data.get('description', 'Professional Services'),
                'quantity': 1,
                'unit_price': invoice_data.get('amount', 0),
                'amount': invoice_data.get('amount', 0)
            }]
        
        for item in line_items:
            item_data.append([
                item.get('description', ''),
                str(item.get('quantity', 1)),
                f"{item.get('unit_price', 0):.2f}",
                f"{item.get('amount', 0):.2f}"
            ])
        
        # Add subtotal, tax, total
        subtotal = sum(item.get('amount', 0) for item in line_items)
        tax_rate = invoice_data.get('tax_rate', 0)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Add empty row
        item_data.append(["", "", "", ""])
        # Add subtotal
        item_data.append(["", "", "Subtotal:", f"{subtotal:.2f}"])
        # Add tax if applicable
        if tax_rate > 0:
            item_data.append(["", "", f"Tax ({tax_rate*100:.2f}%):", f"{tax_amount:.2f}"])
        # Add total
        item_data.append(["", "", "Total:", f"{total:.2f}"])
        
        line_item_table = Table(item_data, colWidths=[3.5 * inch, 1 * inch, 1.25 * inch, 1.25 * inch])
        line_item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -2), 0.25, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(line_item_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # Payment schedule
        if invoice_data.get('payment_schedule'):
            elements.append(Paragraph("Payment Schedule", styles['Heading2']))
            schedule_data = [["Date", "Amount", "Description"]]
            
            for payment in invoice_data.get('payment_schedule', []):
                payment_date = payment.get('date')
                if isinstance(payment_date, datetime):
                    payment_date = payment_date.strftime('%Y-%m-%d')
                
                schedule_data.append([
                    payment_date,
                    f"{payment.get('amount', 0):.2f}",
                    payment.get('description', '')
                ])
            
            schedule_table = Table(schedule_data, colWidths=[2 * inch, 2 * inch, 3 * inch])
            schedule_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ]))
            elements.append(schedule_table)
            elements.append(Spacer(1, 0.25 * inch))
        
        # Payment information
        payment_info = invoice_data.get('payment_info', '')
        payment_terms = invoice_data.get('payment_terms', 'Net 30')
        
        elements.append(Paragraph("<b>Payment Terms:</b> " + payment_terms, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("<b>Payment Information:</b>", styles['Normal']))
        elements.append(Paragraph(payment_info, styles['Normal']))
        
        # Notes
        if invoice_data.get('notes'):
            elements.append(Spacer(1, 0.25 * inch))
            elements.append(Paragraph("Notes", styles['Heading2']))
            elements.append(Paragraph(invoice_data.get('notes', ''), styles['Normal']))
        
        # Build the PDF
        doc.build(elements)
        
        # Save the PDF to the specified path
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
    
    def _generate_minimal_invoice(self, invoice_data, output_path):
        """Generate a minimal invoice template with just essential information"""
        # Simplified version with minimum required information
        # Implementation similar to _generate_standard_invoice
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add invoice title
        c.setFont('Helvetica-Bold', 16)
        c.drawString(50, height - 50, "INVOICE")
        
        # Add invoice number
        c.setFont('Helvetica', 12)
        c.drawString(50, height - 80, f"Invoice #: {invoice_data.get('invoice_number', '')}")
        
        # Add date issued and date due
        date_issued = invoice_data.get('issue_date', datetime.now().strftime('%Y-%m-%d'))
        due_date = invoice_data.get('due_date', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        
        c.drawString(50, height - 100, f"Date: {date_issued}")
        c.drawString(50, height - 120, f"Due Date: {due_date}")
        
        # Add client name
        c.drawString(50, height - 150, f"Bill To: {invoice_data.get('client_name', 'Client')}")
        
        # Add line
        c.line(50, height - 170, width - 50, height - 170)
        
        # Add description and amount
        c.drawString(50, height - 200, "Description")
        c.drawString(width - 150, height - 200, "Amount")
        
        # Add invoice item
        description = invoice_data.get('description', 'Professional Services')
        amount = invoice_data.get('amount', 0)
        c.drawString(50, height - 230, description)
        c.drawString(width - 150, height - 230, f"{amount:.2f}")
        
        # Add line
        c.line(50, height - 250, width - 50, height - 250)
        
        # Add total
        c.setFont('Helvetica-Bold', 12)
        c.drawString(width - 200, height - 280, "Total:")
        c.drawString(width - 150, height - 280, f"{amount:.2f}")
        
        # Add payment terms
        c.setFont('Helvetica', 10)
        c.drawString(50, height - 310, f"Payment Terms: {invoice_data.get('payment_terms', 'Net 30')}")
        
        # Save the PDF
        c.save()
        
        # Save the PDF to the specified path
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())