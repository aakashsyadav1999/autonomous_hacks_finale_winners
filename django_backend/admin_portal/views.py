"""
Admin Portal Views for Smart Civic Complaint Management System.

Provides staff-only interfaces for:
- Authentication (login/logout)
- Dashboard with statistics
- Department-specific ticket management (Kanban board)
- Ticket detail and assignment
- Bulk operations
- Export functionality
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from admin_portal.decorators import staff_required
from user_portal.models import Ticket, TicketNote, CivicComplaint
from admin_portal.models import Contractor, Ward


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def admin_login(request):
    """
    Staff user login page.
    
    GET: Display login form
    POST: Authenticate user and create session
    
    Only allows staff users (is_staff=True, is_superuser=False) to login.
    Superusers are redirected to Django admin interface.
    """
    # Redirect if already authenticated as staff
    if request.user.is_authenticated:
        if request.user.is_staff and not request.user.is_superuser:
            return redirect('admin_portal:dashboard')
        elif request.user.is_superuser:
            messages.warning(request, 'Superusers should use the Django admin interface at /admin/')
            logout(request)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is staff (not superuser)
            if user.is_staff and not user.is_superuser:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect to next parameter or dashboard
                next_url = request.GET.get('next', 'admin_portal:dashboard')
                return redirect(next_url)
            elif user.is_superuser:
                messages.error(request, 'Superusers should use the Django admin interface at /admin/')
            else:
                messages.error(request, 'You must be a staff user to access this portal.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_portal/login.html')


@staff_required
def admin_logout(request):
    """
    Logout current staff user and redirect to login page.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_portal:login')


# ============================================================================
# DASHBOARD VIEW
# ============================================================================

@staff_required
def dashboard(request):
    """
    Admin dashboard with statistics and charts.
    
    Displays:
    - Total tickets (overall and per department)
    - Status distribution (submitted, assigned, in progress, resolved)
    - Recent tickets (last 10)
    - Department-wise breakdown
    - Average resolution time
    - Top contractors by rating
    """
    # Overall statistics
    total_tickets = Ticket.objects.count()
    submitted_count = Ticket.objects.filter(status='SUBMITTED').count()
    assigned_count = Ticket.objects.filter(status='ASSIGNED').count()
    in_progress_count = Ticket.objects.filter(status='IN_PROGRESS').count()
    resolved_count = Ticket.objects.filter(status='RESOLVED').count()
    
    # Department-wise breakdown
    department_stats = Ticket.objects.values('department').annotate(
        total=Count('id'),
        submitted=Count('id', filter=Q(status='SUBMITTED')),
        assigned=Count('id', filter=Q(status='ASSIGNED')),
        in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
        resolved=Count('id', filter=Q(status='RESOLVED')),
    ).order_by('department')
    
    # Recent tickets (last 10)
    recent_tickets = Ticket.objects.select_related(
        'civic_complaint', 'contractor', 'ward'
    ).order_by('-created_at')[:10]
    
    # Top contractors by rating (with at least 1 rating)
    top_contractors = Contractor.objects.filter(
        ratings__isnull=False
    ).order_by('-ratings')[:5]
    
    # Tickets created today, this week, this month
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    tickets_today = Ticket.objects.filter(created_at__date=today).count()
    tickets_week = Ticket.objects.filter(created_at__date__gte=week_ago).count()
    tickets_month = Ticket.objects.filter(created_at__date__gte=month_ago).count()
    
    # Average user rating
    avg_rating = Ticket.objects.filter(
        user_rating__isnull=False
    ).aggregate(Avg('user_rating'))['user_rating__avg']
    
    context = {
        'total_tickets': total_tickets,
        'submitted_count': submitted_count,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'department_stats': department_stats,
        'recent_tickets': recent_tickets,
        'top_contractors': top_contractors,
        'tickets_today': tickets_today,
        'tickets_week': tickets_week,
        'tickets_month': tickets_month,
        'avg_rating': round(avg_rating, 2) if avg_rating else None,
    }
    
    return render(request, 'admin_portal/dashboard.html', context)


# ============================================================================
# DEPARTMENT KANBAN BOARD VIEW
# ============================================================================

