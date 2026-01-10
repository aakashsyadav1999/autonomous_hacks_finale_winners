"""
Admin Portal Models for Smart Civic Complaint Management System.

This module contains administrative models for managing contractors and wards.
These entities are assigned to tickets by administrative staff to track
resolution responsibility and work progress.
"""

from django.db import models
from django.core.validators import RegexValidator


class Ward(models.Model):
    """
    Represents an administrative ward within the city.
    
    Wards are geographic divisions used for complaint management.
    Each ward has a designated administrator responsible for
    overseeing civic issue resolution in that area.
    """
    
    # Numeric ward identifier
    ward_no = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Ward number (e.g., 1, 2A, 3B)"
    )
    
    # Ward name
    ward_name = models.CharField(
        max_length=100,
        help_text="Official ward name"
    )
    
    # Ward administrator contact details
    ward_admin_name = models.CharField(
        max_length=100,
        help_text="Name of ward administrator"
    )
    
    # Phone number with Indian format validation
    phone_regex = RegexValidator(
        regex=r'^\+?91?[6-9]\d{9}$',
        message="Phone number must be in format: '+919876543210' or '9876543210'"
    )
    
    ward_admin_no = models.CharField(
        validators=[phone_regex],
        max_length=15,
        help_text="Ward administrator contact number"
    )
    
    # Ward office address
    ward_address = models.TextField(
        help_text="Complete ward office address"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When ward was added to system"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        ordering = ['ward_no']
        verbose_name = 'Ward'
        verbose_name_plural = 'Wards'
    
    def __str__(self):
        return f"Ward {self.ward_no} - {self.ward_name}"


class Contractor(models.Model):
    """
    Represents a contractor responsible for resolving civic complaints.
    
    Contractors are assigned to tickets and perform the actual work
    to resolve civic issues. Citizens can rate their work quality
    upon ticket resolution.
    """
    
    # Contractor identification
    contractor_name = models.CharField(
        max_length=150,
        help_text="Full name or company name of contractor"
    )
    
    # Contact details
    phone_regex = RegexValidator(
        regex=r'^\+?91?[6-9]\d{9}$',
        message="Phone number must be in format: '+919876543210' or '9876543210'"
    )
    
    contractor_phone = models.CharField(
        validators=[phone_regex],
        max_length=15,
        help_text="Primary contact number"
    )
    
    contractor_email = models.EmailField(
        help_text="Email address for notifications"
    )
    
    # Work assignment details
    assigned_area = models.CharField(
        max_length=200,
        help_text="Geographic area where contractor operates (e.g., Satellite, Vastrapur)"
    )
    
    department = models.CharField(
        max_length=100,
        help_text="Department specialization (e.g., PWD, Sanitation, Drainage)"
    )
    
    # Performance metrics
    ratings = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average rating from citizens (0.00 to 5.00)"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When contractor was registered"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        ordering = ['-ratings', 'contractor_name']
        verbose_name = 'Contractor'
        verbose_name_plural = 'Contractors'
    
    def __str__(self):
        return f"{self.contractor_name} - {self.department} ({self.ratings:.2f}★)"
    
    def update_average_rating(self):
        """
        Recalculate average rating from all completed tickets.
        
        This method is called automatically when a user rates a ticket.
        It aggregates all user_rating values from resolved tickets
        assigned to this contractor.
        """
        from django.db.models import Avg
        from user_portal.models import Ticket
        
        # Calculate average rating from all tickets with user ratings
        avg_rating = Ticket.objects.filter(
            contractor=self,
            user_rating__isnull=False
        ).aggregate(
            avg=Avg('user_rating')
        )['avg']
        
        # Update contractor's rating (convert to 0.00 if no ratings exist)
        self.ratings = avg_rating if avg_rating is not None else 0.00
        self.save(update_fields=['ratings', 'updated_at'])

