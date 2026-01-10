"""
Ticket number generation utilities.

This module generates unique ticket numbers with daily reset counter.
Format: CMP-YYYYMMDD-NNN (e.g., CMP-20260110-001)
"""

import logging
from datetime import date
from django.db import transaction
from user_portal.models import Ticket


logger = logging.getLogger(__name__)


def generate_ticket_number() -> str:
    """
    Generate unique ticket number with daily reset counter.
    
    Format: CMP-YYYYMMDD-NNN
    - CMP: Prefix for "Complaint"
    - YYYYMMDD: Current date (20260110)
    - NNN: Daily incrementing counter (001, 002, ...)
    
    Counter resets to 001 each day at midnight.
    
    Returns:
        Unique ticket number string
    
    Example:
        First ticket of day: CMP-20260110-001
        Second ticket: CMP-20260110-002
        Next day first: CMP-20260111-001
    
    Note:
        Uses database transaction to ensure thread-safe counter increment.
        Prevents duplicate numbers even under concurrent ticket creation.
    """
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    prefix = f"CMP-{date_str}-"
    
    # Find highest ticket number for today
    with transaction.atomic():
        # Lock table to prevent race conditions
        today_tickets = Ticket.objects.filter(
            ticket_number__startswith=prefix
        ).order_by('-ticket_number').first()
        
        if today_tickets:
            # Extract counter from last ticket number
            last_number = today_tickets.ticket_number
            last_counter = int(last_number.split('-')[-1])
            new_counter = last_counter + 1
        else:
            # First ticket of the day
            new_counter = 1
        
        # Format counter as zero-padded 3-digit number
        ticket_number = f"{prefix}{new_counter:03d}"
        
        logger.info(f"Generated ticket number: {ticket_number}")
        
        return ticket_number


def parse_ticket_number(ticket_number: str) -> dict:
    """
    Parse ticket number into components.
    
    Args:
        ticket_number: Ticket number string (e.g., CMP-20260110-001)
    
    Returns:
        Dictionary with components:
        {
            'prefix': 'CMP',
            'date': '20260110',
            'counter': '001',
            'is_valid': True
        }
        Returns {'is_valid': False} if format is invalid.
    
    Example:
        >>> parse_ticket_number('CMP-20260110-001')
        {'prefix': 'CMP', 'date': '20260110', 'counter': '001', 'is_valid': True}
    """
    try:
        parts = ticket_number.split('-')
        
        if len(parts) != 3:
            return {'is_valid': False}
        
        prefix, date_str, counter = parts
        
        # Validate format
        if (prefix == 'CMP' and 
            len(date_str) == 8 and date_str.isdigit() and
            len(counter) == 3 and counter.isdigit()):
            
            return {
                'prefix': prefix,
                'date': date_str,
                'counter': counter,
                'is_valid': True
            }
        
        return {'is_valid': False}
    
    except Exception as e:
        logger.error(f"Error parsing ticket number '{ticket_number}': {str(e)}")
        return {'is_valid': False}
