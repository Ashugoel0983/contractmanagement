from datetime import datetime
import re
from models import ContractType, UserRole

def validate_contract_data(data):
    """
    Validate contract data
    Args:
        data: Dictionary containing contract data
    Returns:
        list: List of validation errors, empty if valid
    """
    errors = []
    
    # Validate required fields
    if 'title' not in data or not data['title']:
        errors.append("Contract title is required")
    
    if 'contract_type' in data:
        try:
            ContractType(data['contract_type'])
        except ValueError:
            valid_types = [t.value for t in ContractType]
            errors.append(f"Invalid contract type. Valid types: {', '.join(valid_types)}")
    
    # Validate dates
    if 'start_date' in data and data['start_date']:
        try:
            if isinstance(data['start_date'], str):
                datetime.strptime(data['start_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("Start date must be in YYYY-MM-DD format")
    
    if 'end_date' in data and data['end_date']:
        try:
            if isinstance(data['end_date'], str):
                datetime.strptime(data['end_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("End date must be in YYYY-MM-DD format")
    
    # Validate date range
    if 'start_date' in data and 'end_date' in data and data['start_date'] and data['end_date']:
        try:
            start_date = data['start_date']
            end_date = data['end_date']
            
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_date > end_date:
                errors.append("End date must be after start date")
        except (ValueError, TypeError):
            # Already covered by the individual date validations
            pass
    
    # Validate numeric fields
    if 'value' in data and data['value'] and not data['value'] == '':
        try:
            value = float(data['value'])
            if value < 0:
                errors.append("Contract value cannot be negative")
        except ValueError:
            errors.append("Contract value must be a number")
    
    # Validate tags
    if 'tags' in data and isinstance(data['tags'], list):
        for tag in data['tags']:
            if not isinstance(tag, str) or len(tag) > 50:
                errors.append("Tags must be strings with maximum length of 50 characters")
    
    return errors

def validate_invoice_data(data):
    """
    Validate invoice data
    Args:
        data: Dictionary containing invoice data
    Returns:
        list: List of validation errors, empty if valid
    """
    errors = []
    
    # Validate required fields
    if 'contract_id' not in data or not data['contract_id']:
        errors.append("Contract ID is required")
    
    if 'amount' not in data or not data['amount']:
        errors.append("Invoice amount is required")
    
    # Validate numeric fields
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append("Invoice amount must be greater than zero")
        except ValueError:
            errors.append("Invoice amount must be a number")
    
    # Validate dates for recurring invoices
    if data.get('is_recurring') == True or data.get('is_recurring') == 'true':
        if 'frequency' not in data or not data['frequency']:
            errors.append("Frequency is required for recurring invoices")
        elif data['frequency'] not in ['monthly', 'quarterly', 'biannually', 'annually']:
            errors.append("Invalid frequency. Valid values: monthly, quarterly, biannually, annually")
        
        if 'start_date' not in data or not data['start_date']:
            errors.append("Start date is required for recurring invoices")
        
        if 'end_date' not in data or not data['end_date']:
            errors.append("End date is required for recurring invoices")
    
    # Validate dates
    if 'start_date' in data and data['start_date']:
        try:
            if isinstance(data['start_date'], str):
                datetime.strptime(data['start_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("Start date must be in YYYY-MM-DD format")
    
    if 'end_date' in data and data['end_date']:
        try:
            if isinstance(data['end_date'], str):
                datetime.strptime(data['end_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("End date must be in YYYY-MM-DD format")
    
    # Validate date range
    if 'start_date' in data and 'end_date' in data and data['start_date'] and data['end_date']:
        try:
            start_date = data['start_date']
            end_date = data['end_date']
            
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_date > end_date:
                errors.append("End date must be after start date")
        except (ValueError, TypeError):
            # Already covered by the individual date validations
            pass
    
    return errors

def validate_user_data(data):
    """
    Validate user data
    Args:
        data: Dictionary containing user data
    Returns:
        list: List of validation errors, empty if valid
    """
    errors = []
    
    # Validate required fields
    if 'email' not in data or not data['email']:
        errors.append("Email is required")
    
    if 'name' not in data or not data['name']:
        errors.append("Name is required")
    
    # Validate email format
    if 'email' in data and data['email']:
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, data['email']):
            errors.append("Invalid email format")
    
    # Validate role
    if 'role' in data:
        try:
            UserRole(data['role'])
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            errors.append(f"Invalid role. Valid roles: {', '.join(valid_roles)}")
    
    return errors

def validate_contract_metadata(data):
    """
    Validate contract metadata
    Args:
        data: Dictionary containing contract metadata
    Returns:
        list: List of validation errors, empty if valid
    """
    errors = []
    
    # No strict validation rules for metadata,
    # but we can check for data types
    
    if 'invoice_required' in data and not isinstance(data['invoice_required'], bool):
        errors.append("invoice_required must be a boolean")
    
    # Clauses can be any text
    
    # Validate risk flags if provided
    if 'risk_flags' in data and not isinstance(data['risk_flags'], dict):
        errors.append("risk_flags must be a dictionary")
    
    return errors

def validate_approval_data(data):
    """
    Validate approval data
    Args:
        data: Dictionary containing approval data
    Returns:
        list: List of validation errors, empty if valid
    """
    errors = []
    
    # Validate required fields for rejection
    if data.get('status') == 'rejected' and ('comments' not in data or not data['comments']):
        errors.append("Comments are required when rejecting a contract")
    
    return errors
