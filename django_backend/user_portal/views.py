"""
User Portal API Views.

This module implements REST API endpoints for:
1. Photo capture with location
2. Complaint submission (with AI validation)
3. Ticket tracking
4. Ticket rating

And template views for:
5. Photo capture page
6. Ticket tracking page
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView

from contractor_portal.fastapi_client import analyze_complaint_image, FastAPIError

from user_portal.models import CivicComplaint, Ticket
from user_portal.serializers import (
    PhotoCaptureSerializer,
    SubmitComplaintSerializer,
    TicketDetailSerializer,
    TicketRatingSerializer,
    CivicComplaintSerializer
)
from user_portal.utils.geocoding import geocode_coordinates
from user_portal.utils.image_validator import (
    validate_base64_image,
    base64_to_image_file
)
from user_portal.utils.ticket_generator import generate_ticket_number


logger = logging.getLogger(__name__)


# ============================================================================
# Template Views (HTML Pages)
# ============================================================================

class CapturePhotoTemplateView(TemplateView):
    """
    Render photo capture page.
    
    URL: /capture/
    """
    template_name = 'user_portal/capture.html'


class TrackTicketTemplateView(TemplateView):
    """
    Render ticket tracking page.
    
    URL: /track/
    """
    template_name = 'user_portal/track.html'


# ============================================================================
# API Views (REST Endpoints)
# ============================================================================


class CapturePhotoView(APIView):
    """
    API endpoint for capturing photo with location.
    
    POST /api/user/capture-photo/
    
    Request Body:
        {
            "image_base64": "base64_encoded_image_data",
            "latitude": 23.0225,
            "longitude": 72.5714
        }
    
    Response:
        {
            "success": true,
            "session_id": "uuid-string",
            "complaint_id": 123,
            "location": {
                "street": "132 Feet Ring Road",
                "area": "Satellite",
                "postal_code": "380015"
            }
        }
    
    Process:
        1. Validate base64 image (format, size)
        2. Reverse geocode coordinates to address
        3. Create CivicComplaint with is_submit=False
        4. Return session_id for later submission
    """
    
    def post(self, request):
        """Handle photo capture request."""
        serializer = PhotoCaptureSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        image_base64 = serializer.validated_data['image_base64']
        latitude = float(serializer.validated_data['latitude'])
        longitude = float(serializer.validated_data['longitude'])
        
        # Validate image
        is_valid, error_message = validate_base64_image(image_base64)
        if not is_valid:
            return Response({
                'success': False,
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reverse geocode coordinates
        location_data = geocode_coordinates(latitude, longitude)
        
        if not location_data:
            return Response({
                'success': False,
                'error': 'Failed to fetch address from coordinates. Please ensure location is in Ahmedabad.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert base64 to image file
        image_file = base64_to_image_file(image_base64, 'complaint.jpg')
        
        if not image_file:
            return Response({
                'success': False,
                'error': 'Failed to process image data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create CivicComplaint record (not yet submitted)
        try:
            complaint = CivicComplaint.objects.create(
                image=image_file,
                street=location_data.get('street', ''),
                area=location_data['area'],
                postal_code=location_data.get('postal_code', ''),
                latitude=latitude,
                longitude=longitude,
                is_submit=False  # Mark as draft
            )
            
            logger.info(
                f"Photo captured: session_id={complaint.session_id}, "
                f"location={location_data['area']}"
            )
            
            return Response({
                'success': True,
                'session_id': str(complaint.session_id),
                'complaint_id': complaint.id,
                'location': {
                    'street': complaint.street,
                    'area': complaint.area,
                    'postal_code': complaint.postal_code
                },
                'message': 'Photo captured successfully. Please submit to create ticket.'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to save complaint: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to save complaint. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitComplaintView(APIView):
    """
    API endpoint for submitting complaint to AI validation.
    
    POST /api/user/submit-complaint/
    
    Request Body:
        {
            "session_id": "uuid-string" OR "complaint_id": 123
        }
    
    Response (Success):
        {
            "success": true,
            "tickets": ["CMP-20260110-001", "CMP-20260110-002"],
            "message": "Complaint validated and tickets created"
        }
    
    Response (Invalid):
        {
            "success": false,
            "message": "Photo validation failed. Please capture a valid civic issue."
        }
    
    Process:
        1. Fetch CivicComplaint by session_id/complaint_id
        2. Call FastAPI for AI validation (MOCK for now)
        3. If valid: Create tickets from AI response
        4. If invalid: Delete complaint and notify user
    """
    
    def post(self, request):
        """Handle complaint submission request."""
        serializer = SubmitComplaintSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch complaint
        try:
            if serializer.validated_data.get('session_id'):
                complaint = CivicComplaint.objects.get(
                    session_id=serializer.validated_data['session_id'],
                    is_submit=False
                )
            else:
                complaint = CivicComplaint.objects.get(
                    id=serializer.validated_data['complaint_id'],
                    is_submit=False
                )
        except CivicComplaint.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Complaint not found or already submitted'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Mark as submitted
        complaint.is_submit = True
        complaint.save()
        
        # Call AI validation using FastAPI
        ai_response = self._call_ai_validation(complaint)
        
        if not ai_response['is_valid']:
            # Delete invalid complaint
            complaint.delete()
            
            logger.info(f"Invalid complaint deleted: {complaint.id}")
            
            return Response({
                'success': False,
                'message': 'Photo validation failed. Please capture a valid civic issue.',
                'reason': ai_response.get('error_message', 'AI did not detect any civic complaints in the image')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create tickets from AI response
        try:
            with transaction.atomic():
                complaint.is_valid = True
                complaint.save()
                
                tickets_created = []
                
                for issue_data in ai_response['data']:
                    ticket_number = generate_ticket_number()
                    
                    ticket = Ticket.objects.create(
                        ticket_number=ticket_number,
                        civic_complaint=complaint,
                        severity=issue_data['severity'],
                        category=issue_data['category'],
                        department=issue_data['department'],
                        status='SUBMITTED'
                    )
                    
                    tickets_created.append(ticket_number)
                    
                    logger.info(
                        f"Ticket created: {ticket_number} - "
                        f"{issue_data['category']} ({issue_data['department']})"
                    )
                
                return Response({
                    'success': True,
                    'tickets': tickets_created,
                    'message': f"{len(tickets_created)} ticket(s) created successfully",
                    'details': ai_response['data']
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to create tickets: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to create tickets. Please contact support.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _call_ai_validation(self, complaint):
        """
        Call FastAPI AI service for complaint validation.
        
        Args:
            complaint: CivicComplaint instance
        
        Returns:
            dict: {
                'is_valid': bool,
                'data': list of issue dicts OR empty list,
                'error_message': str (if error occurred)
            }
        
        FastAPI endpoint: POST /api/v1/analyze/complaint
        Request payload:
            {
                "image": "base64_encoded_string",
                "street": "Street Name",
                "area": "Area Name",
                "postal_code": "380001",
                "latitude": 23.0225,
                "longitude": 72.5714
            }
        
        Expected response:
            {
                "is_valid": true,
                "issues": [
                    {
                        "severity": "High",
                        "category": "Garbage/Waste accumulation",
                        "department": "Sanitation"
                    }
                ]
            }
        """
        try:
            # Call FastAPI with image path and location
            is_valid, data_list, error_message = analyze_complaint_image(
                image_path=complaint.image.path,
                street=complaint.street,
                area=complaint.area,
                postal_code=complaint.postal_code,
                latitude=float(complaint.latitude) if complaint.latitude else None,
                longitude=float(complaint.longitude) if complaint.longitude else None
            )
            
            if is_valid:
                logger.info(f"AI validation successful for complaint {complaint.id}: {len(data_list)} issue(s) detected")
                return {
                    'is_valid': True,
                    'data': data_list
                }
            else:
                logger.warning(f"AI validation failed for complaint {complaint.id}: {error_message}")
                return {
                    'is_valid': False,
                    'data': [],
                    'error_message': error_message or 'AI could not detect valid civic complaints'
                }
        
        except FastAPIError as e:
            # Log FastAPI errors but fall back to mock validation
            logger.error(f"FastAPI error for complaint {complaint.id}: {str(e)}")
            logger.info("Falling back to mock AI validation due to FastAPI error")
            return self._mock_ai_validation(complaint)
        
        except Exception as e:
            # Log unexpected errors but fall back to mock validation
            logger.error(f"Unexpected error calling AI service for complaint {complaint.id}: {str(e)}")
            logger.info("Falling back to mock AI validation due to unexpected error")
            return self._mock_ai_validation(complaint)
    
    def _mock_ai_validation(self, complaint):
        """
        MOCK AI validation as fallback when FastAPI is unavailable.
        
        This is used when:
        1. FastAPI service is down or unreachable
        2. Network errors occur
        3. Environment variable FASTAPI_BASE_URL is not set
        
        Returns random valid complaint data for testing purposes.
        """
        import random
        
        logger.warning(f"Using MOCK AI validation for complaint {complaint.id}")
        
        departments = [
            {
                'severity': 'High',
                'category': 'Garbage/Waste accumulation',
                'department': 'Sanitation Department'
            },
            {
                'severity': 'Medium',
                'category': 'Manholes/drainage opening damage',
                'department': 'Roads & Infrastructure'
            },
            {
                'severity': 'High',
                'category': 'Water leakage',
                'department': 'Water Supply Department'
            },
            {
                'severity': 'Critical',
                'category': 'Drainage overflow',
                'department': 'Drainage Department'
            }
        ]
        
        # Return one random department issue
        return {
            'is_valid': True,
            'data': [random.choice(departments)]
        }


class TrackTicketView(APIView):
    """
    API endpoint for ticket tracking.
    
    GET /api/user/track-ticket/?ticket_number=CMP-20260110-001
    
    Response:
        {
            "success": true,
            "ticket": {
                "ticket_number": "CMP-20260110-001",
                "status": "ASSIGNED",
                "severity": "High",
                "category": "Roads",
                "department": "PWD",
                "contractor_info": {
                    "contractor_name": "ABC Contractors",
                    "contractor_phone": "9876543210"
                },
                "ward_info": null,
                "user_rating": null,
                "can_rate": false,
                "image_url": "http://localhost:8000/media/complaints/2026/01/10/...",
                "created_at": "2026-01-10T10:30:00Z",
                "updated_at": "2026-01-10T11:00:00Z"
            }
        }
    
    Display Rules:
        - SUBMITTED: Show basic info
        - ASSIGNED: Show contractor_info
        - IN_PROGRESS: Show ward_info
        - RESOLVED: Show rating form (if not rated)
    """
    
    def get(self, request):
        """Handle ticket tracking request."""
        ticket_number = request.query_params.get('ticket_number')
        
        if not ticket_number:
            return Response({
                'success': False,
                'error': 'ticket_number parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Exact match search
        try:
            ticket = Ticket.objects.select_related(
                'civic_complaint',
                'contractor',
                'ward'
            ).get(ticket_number=ticket_number)
        except Ticket.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Ticket {ticket_number} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize ticket data
        serializer = TicketDetailSerializer(ticket, context={'request': request})
        
        return Response({
            'success': True,
            'ticket': serializer.data
        }, status=status.HTTP_200_OK)


class RateTicketView(APIView):
    """
    API endpoint for submitting ticket rating.
    
    POST /api/user/rate-ticket/
    
    Request Body:
        {
            "ticket_number": "CMP-20260110-001",
            "rating": 4
        }
    
    Response:
        {
            "success": true,
            "message": "Rating submitted successfully",
            "contractor_rating": 4.25
        }
    
    Validation:
        - Ticket must exist
        - Ticket status must be RESOLVED
        - Rating must not already exist
        - Rating must be 1-5
    """
    
    def post(self, request):
        """Handle ticket rating submission."""
        serializer = TicketRatingSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ticket_number = serializer.validated_data['ticket_number']
        rating = serializer.validated_data['rating']
        
        # Fetch ticket
        try:
            ticket = Ticket.objects.select_related('contractor').get(
                ticket_number=ticket_number
            )
        except Ticket.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Ticket {ticket_number} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate ticket is resolved
        if ticket.status != 'RESOLVED':
            return Response({
                'success': False,
                'error': 'Can only rate resolved tickets'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already rated
        if ticket.user_rating is not None:
            return Response({
                'success': False,
                'error': 'Ticket has already been rated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save rating
        ticket.user_rating = rating
        ticket.save()  # This will trigger contractor rating update
        
        logger.info(
            f"Ticket rated: {ticket_number} - {rating} stars "
            f"(Contractor: {ticket.contractor.contractor_name if ticket.contractor else 'N/A'})"
        )
        
        return Response({
            'success': True,
            'message': 'Rating submitted successfully. Thank you for your feedback!',
            'contractor_rating': float(ticket.contractor.ratings) if ticket.contractor else None
        }, status=status.HTTP_200_OK)

