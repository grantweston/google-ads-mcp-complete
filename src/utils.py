"""Utility functions for Google Ads MCP server."""

from typing import Union, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
import re


def micros_to_currency(micros: int) -> float:
    """Convert micros to currency amount.
    
    Args:
        micros: Amount in micros (1,000,000 micros = 1 currency unit)
        
    Returns:
        Currency amount as float
    """
    return micros / 1_000_000


def currency_to_micros(amount: Union[float, Decimal, str]) -> int:
    """Convert currency amount to micros.
    
    Args:
        amount: Currency amount
        
    Returns:
        Amount in micros
    """
    if isinstance(amount, str):
        # Remove currency symbols and commas
        amount = re.sub(r'[^\d.-]', '', amount)
        amount = float(amount)
    return int(amount * 1_000_000)


def format_currency(amount: Union[float, int], currency_code: str = "USD") -> str:
    """Format currency amount with symbol.
    
    Args:
        amount: Currency amount
        currency_code: ISO 4217 currency code
        
    Returns:
        Formatted currency string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "AUD": "A$",
        "CAD": "C$",
        "CHF": "CHF",
        "CNY": "¥",
        "INR": "₹",
    }
    
    symbol = currency_symbols.get(currency_code, currency_code + " ")
    
    # Format with appropriate decimal places
    if currency_code == "JPY":
        return f"{symbol}{amount:,.0f}"
    else:
        return f"{symbol}{amount:,.2f}"


def parse_date(date_str: str) -> date:
    """Parse date string in various formats.
    
    Args:
        date_str: Date string in format YYYY-MM-DD, YYYYMMDD, or MM/DD/YYYY
        
    Returns:
        date object
    """
    # Remove any whitespace
    date_str = date_str.strip()
    
    # Try different formats
    formats = [
        "%Y-%m-%d",  # 2024-01-15
        "%Y%m%d",    # 20240115
        "%m/%d/%Y",  # 01/15/2024
        "%d/%m/%Y",  # 15/01/2024
        "%Y/%m/%d",  # 2024/01/15
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    raise ValueError(f"Unable to parse date: {date_str}")


def format_date_range(start_date: Union[str, date], end_date: Union[str, date]) -> str:
    """Format a date range for display.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Formatted date range string
    """
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
        
    return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"


def get_date_range_dates(date_range: str) -> Tuple[date, date]:
    """Convert a date range string to start and end dates.
    
    Args:
        date_range: Date range like "LAST_30_DAYS", "THIS_MONTH", etc.
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()
    
    if date_range == "TODAY":
        return today, today
    elif date_range == "YESTERDAY":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif date_range == "LAST_7_DAYS":
        return today - timedelta(days=6), today
    elif date_range == "LAST_14_DAYS":
        return today - timedelta(days=13), today
    elif date_range == "LAST_30_DAYS":
        return today - timedelta(days=29), today
    elif date_range == "LAST_90_DAYS":
        return today - timedelta(days=89), today
    elif date_range == "THIS_MONTH":
        start = today.replace(day=1)
        return start, today
    elif date_range == "LAST_MONTH":
        # First day of last month
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
            end = date(today.year - 1, 12, 31)
        else:
            start = date(today.year, today.month - 1, 1)
            # Last day of last month
            if today.month == 1:
                end = date(today.year - 1, 12, 31)
            else:
                next_month_first = date(today.year, today.month, 1)
                end = next_month_first - timedelta(days=1)
        return start, end
    elif date_range == "THIS_YEAR":
        return date(today.year, 1, 1), today
    elif date_range == "LAST_YEAR":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    elif date_range == "ALL_TIME":
        # Return a very old date to today
        return date(2000, 1, 1), today
    else:
        # Try to parse custom range like "2024-01-01,2024-12-31"
        if "," in date_range:
            start_str, end_str = date_range.split(",", 1)
            return parse_date(start_str.strip()), parse_date(end_str.strip())
        else:
            raise ValueError(f"Unknown date range: {date_range}")


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a decimal value as percentage.
    
    Args:
        value: Decimal value (0.15 = 15%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def sanitize_customer_id(customer_id: str) -> str:
    """Sanitize customer ID by removing hyphens.
    
    Args:
        customer_id: Customer ID with or without hyphens
        
    Returns:
        Customer ID without hyphens
    """
    return customer_id.replace("-", "")


def format_customer_id(customer_id: Union[str, int]) -> str:
    """Format customer ID with hyphens for display.
    
    Args:
        customer_id: Customer ID without hyphens
        
    Returns:
        Customer ID formatted as XXX-XXX-XXXX
    """
    customer_id = str(customer_id)
    if len(customer_id) == 10 and "-" not in customer_id:
        return f"{customer_id[:3]}-{customer_id[3:6]}-{customer_id[6:]}"
    return customer_id


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def parse_keyword_match_type(match_type_str: str) -> str:
    """Parse and validate keyword match type.
    
    Args:
        match_type_str: Match type string
        
    Returns:
        Normalized match type
    """
    match_type_map = {
        "broad": "BROAD",
        "phrase": "PHRASE",
        "exact": "EXACT",
        "broad match modifier": "BROAD_MATCH_MODIFIER",
        "bmm": "BROAD_MATCH_MODIFIER",
    }
    
    normalized = match_type_str.lower().strip()
    return match_type_map.get(normalized, "BROAD")


def format_resource_name(resource_type: str, customer_id: str, resource_id: str) -> str:
    """Format a Google Ads resource name.
    
    Args:
        resource_type: Type of resource (campaigns, adGroups, etc.)
        customer_id: Customer ID
        resource_id: Resource ID
        
    Returns:
        Formatted resource name
    """
    customer_id = sanitize_customer_id(customer_id)
    return f"customers/{customer_id}/{resource_type}/{resource_id}"


def parse_resource_name(resource_name: str) -> dict:
    """Parse a Google Ads resource name into components.
    
    Args:
        resource_name: Resource name like "customers/1234567890/campaigns/123"
        
    Returns:
        Dict with customer_id, resource_type, and resource_id
    """
    parts = resource_name.split("/")
    if len(parts) >= 4 and parts[0] == "customers":
        return {
            "customer_id": parts[1],
            "resource_type": parts[2],
            "resource_id": parts[3],
        }
    return {}


def batch_list(items: list, batch_size: int = 1000) -> list:
    """Split a list into batches.
    
    Args:
        items: List to batch
        batch_size: Maximum size of each batch
        
    Returns:
        List of batches
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches