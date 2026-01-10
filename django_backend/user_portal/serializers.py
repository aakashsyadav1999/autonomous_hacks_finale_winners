"""
REST API Serializers for User Portal.

This module provides serializers for converting model instances to JSON
and validating incoming request data.
"""

from rest_framework import serializers
from user_portal.models import CivicComplaint, Ticket
from admin_portal.models import Contractor, Ward


class CivicComplaintSerializer(serializers.ModelSerializer):
    """
    Serializer for CivicComplaint model.
    
    Handles conversion between CivicComplaint instances and JSON.
    Validates location data and image files.
    """
    
    class Meta:
        model = CivicComplaint
        fields = [
            'id',
            'session_id',
            'image',
            'street',
            'area',
            'postal_code',
            'latitude',
            'longitude',
            'is_submit',
            'is_valid',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'session_id', 'created_at', 'updated_at']


class ContractorInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying contractor information in ticket details.
    
    Shows only essential contractor info (name and phone) to citizens.
    """
    
    class Meta:
        model = Contractor
        fields = ['contractor_name', 'contractor_phone']


class WardInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying ward information in ticket details.
    
    Shows ward administrator contact details when ticket is in progress.
    """
    
    class Meta:
        model = Ward
        fields = ['ward_name', 'ward_admin_name', 'ward_admin_no']


class TicketDetailSerializer(serializers.ModelSerializer):
    """
    Detailed ticket serializer for tracking page.
    
    Includes status-specific information:
    - ASSIGNED: Shows contractor details
    - IN_PROGRESS: Shows ward details
    - RESOLVED: Shows rating option
    """
    
    contractor_info = ContractorInfoSerializer(source='contractor', read_only=True)
    ward_info = WardInfoSerializer(source='ward', read_only=True)
    image_url = serializers.SerializerMethodField()
    can_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'ticket_number',
            'status',
            'severity',
            'category',
            'department',
            'contractor_info',
            'ward_info',
            'user_rating',
            'can_rate',
            'image_url',
            'created_at',
            'updated_at'
        ]
    
    def get_image_url(self, obj):
        """
        Get complaint image URL for display.
        
        Returns:
            Image URL string or None if no image
        """
        if obj.civic_complaint and obj.civic_complaint.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.civic_complaint.image.url)
        return None
    
    def get_can_rate(self, obj):
        """
        Determine if user can rate this ticket.
        
        Rating is allowed when:
        - Status is RESOLVED
        - Rating hasn't been submitted yet
        
        Returns:
            Boolean indicating if rating form should be shown
        """
        return obj.status == 'RESOLVED' and obj.user_rating is None


class PhotoCaptureSerializer(serializers.Serializer):
    """
    Serializer for photo capture endpoint.
    
    Validates incoming photo data with coordinates.
    Expects base64-encoded image and GPS coordinates.
    """
    
    image_base64 = serializers.CharField(
        required=True,
        help_text="Base64-encoded image data"
    )
    
    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=True,
        help_text="GPS latitude coordinate"
    )
    
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=True,
        help_text="GPS longitude coordinate"
    )
    
    def validate_latitude(self, value):
        """
        Validate latitude is within valid range.
        
        Ahmedabad latitude range: approximately 22.9° to 23.2°
        """
        if not (22.0 <= float(value) <= 24.0):
            raise serializers.ValidationError(
                "Latitude must be within Ahmedabad region (22.0 to 24.0)"
            )
        return value
    
    def validate_longitude(self, value):
        """
        Validate longitude is within valid range.
        
        Ahmedabad longitude range: approximately 72.4° to 72.8°
        """
        if not (72.0 <= float(value) <= 73.0):
            raise serializers.ValidationError(
                "Longitude must be within Ahmedabad region (72.0 to 73.0)"
            )
        return value


class SubmitComplaintSerializer(serializers.Serializer):
    """
    Serializer for complaint submission endpoint.
    
    References previously captured photo by session_id or complaint_id.
    """
    
    session_id = serializers.UUIDField(
        required=False,
        help_text="Browser session ID from photo capture"
    )
    
    complaint_id = serializers.IntegerField(
        required=False,
        help_text="CivicComplaint ID from photo capture"
    )
    
    def validate(self, data):
        """
        Ensure either session_id or complaint_id is provided.
        """
        if not data.get('session_id') and not data.get('complaint_id'):
            raise serializers.ValidationError(
                "Either session_id or complaint_id must be provided"
            )
        return data


class TicketRatingSerializer(serializers.Serializer):
    """
    Serializer for submitting ticket ratings.
    
    Validates rating is between 1-5 stars.
    """
    
    ticket_number = serializers.CharField(
        required=True,
        max_length=20,
        help_text="Ticket number to rate"
    )
    
    rating = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=5,
        help_text="Rating from 1 to 5 stars"
    )
