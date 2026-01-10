"""
Django Admin Configuration for Admin Portal.

Registers Ward and Contractor models for administrative management.
"""

from django.contrib import admin
from django.utils.html import format_html
from admin_portal.models import Ward, Contractor


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    """
    Admin interface for Ward model.
    
    Features:
    - List view with ward details
    - Search by ward number and name
    - Ward administrator contact management
    """
    
    list_display = [
        'ward_no',
        'ward_name',
        'ward_admin_name',
        'ward_admin_no',
        'created_at'
    ]
    
    search_fields = ['ward_no', 'ward_name', 'ward_admin_name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Ward Information', {
            'fields': ('ward_no', 'ward_name', 'ward_address')
        }),
        ('Administrator Contact', {
            'fields': ('ward_admin_name', 'ward_admin_no')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    """
    Admin interface for Contractor model.
    
    Features:
    - List view with contractor details and ratings
    - Filters for department and rating range
    - Search by name and area
    - Color-coded ratings display
    """
    
    list_display = [
        'contractor_name',
        'contractor_phone',
        'department',
        'assigned_area',
        'ratings_display',
        'ticket_count',
        'created_at'
    ]
    
    list_filter = ['department', 'assigned_area']
    
    search_fields = ['contractor_name', 'contractor_email', 'assigned_area']
    
    readonly_fields = ['ratings', 'created_at', 'updated_at', 'ticket_count']
    
    fieldsets = (
        ('Contractor Information', {
            'fields': ('contractor_name', 'contractor_phone', 'contractor_email')
        }),
        ('Work Details', {
            'fields': ('department', 'assigned_area')
        }),
        ('Performance', {
            'fields': ('ratings', 'ticket_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def ratings_display(self, obj):
        """Display rating with color coding."""
        rating = float(obj.ratings)
        
        # Color code based on rating
        if rating >= 4.0:
            color = 'green'
        elif rating >= 3.0:
            color = 'orange'
        elif rating > 0:
            color = 'red'
        else:
            color = 'gray'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f} ⭐</span>',
            color,
            rating
        )
    ratings_display.short_description = 'Rating'
    
    def ticket_count(self, obj):
        """Display number of tickets assigned."""
        count = obj.tickets.count()
        resolved = obj.tickets.filter(status='RESOLVED').count()
        return f"{resolved}/{count} resolved"
    ticket_count.short_description = 'Tickets'
