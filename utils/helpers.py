import uuid
import re
from datetime import datetime
import os
import random
import string

def generate_contract_number():
    """
    Generate a unique contract number
    Returns:
        str: Unique contract number
    """
    # Format: CONT-YYYYMMDD-XXXX where XXXX is a unique ID
    date_part = datetime.utcnow().strftime("%Y%m%d")
    unique_part = str(uuid.uuid4())[:4].upper()
    return f"CONT-{date_part}-{unique_part}"

def parse_date(date_string):
    """
    Parse a date string into a datetime object
    Args:
        date_string: Date string in YYYY-MM-DD format
    Returns:
        datetime: Parsed datetime object or None if invalid
    """
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        return None

def slugify(text):
    """
    Convert text to a URL-friendly slug
    Args:
        text: Text to convert
    Returns:
        str: URL-friendly slug
    """
    # Remove non-alphanumeric characters
    text = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace spaces with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    return text.strip('-')

def get_file_extension(filename):
    """
    Get the file extension from a filename
    Args:
        filename: Name of the file
    Returns:
        str: File extension (without the dot)
    """
    return os.path.splitext(filename)[1][1:].lower()

def is_allowed_file(filename, allowed_extensions):
    """
    Check if the file has an allowed extension
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions
    Returns:
        bool: True if the file is allowed, False otherwise
    """
    extension = get_file_extension(filename)
    return extension in allowed_extensions

def generate_random_string(length=10):
    """
    Generate a random string of specified length
    Args:
        length: Length of the string
    Returns:
        str: Random string
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def calculate_date_difference(start_date, end_date):
    """
    Calculate the difference between two dates in days
    Args:
        start_date: Start date
        end_date: End date
    Returns:
        int: Difference in days
    """
    if not start_date or not end_date:
        return None
    
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    
    if not start_date or not end_date:
        return None
    
    return (end_date - start_date).days

def format_currency(amount, currency='USD'):
    """
    Format a currency amount
    Args:
        amount: Amount to format
        currency: Currency code
    Returns:
        str: Formatted currency amount
    """
    if not amount:
        return None
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return None
    
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'EUR':
        return f"€{amount:,.2f}"
    elif currency == 'GBP':
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def get_approval_level_for_contract(contract_value, thresholds):
    """
    Determine the approval level needed for a contract based on its value
    Args:
        contract_value: Value of the contract
        thresholds: Dictionary of approval thresholds
    Returns:
        str: Approval level
    """
    if not contract_value:
        return 'level1'  # Default lowest level
    
    try:
        value = float(contract_value)
    except (ValueError, TypeError):
        return 'level1'
    
    if value <= thresholds['level1']:
        return 'level1'
    elif value <= thresholds['level2']:
        return 'level2'
    elif value <= thresholds['level3']:
        return 'level3'
    else:
        return 'level4'

def format_date(date_obj, format_string='%Y-%m-%d'):
    """
    Format a date object as a string
    Args:
        date_obj: Date to format
        format_string: Format string
    Returns:
        str: Formatted date string
    """
    if not date_obj:
        return None
    
    return date_obj.strftime(format_string)

def validate_email(email):
    """
    Validate an email address
    Args:
        email: Email address to validate
    Returns:
        bool: True if valid, False otherwise
    """
    if not email:
        return False
    
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email))
