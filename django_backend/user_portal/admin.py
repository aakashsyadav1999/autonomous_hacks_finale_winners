"""
Django Admin Configuration for User Portal.

Registers CivicComplaint and Ticket models with customized admin interface.
"""

from django.contrib import admin
from django.utils.html import format_html
from user_portal.models import CivicComplaint, Ticket


@admin.register(CivicComplaint)
class CivicComplaintAdmin(admin.ModelAdmin):
    """
    Admin interface for CivicComplaint model.
    
    Features:
    - List view with key fields
    - Filters for submission status and validation
    - Search by area and postal code
    - Image thumbnail preview
    """
    
    list_display = [
        'id',
        'session_id',
        'area',
        'postal_code',
        'is_submit',
        'is_valid',
        'created_at',
        'image_preview'
    ]
    
    list_filter = ['is_submit', 'is_valid', 'created_at']
    
    search_fields = ['area', 'street', 'postal_code', 'session_id']
    
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'image_preview_large']
    
    fieldsets = (
        ('Photo', {
            'fields': ('image', 'image_preview_large')
        }),
        ('Location Details', {
            'fields': ('street', 'area', 'postal_code', 'latitude', 'longitude')
        }),
        ('Status', {
            'fields': ('is_submit', 'is_valid')
        }),
        ('Metadata', {
            'fields': ('session_id', 'created_at', 'updated_at')
        }),
    )
    
    def image_preview(self, obj):
        """Display small image thumbnail in list view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        """Display larger image preview in detail view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px;" />',
                obj.image.url
            )
        return 'No image'
    image_preview_large.short_description = 'Image Preview'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Admin interface for Ticket model.
    
    Features:
    - List view with ticket details
    - Filters for status, department, severity
    - Search by ticket number and category
    - Contractor and ward assignment
    - User rating display
    """
    
    list_display = [
        'ticket_number',
        'category',
        'severity',
        'department',
        'status',
        'contractor',
        'ward',
        'user_rating_display',
        'created_at'
    ]
    
    list_filter = ['status', 'department', 'severity', 'created_at']
    
    search_fields = ['ticket_number', 'category', 'department']
    
    readonly_fields = ['ticket_number', 'created_at', 'updated_at', 'user_rating']
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'civic_complaint', 'status')
        }),
        ('Issue Details', {
            'fields': ('category', 'severity', 'department')
        }),
        ('Assignment', {
            'fields': ('contractor', 'ward')
        }),
        ('Feedback', {
            'fields': ('user_rating',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_rating_display(self, obj):
        """Display rating with stars."""
        if obj.user_rating:
            stars = '⭐' * obj.user_rating
            return format_html('<span style="color: gold;">{}</span>', stars)
        return '-'
    user_rating_display.short_description = 'User Rating'
    
    def save_model(self, request, obj, form, change):
        """
        Override save to handle status transitions.
        
        Admin can change status and assign contractor/ward.
        """
        super().save_model(request, obj, form, change)
