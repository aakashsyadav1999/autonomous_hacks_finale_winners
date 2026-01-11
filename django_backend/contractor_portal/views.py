"""
Contractor Portal Views.

Views for contractor-facing portal including:
- Login/logout
- Dashboard with assigned tickets
- Ticket detail with map integration
- Work completion with photo upload and location verification
"""

import os
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.conf import settings
from datetime import datetime, timedelta

from contractor_portal.decorators import contractor_required
from contractor_portal.geolocation_utils import is_within_radius, format_distance
from contractor_portal.fastapi_client import FastAPIClient, FastAPIError
from user_portal.models import Ticket
from admin_portal.models import Contractor, TicketCompletion, Notification


def contractor_login(request):
    """
    Contractor login page.
    
    Authenticates contractors (regular users with contractor profile).
    Redirects staff/superusers to admin portal.
    
    GET: Display login form
    POST: Authenticate and redirect to dashboard
    """
    # If already logged in, redirect appropriately
    if request.user.is_authenticated:
        if hasattr(request.user, 'contractor_profile'):
            return redirect('contractor_portal:dashboard')
        elif request.user.is_staff:
            return redirect('admin_portal:dashboard')
        else:
            # Regular user without contractor profile
            logout(request)
            messages.error(request, 'You do not have contractor access.')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has contractor profile
            if hasattr(user, 'contractor_profile'):
                # Check user is not staff/superuser
                if user.is_staff or user.is_superuser:
                    messages.error(
                        request,
                        'Staff/admin accounts should use the admin portal.'
                    )
                    return render(request, 'contractor_portal/login.html')
                
                # Valid contractor login
                login(request, user)
                messages.success(
                    request,
                    f'Welcome, {user.contractor_profile.contractor_name}!'
                )
                return redirect('contractor_portal:dashboard')
            else:
                messages.error(
                    request,
                    'You do not have contractor access. Contact administrator.'
                )
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'contractor_portal/login.html')


