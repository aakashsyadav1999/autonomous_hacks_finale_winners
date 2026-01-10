"""
User Portal Models for Smart Civic Complaint Management System.

This module contains models for citizen-facing complaint submission and tracking.
Includes CivicComplaint (photo submissions) and Ticket (generated complaints).
"""

import os
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_image_size(image):
    """
    Validate that uploaded image does not exceed 5MB.
    
    Args:
        image: ImageField instance to validate
    
    Raises:
        ValidationError: If image size exceeds 5MB
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert to bytes
    
    if image.size > max_size_bytes:
        raise ValidationError(
            f'Image file size cannot exceed {max_size_mb}MB. '
            f'Current size: {image.size / (1024 * 1024):.2f}MB'
        )


def civic_complaint_image_path(instance, filename):
    """
    Generate upload path for civic complaint images.
    
    Path structure: complaints/YYYY/MM/DD/session_id/filename
    This organization helps with cleanup and archival.
    
    Args:
        instance: CivicComplaint model instance
        filename: Original filename
    
    Returns:
        String path for file storage
    """
    date = timezone.now()
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    
    return os.path.join(
        'complaints',
        str(date.year),
        str(date.month).zfill(2),
        str(date.day).zfill(2),
        str(instance.session_id),
        new_filename
    )


class CivicComplaint(models.Model):
    """
    Represents a citizen's photo submission with location data.
    
    This model stores the initial photo capture before AI validation.
    Photos are saved immediately when captured but marked as unsubmitted
    until the user explicitly submits. Unsubmitted complaints are
    automatically cleaned up at 11:55 PM daily.
    
    Workflow:
        1. User captures photo → CivicComplaint created (is_submit=False)
        2. User submits → is_submit=True, sent to AI for validation
        3. AI validates → is_valid set, tickets created if valid
        4. If invalid → CivicComplaint deleted
    """
    
    # Unique identifier for browser session tracking
    session_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Browser session identifier for tracking unsaved submissions"
    )
    
    # Photo evidence of civic issue
    image = models.ImageField(
        upload_to=civic_complaint_image_path,
        validators=[validate_image_size],
        help_text="Photo of civic complaint (max 5MB)"
    )
    
    # Location details (extracted from coordinates via reverse geocoding)
    street = models.CharField(
        max_length=255,
        blank=True,
        help_text="Street address where complaint photo was taken"
    )
    
    area = models.CharField(
        max_length=255,
        help_text="Area/locality name (e.g., Satellite, Vastrapur)"
    )
    
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="PIN code of the location"
    )
    
    # Geographic coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Latitude coordinate (GPS)"
    )
    
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Longitude coordinate (GPS)"
    )
    
    # Submission status flags
    is_submit = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if user has submitted complaint, False if only captured"
    )
    
    is_valid = models.BooleanField(
        null=True,
        blank=True,
        help_text="AI validation result: True=valid complaint, False=invalid, None=not yet validated"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When photo was captured"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_submit', 'created_at']),
            models.Index(fields=['session_id', 'is_submit']),
        ]
        verbose_name = 'Civic Complaint'
        verbose_name_plural = 'Civic Complaints'
    
    def __str__(self):
        status = "Submitted" if self.is_submit else "Draft"
        return f"{status} - {self.area} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def delete(self, *args, **kwargs):
        """
        Override delete to remove image file from storage.
        """
        if self.image:
            # Delete the physical file
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        
        super().delete(*args, **kwargs)


class Ticket(models.Model):
    """
    Represents a trackable civic complaint ticket.
    
    Multiple tickets can be generated from a single CivicComplaint
    if AI detects multiple issues requiring different department actions.
    Citizens track resolution progress via ticket number.
    
    Status Flow:
        Submitted → Assigned (contractor assigned) → In Progress (work started) → Resolved
    """
    
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]
    
    # Standardized department choices (matching category → department mapping)
    DEPARTMENT_CHOICES = [
        ('Sanitation Department', 'Sanitation Department'),
        ('Roads & Infrastructure', 'Roads & Infrastructure'),
        ('Water Supply Department', 'Water Supply Department'),
        ('Drainage Department', 'Drainage Department'),
    ]
    
    # Unique ticket identifier (format: CMP-YYYYMMDD-NNN)
    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique ticket number for tracking (CMP-20260110-001)"
    )
    
    # Link to parent complaint
    civic_complaint = models.ForeignKey(
        CivicComplaint,
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text="Parent complaint that generated this ticket"
    )
    
    # AI-classified issue details (free text from AI response)
    severity = models.CharField(
        max_length=50,
        help_text="Issue severity level (e.g., Low, Medium, High, Critical)"
    )
    
    category = models.CharField(
        max_length=100,
        help_text="Issue category (e.g., Roads, Sanitation, Drainage)"
    )
    
    department = models.CharField(
        max_length=100,
        choices=DEPARTMENT_CHOICES,
        db_index=True,
        help_text="Responsible department (standardized from AI classification)"
    )
    
    # Current ticket status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SUBMITTED',
        db_index=True,
        help_text="Current processing status"
    )
    
    # Assignment details (populated by admin)
    contractor = models.ForeignKey(
        'admin_portal.Contractor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text="Assigned contractor (visible when status=ASSIGNED)"
    )
    
    ward = models.ForeignKey(
        'admin_portal.Ward',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text="Assigned ward (visible when status=IN_PROGRESS)"
    )
    
    # User feedback (available when status=RESOLVED)
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Citizen rating of work quality (1-5 stars)"
    )
    
    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When ticket was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last status update timestamp"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['department', 'status']),
        ]
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
    
    def __str__(self):
        return f"{self.ticket_number} - {self.category} ({self.status})"
    
    def save(self, *args, **kwargs):
        """
        Override save to update contractor ratings when user submits rating.
        """
        # Check if rating was just added
        if self.user_rating and self.contractor:
            is_new_rating = False
            
            if self.pk:  # Existing ticket
                old_instance = Ticket.objects.get(pk=self.pk)
                is_new_rating = old_instance.user_rating is None and self.user_rating is not None
            
            super().save(*args, **kwargs)
            
            # Recalculate contractor average rating
            if is_new_rating:
                self.contractor.update_average_rating()
        else:
            super().save(*args, **kwargs)


class TicketNote(models.Model):
    """
    Represents notes/comments added to tickets by admin staff.
    
    Provides an audit trail of actions taken on each ticket,
    including status changes, assignments, and general observations.
    Useful for tracking work progress and communication history.
    """
    
    NOTE_TYPE_CHOICES = [
        ('STATUS_CHANGE', 'Status Change'),
        ('ASSIGNMENT', 'Assignment'),
        ('COMMENT', 'Comment'),
        ('SYSTEM', 'System Generated'),
    ]
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text="Ticket this note belongs to"
    )
    
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default='COMMENT',
        help_text="Type of note for filtering and display"
    )
    
    content = models.TextField(
        help_text="Note content (action description, observations, etc.)"
    )
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ticket_notes',
        help_text="Staff user who created this note (null for system-generated)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When note was created"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['note_type', 'created_at']),
        ]
        verbose_name = 'Ticket Note'
        verbose_name_plural = 'Ticket Notes'
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.note_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
