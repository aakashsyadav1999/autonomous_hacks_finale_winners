"""
Admin Portal Models for Smart Civic Complaint Management System.

This module contains administrative models for managing contractors and wards.
These entities are assigned to tickets by administrative staff to track
resolution responsibility and work progress.
"""

import os
import uuid
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.utils import timezone


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
    
    Each contractor has a User account (regular user, not staff/superuser)
    and can work across multiple wards (ManyToMany relationship).
    """
    
    # Link to Django User model (regular user, not staff)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,  # Temporarily nullable for migration
        blank=True,
        related_name='contractor_profile',
        help_text="Django user account for contractor login"
    )
    
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
    
    # Work assignment - Many-to-Many relationship with wards
    wards = models.ManyToManyField(
        Ward,
        related_name='contractors',
        help_text="Wards where contractor can work (one contractor can work in multiple wards)"
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


def contractor_completion_image_path(instance, filename):
    """
    Generate upload path for contractor completion images.
    
    Path structure: contractor_work/YYYY/MM/DD/ticket_id/after_uuid.ext
    Organized by date and ticket for easy retrieval.
    
    Args:
        instance: TicketCompletion model instance
        filename: Original filename
    
    Returns:
        String path for file storage
    """
    date = timezone.now()
    ext = os.path.splitext(filename)[1]
    new_filename = f"after_{uuid.uuid4()}{ext}"
    
    return os.path.join(
        'contractor_work',
        str(date.year),
        str(date.month).zfill(2),
        str(date.day).zfill(2),
        str(instance.ticket.id),
        new_filename
    )


class TicketCompletion(models.Model):
    """
    Represents a contractor's work completion submission with photo evidence.
    
    When a contractor finishes work, they upload an after-photo with their
    current GPS location. This data is sent to AI for verification.
    The AI checks if the issue is resolved by comparing before/after images.
    
    Workflow:
        1. Contractor uploads after-photo with GPS coordinates
        2. System validates contractor is within 50m of original location
        3. System sends before/after images to AI verification API
        4. AI returns is_completed (True/False) and optional error message
        5. If completed=True, admin is notified and can mark ticket resolved
    """
    
    # Link to ticket being completed
    ticket = models.OneToOneField(
        'user_portal.Ticket',
        on_delete=models.CASCADE,
        related_name='completion',
        help_text="Ticket this completion is for"
    )
    
    # Link to contractor who performed the work
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        related_name='completions',
        help_text="Contractor who submitted completion"
    )
    
    # After-work photo evidence
    after_image = models.ImageField(
        upload_to=contractor_completion_image_path,
        help_text="Photo of resolved issue taken by contractor"
    )
    
    # Contractor's location at time of photo upload
    contractor_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Contractor's GPS latitude when uploading photo"
    )
    
    contractor_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Contractor's GPS longitude when uploading photo"
    )
    
    # Distance from original complaint location (in meters)
    distance_from_original = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text="Distance in meters from original complaint location"
    )
    
    # AI verification results
    ai_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if AI confirms work is completed successfully"
    )
    
    ai_verification_message = models.TextField(
        null=True,
        blank=True,
        help_text="AI response message (error details if verification failed)"
    )
    
    # Submission timestamp
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When contractor submitted completion photo"
    )
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Ticket Completion'
        verbose_name_plural = 'Ticket Completions'
    
    def __str__(self):
        status = "✓ Verified" if self.ai_verified else "✗ Not Verified"
        return f"{self.ticket.ticket_number} - {status}"
    
    def delete(self, *args, **kwargs):
        """
        Override delete to remove after-image file from storage.
        """
        if self.after_image:
            if os.path.isfile(self.after_image.path):
                os.remove(self.after_image.path)
        
        super().delete(*args, **kwargs)


class Notification(models.Model):
    """
    Represents a notification for admin users.
    
    Notifications are created when significant events occur,
    such as AI verification completion. Admins can view, mark as read,
    or delete notifications from the admin portal.
    
    Types of notifications:
        - AI_VERIFICATION: AI has verified a ticket completion
        - TICKET_ASSIGNED: New ticket assigned to contractor
        - TICKET_COMPLETED: Contractor submitted completion photo
    """
    
    NOTIFICATION_TYPE_CHOICES = [
        ('AI_VERIFICATION', 'AI Verification Complete'),
        ('TICKET_ASSIGNED', 'Ticket Assigned'),
        ('TICKET_COMPLETED', 'Work Completed'),
    ]
    
    # Link to related ticket
    ticket = models.ForeignKey(
        'user_portal.Ticket',
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="Ticket this notification is about"
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True,
        help_text="Type of notification"
    )
    
    message = models.TextField(
        help_text="Notification message to display to admin"
    )
    
    # Read/unread status
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if admin has viewed this notification"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When notification was created"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_read', 'created_at']),
            models.Index(fields=['notification_type', 'is_read']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        read_status = "Read" if self.is_read else "Unread"
        return f"{self.ticket.ticket_number} - {self.notification_type} ({read_status})"