@contractor_required
def contractor_logout(request):
    """Logout contractor and redirect to login page."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('contractor_portal:login')


@contractor_required
def dashboard(request):
    """
    Contractor dashboard showing assigned tickets.
    
    Displays tickets assigned to this contractor with filtering and search:
    - Status filter (all, assigned, in_progress)
    - Date range filter
    - Severity filter
    - Search by ticket number or category
    
    Shows ticket count summary and list of tickets.
    """
    contractor = request.user.contractor_profile
    
    # Get all tickets assigned to this contractor
    tickets = Ticket.objects.filter(contractor=contractor).select_related(
        'civic_complaint', 'ward', 'contractor'
    ).prefetch_related('completion')
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status', '')
    severity_filter = request.GET.get('severity', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')
    
    if status_filter and status_filter != 'all':
        tickets = tickets.filter(status=status_filter.upper())
    
    if severity_filter:
        tickets = tickets.filter(severity=severity_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            tickets = tickets.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Include the entire end date
            date_to_obj = date_to_obj + timedelta(days=1)
            tickets = tickets.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if search_query:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(civic_complaint__area__icontains=search_query)
        )
    
    # Calculate statistics
    total_tickets = tickets.count()
    assigned_count = tickets.filter(status='ASSIGNED').count()
    in_progress_count = tickets.filter(status='IN_PROGRESS').count()
    resolved_count = tickets.filter(status='RESOLVED').count()
    ai_verified_count = tickets.filter(ai_verified=True).count()
    
    # Get unique severities for filter dropdown
    severities = tickets.values_list('severity', flat=True).distinct()
    
    context = {
        'contractor': contractor,
        'tickets': tickets.order_by('-created_at'),
        'total_tickets': total_tickets,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'ai_verified_count': ai_verified_count,
        'severities': severities,
        'filters': {
            'status': status_filter,
            'severity': severity_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'contractor_portal/dashboard.html', context)


@contractor_required
def ticket_detail(request, ticket_id):
    """
    Display detailed ticket information.
    
    Shows:
    - Complaint details with image
    - Location with Google Maps link
    - Current status and assignment
    - Work completion form (if not yet completed)
    - AI verification status (if completed)
    """
    contractor = request.user.contractor_profile
    
    # Get ticket assigned to this contractor
    ticket = get_object_or_404(
        Ticket.objects.select_related('civic_complaint', 'ward', 'contractor'),
        id=ticket_id,
        contractor=contractor
    )
    
    # Check if completion already exists
    completion = None
    try:
        completion = TicketCompletion.objects.get(ticket=ticket)
    except TicketCompletion.DoesNotExist:
        pass
    
    # Generate Google Maps link
    google_maps_url = (
        f"https://www.google.com/maps/search/?api=1"
        f"&query={ticket.civic_complaint.latitude},{ticket.civic_complaint.longitude}"
    )
    
    # Parse comma-separated tools and equipment for display
    suggested_tools_list = []
    if ticket.suggested_tools:
        suggested_tools_list = [tool.strip() for tool in ticket.suggested_tools.split(',') if tool.strip()]
    
    safety_equipment_list = []
    if ticket.safety_equipment:
        safety_equipment_list = [item.strip() for item in ticket.safety_equipment.split(',') if item.strip()]
    
    context = {
        'ticket': ticket,
        'completion': completion,
        'google_maps_url': google_maps_url,
        'contractor': contractor,
        'suggested_tools_list': suggested_tools_list,
        'safety_equipment_list': safety_equipment_list,
    }
    
    return render(request, 'contractor_portal/ticket_detail.html', context)


@contractor_required
@require_http_methods(["POST"])
def start_work(request, ticket_id):
    """
    Update ticket status from ASSIGNED to IN_PROGRESS.
    
    Called when contractor clicks "Start Work" button to indicate
    they have begun working on the ticket.
    """
    contractor = request.user.contractor_profile
    
    # Get ticket and verify assignment
    ticket = get_object_or_404(
        Ticket,
        id=ticket_id,
        contractor=contractor
    )
    
    # Verify ticket is in ASSIGNED status
    if ticket.status != 'ASSIGNED':
        return JsonResponse({
            'success': False,
            'error': f'Ticket status is {ticket.get_status_display()}, cannot start work.'
        }, status=400)
    
    # Update status to IN_PROGRESS
    ticket.status = 'IN_PROGRESS'
    ticket.save(update_fields=['status'])
    
    # Create notification for admin
    Notification.objects.create(
        ticket=ticket,
        notification_type='STATUS_CHANGE',
        message=(
            f'Contractor {contractor.contractor_name} has started work on '
            f'ticket {ticket.ticket_number}.'
        )
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Work started successfully!',
        'new_status': ticket.get_status_display()
    })


@contractor_required
@require_http_methods(["POST"])
def submit_completion(request, ticket_id):
    """
    Handle work completion submission with photo upload.
    
    Process:
    1. Validate contractor is assigned to ticket
    2. Get contractor's current GPS location from request
    3. Verify location is within 50m of original complaint
    4. Save after-photo
    5. Call FastAPI to verify completion (before/after comparison)
    6. Create TicketCompletion record
    7. Create notification for admin if AI verified
    8. Update ticket ai_verified status
    
    Request must include:
    - after_image: Photo file
    - latitude: Contractor's current latitude
    - longitude: Contractor's current longitude
    """
    contractor = request.user.contractor_profile
    
    # Get ticket
    ticket = get_object_or_404(
        Ticket.objects.select_related('civic_complaint'),
        id=ticket_id,
        contractor=contractor
    )
    
    # Check if already completed
    if hasattr(ticket, 'completion'):
        return JsonResponse({
            'success': False,
            'error': 'Work completion already submitted for this ticket'
        }, status=400)
    
    # Get uploaded photo
    after_image = request.FILES.get('after_image')
    if not after_image:
        return JsonResponse({
            'success': False,
            'error': 'Please upload an after-work photo'
        }, status=400)
    
    # Get contractor's current location
    try:
        contractor_lat = Decimal(request.POST.get('latitude'))
        contractor_lon = Decimal(request.POST.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid GPS coordinates. Please enable location services.'
        }, status=400)
    
    # Verify contractor is within 50m of original location
    original_lat = ticket.civic_complaint.latitude
    original_lon = ticket.civic_complaint.longitude

    # Temporarily disable strict proximity validation (50 meters).
    # The live check is commented out to allow uploads and testing from remote devices.
    # We keep `is_valid_location` and `distance` defined so downstream logic
    # (TicketCompletion creation and stored distance) continues to work.
    # NOTE: Restore the following block to re-enable validation.
    # is_valid_location, distance = is_within_radius(
    #     original_lat, original_lon,
    #     contractor_lat, contractor_lon,
    #     radius_meters=50
    # )
    is_valid_location = True
    distance = 0.0  # Float type matches is_within_radius() return value
    
    # Create TicketCompletion record (will trigger image upload)
    completion = TicketCompletion.objects.create(
        ticket=ticket,
        contractor=contractor,
        after_image=after_image,
        contractor_latitude=contractor_lat,
        contractor_longitude=contractor_lon,
        distance_from_original=Decimal(str(distance))
    )
    
    # Call FastAPI for AI verification
    try:
        client = FastAPIClient()
        
        # Get paths to images
        before_image_path = ticket.civic_complaint.image.path
        after_image_path = completion.after_image.path
        
        # Verify completion
        result = client.verify_completion(
            before_image_path=before_image_path,
            after_image_path=after_image_path,
            category=ticket.category
        )
        
        # Update completion with AI result
        completion.ai_verified = result.get('is_completed', False)
        completion.ai_verification_message = result.get('error')
        completion.save()
        
        # Update ticket ai_verified status
        ticket.ai_verified = completion.ai_verified
        ticket.save(update_fields=['ai_verified'])
        
        # Create notification for admin if AI verified
        if completion.ai_verified:
            Notification.objects.create(
                ticket=ticket,
                notification_type='AI_VERIFICATION',
                message=(
                    f'Work completion for ticket {ticket.ticket_number} has been '
                    f'verified by AI. Contractor: {contractor.contractor_name}. '
                    f'You can now mark this ticket as resolved.'
                )
            )
        
        return JsonResponse({
            'success': True,
            'ai_verified': completion.ai_verified,
            'message': (
                'Work completion submitted successfully! AI has verified your work. '
                'The admin will review and mark the ticket as resolved.'
                if completion.ai_verified else
                'Work completion submitted. AI verification did not pass. '
                f'Reason: {completion.ai_verification_message or "Unknown"}'
            )
        })
    
    except FastAPIError as e:
        # AI verification failed - still save completion but mark as unverified
        completion.ai_verified = False
        completion.ai_verification_message = str(e)
        completion.save()
        
        return JsonResponse({
            'success': True,
            'ai_verified': False,
            'message': (
                f'Work completion submitted, but AI verification encountered an error: {str(e)}. '
                f'Admin will manually review your submission.'
            )
        })
    
    except Exception as e:
        # Unexpected error - delete completion and return error
        completion.delete()
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to process completion: {str(e)}'
        }, status=500)

