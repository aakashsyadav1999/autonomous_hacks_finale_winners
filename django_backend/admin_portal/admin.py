"""
Django Admin Configuration for Admin Portal.

Registers Ward, Contractor, TicketCompletion, and Notification models
for administrative management.
"""

from django.contrib import admin
from django.utils.html import format_html
from admin_portal.models import Ward, Contractor, TicketCompletion, Notification


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
    - Search by name and user
    - Color-coded ratings display
    - Ward management via ManyToMany
    """
    
    list_display = [
        'contractor_name',
        'user',
        'contractor_phone',
        'department',
        'get_wards',
        'ratings_display',
        'ticket_count',
        'created_at'
    ]
    
    list_filter = ['department', 'wards']
    
    search_fields = ['contractor_name', 'contractor_email', 'user__username']
    
    readonly_fields = ['ratings', 'created_at', 'updated_at', 'ticket_count']
    
    filter_horizontal = ['wards']  # Nice UI for ManyToMany selection
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Contractor Information', {
            'fields': ('contractor_name', 'contractor_phone', 'contractor_email')
        }),
        ('Work Details', {
            'fields': ('department', 'wards')
        }),
        ('Performance', {
            'fields': ('ratings', 'ticket_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_wards(self, obj):
        """Display assigned wards."""
        wards = obj.wards.all()
        if wards.exists():
            return ', '.join([f"Ward {w.ward_no}" for w in wards[:3]])
        return 'No wards assigned'
    get_wards.short_description = 'Wards'
    
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


@admin.register(TicketCompletion)
class TicketCompletionAdmin(admin.ModelAdmin):
    """
    Admin interface for TicketCompletion model.
    
    Shows contractor work submissions with AI verification status.
    """
    
    list_display = [
        'ticket',
        'contractor',
        'ai_verified_display',
        'distance_from_original',
        'submitted_at'
    ]
    
    list_filter = ['ai_verified', 'submitted_at']
    
    search_fields = [
        'ticket__ticket_number',
        'contractor__contractor_name'
    ]
    
    readonly_fields = [
        'ticket',
        'contractor',
        'after_image',
        'contractor_latitude',
        'contractor_longitude',
        'distance_from_original',
        'ai_verified',
        'ai_verification_message',
        'submitted_at'
    ]
    
    def ai_verified_display(self, obj):
        """Display verification status with visual indicator."""
        if obj.ai_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Not Verified</span>'
            )
    ai_verified_display.short_description = 'AI Status'
    
    def has_add_permission(self, request):
        """Disable manual creation - only created by contractor portal."""
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model.
    
    Shows all admin notifications with read/unread status.
    """
    
    list_display = [
        'ticket',
        'notification_type',
        'is_read_display',
        'created_at',
        'message_preview'
    ]
    
    list_filter = ['notification_type', 'is_read', 'created_at']
    
    search_fields = ['ticket__ticket_number', 'message']
    
    readonly_fields = ['ticket', 'notification_type', 'message', 'created_at']
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def is_read_display(self, obj):
        """Display read status with visual indicator."""
        if obj.is_read:
            return format_html(
                '<span style="color: gray;">✓ Read</span>'
            )
        else:
            return format_html(
                '<span style="color: blue; font-weight: bold;">● Unread</span>'
            )
    is_read_display.short_description = 'Status'
    
    def message_preview(self, obj):
        """Show truncated message."""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def mark_as_read(self, request, queryset):
        """Bulk action to mark notifications as read."""
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        """Bulk action to mark notifications as unread."""
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark selected as unread'