@staff_required
def department_tickets(request, department):
    """
    Department-specific ticket management with Kanban board.
    
    Displays tickets for a specific department organized by status columns.
    Supports filtering, searching, and drag-drop status updates.
    
    Args:
        department: Department name (URL parameter)
    """
    # Validate department
    valid_departments = [choice[0] for choice in Ticket.DEPARTMENT_CHOICES]
    if department not in valid_departments:
        messages.error(request, f'Invalid department: {department}')
        return redirect('admin_portal:dashboard')
    
    # Base queryset for this department
    tickets_qs = Ticket.objects.filter(department=department).select_related(
        'civic_complaint', 'contractor', 'ward'
    )
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status')
    contractor_filter = request.GET.get('contractor')
    ward_filter = request.GET.get('ward')
    severity_filter = request.GET.get('severity')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    
    if status_filter:
        tickets_qs = tickets_qs.filter(status=status_filter)
    
    if contractor_filter:
        tickets_qs = tickets_qs.filter(contractor_id=contractor_filter)
    
    if ward_filter:
        tickets_qs = tickets_qs.filter(ward_id=ward_filter)
    
    if severity_filter:
        tickets_qs = tickets_qs.filter(severity__icontains=severity_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            tickets_qs = tickets_qs.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            tickets_qs = tickets_qs.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    if search_query:
        tickets_qs = tickets_qs.filter(
            Q(ticket_number__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(civic_complaint__street__icontains=search_query) |
            Q(civic_complaint__area__icontains=search_query) |
            Q(contractor__contractor_name__icontains=search_query)
        )
    
    # Organize tickets by status for Kanban board
    submitted_tickets = tickets_qs.filter(status='SUBMITTED').order_by('-created_at')
    assigned_tickets = tickets_qs.filter(status='ASSIGNED').order_by('-created_at')
    in_progress_tickets = tickets_qs.filter(status='IN_PROGRESS').order_by('-created_at')
    resolved_tickets = tickets_qs.filter(status='RESOLVED').order_by('-created_at')
    
    # Get filter options
    contractors = Contractor.objects.all().order_by('contractor_name')
    wards = Ward.objects.all().order_by('ward_no')
    severities = tickets_qs.values_list('severity', flat=True).distinct()
    
    context = {
        'department': department,
        'submitted_tickets': submitted_tickets,
        'assigned_tickets': assigned_tickets,
        'in_progress_tickets': in_progress_tickets,
        'resolved_tickets': resolved_tickets,
        'contractors': contractors,
        'wards': wards,
        'severities': severities,
        'filters': {
            'status': status_filter,
            'contractor': contractor_filter,
            'ward': ward_filter,
            'severity': severity_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'admin_portal/department_tickets.html', context)


# ============================================================================
# TICKET DETAIL AND ASSIGNMENT (AJAX)
# ============================================================================

@staff_required
@require_http_methods(['GET'])
def ticket_detail(request, ticket_id):
    """
    Get ticket details for modal display (AJAX).
    
    Returns JSON with ticket information, complaint details,
    assignment info, and notes history.
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related('civic_complaint', 'contractor', 'ward'),
        id=ticket_id
    )
    
    # Get ticket notes
    notes = ticket.notes.select_related('created_by').order_by('-created_at')
    
    data = {
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'status': ticket.status,
        'status_display': ticket.get_status_display(),
        'category': ticket.category,
        'severity': ticket.severity,
        'department': ticket.department,
        'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        'user_rating': ticket.user_rating,
        'complaint': {
            'image_url': ticket.civic_complaint.image.url if ticket.civic_complaint.image else None,
            'street': ticket.civic_complaint.street,
            'area': ticket.civic_complaint.area,
            'postal_code': ticket.civic_complaint.postal_code,
            'latitude': str(ticket.civic_complaint.latitude),
            'longitude': str(ticket.civic_complaint.longitude),
        },
        'contractor': {
            'id': ticket.contractor.id if ticket.contractor else None,
            'name': ticket.contractor.contractor_name if ticket.contractor else None,
            'phone': ticket.contractor.contractor_phone if ticket.contractor else None,
            'ratings': str(ticket.contractor.ratings) if ticket.contractor and ticket.contractor.ratings else None,
        } if ticket.contractor else None,
        'ward': {
            'id': ticket.ward.id if ticket.ward else None,
            'number': ticket.ward.ward_no if ticket.ward else None,
            'name': ticket.ward.ward_name if ticket.ward else None,
        } if ticket.ward else None,
        'notes': [
            {
                'id': note.id,
                'type': note.note_type,
                'content': note.content,
                'created_by': note.created_by.get_full_name() or note.created_by.username if note.created_by else 'System',
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for note in notes
        ]
    }
    
    return JsonResponse(data)


@staff_required
@require_POST
def update_ticket_status(request, ticket_id):
    """
    Update ticket status via drag-and-drop (AJAX).
    
    POST Parameters:
        - new_status: Target status (SUBMITTED, ASSIGNED, IN_PROGRESS, RESOLVED)
    
    Creates a system note documenting the status change.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('new_status')
        
        # Validate status
        valid_statuses = [choice[0] for choice in Ticket.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        old_status = ticket.status
        ticket.status = new_status
        ticket.save()
        
        # Create system note
        TicketNote.objects.create(
            ticket=ticket,
            note_type='STATUS_CHANGE',
            content=f'Status changed from {old_status} to {new_status}',
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Ticket status updated to {new_status}',
            'ticket_id': ticket.id,
            'new_status': new_status
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def assign_ticket(request, ticket_id):
    """
    Assign contractor and/or ward to ticket (AJAX).
    
    POST Parameters:
        - contractor_id: Contractor ID (optional)
        - ward_id: Ward ID (optional)
    
    Creates an assignment note documenting the change.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    try:
        data = json.loads(request.body)
        contractor_id = data.get('contractor_id')
        ward_id = data.get('ward_id')
        
        note_parts = []
        
        if contractor_id:
            contractor = get_object_or_404(Contractor, id=contractor_id)
            ticket.contractor = contractor
            note_parts.append(f'Contractor: {contractor.contractor_name}')
        
        if ward_id:
            ward = get_object_or_404(Ward, id=ward_id)
            ticket.ward = ward
            note_parts.append(f'Ward: {ward.ward_name} (#{ward.ward_no})')
        
        ticket.save()
        
        # Create assignment note
        if note_parts:
            TicketNote.objects.create(
                ticket=ticket,
                note_type='ASSIGNMENT',
                content=f'Assigned - {", ".join(note_parts)}',
                created_by=request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Ticket assigned successfully',
            'contractor': {
                'id': ticket.contractor.id,
                'name': ticket.contractor.contractor_name
            } if ticket.contractor else None,
            'ward': {
                'id': ticket.ward.id,
                'number': ticket.ward.ward_no,
                'name': ticket.ward.ward_name
            } if ticket.ward else None
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def add_ticket_note(request, ticket_id):
    """
    Add a comment note to ticket (AJAX).
    
    POST Parameters:
        - content: Note content text
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Note content is required'}, status=400)
        
        note = TicketNote.objects.create(
            ticket=ticket,
            note_type='COMMENT',
            content=content,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Note added successfully',
            'note': {
                'id': note.id,
                'content': note.content,
                'created_by': note.created_by.get_full_name() or note.created_by.username,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@staff_required
@require_POST
def bulk_assign(request):
    """
    Bulk assign contractor/ward to multiple tickets (AJAX).
    
    POST Parameters:
        - ticket_ids: List of ticket IDs
        - contractor_id: Contractor ID (optional)
        - ward_id: Ward ID (optional)
    """
    try:
        data = json.loads(request.body)
        ticket_ids = data.get('ticket_ids', [])
        contractor_id = data.get('contractor_id')
        ward_id = data.get('ward_id')
        
        if not ticket_ids:
            return JsonResponse({'success': False, 'error': 'No tickets selected'}, status=400)
        
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        updated_count = 0
        
        for ticket in tickets:
            note_parts = []
            
            if contractor_id:
                contractor = get_object_or_404(Contractor, id=contractor_id)
                ticket.contractor = contractor
                note_parts.append(f'Contractor: {contractor.contractor_name}')
            
            if ward_id:
                ward = get_object_or_404(Ward, id=ward_id)
                ticket.ward = ward
                note_parts.append(f'Ward: {ward.ward_name}')
            
            ticket.save()
            
            # Create assignment note
            if note_parts:
                TicketNote.objects.create(
                    ticket=ticket,
                    note_type='ASSIGNMENT',
                    content=f'Bulk Assigned - {", ".join(note_parts)}',
                    created_by=request.user
                )
            
            updated_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} tickets assigned successfully',
            'updated_count': updated_count
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def bulk_status_update(request):
    """
    Bulk update status for multiple tickets (AJAX).
    
    POST Parameters:
        - ticket_ids: List of ticket IDs
        - new_status: Target status
    """
    try:
        data = json.loads(request.body)
        ticket_ids = data.get('ticket_ids', [])
        new_status = data.get('new_status')
        
        if not ticket_ids:
            return JsonResponse({'success': False, 'error': 'No tickets selected'}, status=400)
        
        # Validate status
        valid_statuses = [choice[0] for choice in Ticket.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        updated_count = 0
        
        for ticket in tickets:
            old_status = ticket.status
            ticket.status = new_status
            ticket.save()
            
            # Create status change note
            TicketNote.objects.create(
                ticket=ticket,
                note_type='STATUS_CHANGE',
                content=f'Bulk status change from {old_status} to {new_status}',
                created_by=request.user
            )
            
            updated_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} tickets updated to {new_status}',
            'updated_count': updated_count
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# EXPORT FUNCTIONALITY
# ============================================================================

@staff_required
def export_tickets(request):
    """
    Export tickets to CSV file.
    
    Supports filtering by department and date range via GET parameters.
    """
    department = request.GET.get('department')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset
    tickets_qs = Ticket.objects.select_related('civic_complaint', 'contractor', 'ward')
    
    if department:
        tickets_qs = tickets_qs.filter(department=department)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            tickets_qs = tickets_qs.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            tickets_qs = tickets_qs.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tickets_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Ticket Number',
        'Category',
        'Severity',
        'Department',
        'Status',
        'Location',
        'Contractor',
        'Ward',
        'User Rating',
        'Created At',
        'Updated At'
    ])
    
    # Write data rows
    for ticket in tickets_qs:
        writer.writerow([
            ticket.ticket_number,
            ticket.category,
            ticket.severity,
            ticket.department,
            ticket.get_status_display(),
            f"{ticket.civic_complaint.area}, {ticket.civic_complaint.street}",
            ticket.contractor.contractor_name if ticket.contractor else '-',
            f"{ticket.ward.ward_name} (#{ticket.ward.ward_no})" if ticket.ward else '-',
            ticket.user_rating if ticket.user_rating else '-',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response
