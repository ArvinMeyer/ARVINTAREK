"""
Helper utilities for Email Extraction System
"""
import re
import csv
import time
import random
from functools import wraps
from typing import List, Set
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

def normalize_email(email: str) -> str:
    """
    Normalize email address
    
    Args:
        email: Raw email address
    
    Returns:
        Normalized email (lowercase, trimmed)
    """
    return email.strip().lower()

def extract_domain(email: str) -> str:
    """
    Extract domain from email address
    
    Args:
        email: Email address
    
    Returns:
        Domain part of email
    """
    try:
        return email.split('@')[1].lower()
    except IndexError:
        return ''

def extract_emails_from_text(text: str) -> Set[str]:
    """
    Extract email addresses from text using regex
    
    Args:
        text: Text to search for emails
    
    Returns:
        Set of unique email addresses
    """
    # RFC 5322 compliant email regex (simplified)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return {normalize_email(email) for email in emails}

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for each retry
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"{func.__name__} attempt {attempt} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
            
        return wrapper
    return decorator

def rate_limit(min_delay: float, max_delay: float):
    """
    Rate limiting decorator with random delay
    
    Args:
        min_delay: Minimum delay (seconds)
        max_delay: Maximum delay (seconds)
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            delay = random.uniform(min_delay, max_delay)
            time.sleep(delay)
            return result
        return wrapper
    return decorator

def export_to_csv(data: List[dict], filepath: str, fieldnames: List[str] = None):
    """
    Export data to CSV file
    
    Args:
        data: List of dictionaries to export
        filepath: Output CSV file path
        fieldnames: List of field names (keys) to include
    """
    if not data:
        logger.warning("No data to export")
        return
    
    # Use all keys from first item if fieldnames not provided
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported {len(data)} records to {filepath}")
    except Exception as e:
        logger.error(f"Failed to export to CSV: {e}")
        raise

def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime object to string
    
    Args:
        dt: Datetime object
        format_str: Format string
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return 'N/A'
    return dt.strftime(format_str)

def calculate_percentage(part: int, total: int) -> float:
    """
    Calculate percentage
    
    Args:
        part: Part value
        total: Total value
    
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'

def is_valid_url(url: str) -> bool:
    """
    Basic URL validation
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL appears valid
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None
