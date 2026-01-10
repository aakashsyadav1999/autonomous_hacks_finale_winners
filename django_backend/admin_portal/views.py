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
from admin_portal.models import Contractor, Ward, Notification, TicketCompletion
from django.contrib.auth.models import User


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
        'suggested_tools': ticket.suggested_tools,
        'safety_equipment': ticket.safety_equipment,
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


# ============================================================================
# CONTRACTOR MANAGEMENT VIEWS
# ============================================================================

@staff_required
def manage_contractors(request):
    """
    Contractor management page with comprehensive features.
    
    Features:
    - Search by name, email, phone, username
    - Filter by department, ward, status, date range
    - Sort by name, department, date
    - Pagination with adjustable page size
    - Statistics per contractor (tickets assigned/completed)
    - Bulk actions and export to CSV
    """
    # Get query parameters
    search_query = request.GET.get('q', '').strip()
    department_filter = request.GET.get('department', '')
    ward_filter = request.GET.get('ward', '')
    status_filter = request.GET.get('status', '')  # 'active' or 'inactive'
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort_by', 'contractor_name')
    order = request.GET.get('order', 'asc')
    per_page = request.GET.get('per_page', '12')
    
    # Base queryset with related data
    contractors_qs = Contractor.objects.select_related('user').prefetch_related('wards')
    
    # Apply search filter
    if search_query:
        contractors_qs = contractors_qs.filter(
            Q(contractor_name__icontains=search_query) |
            Q(contractor_email__icontains=search_query) |
            Q(contractor_phone__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Apply department filter
    if department_filter:
        contractors_qs = contractors_qs.filter(department=department_filter)
    
    # Apply ward filter
    if ward_filter:
        contractors_qs = contractors_qs.filter(wards__id=ward_filter).distinct()
    
    # Apply status filter
    if status_filter == 'active':
        contractors_qs = contractors_qs.filter(user__is_active=True)
    elif status_filter == 'inactive':
        contractors_qs = contractors_qs.filter(user__is_active=False)
    
    # Apply date range filter
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            contractors_qs = contractors_qs.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            contractors_qs = contractors_qs.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Apply sorting
    sort_field = sort_by
    if order == 'desc':
        sort_field = f'-{sort_field}'
    contractors_qs = contractors_qs.order_by(sort_field)
    
    # Calculate statistics for each contractor
    contractors_with_stats = []
    for contractor in contractors_qs:
        # Get ticket statistics
        total_assigned = Ticket.objects.filter(contractor=contractor).count()
        total_completed = Ticket.objects.filter(
            contractor=contractor,
            status='RESOLVED'
        ).count()
        
        completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        
        # Get last login
        last_login = contractor.user.last_login if contractor.user else None
        
        contractors_with_stats.append({
            'contractor': contractor,
            'total_assigned': total_assigned,
            'total_completed': total_completed,
            'completion_rate': round(completion_rate, 1),
            'last_login': last_login,
        })
    
    # Pagination
    try:
        per_page_int = int(per_page) if per_page != 'all' else len(contractors_with_stats)
    except ValueError:
        per_page_int = 12
    
    paginator = Paginator(contractors_with_stats, per_page_int)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all wards and departments for filters
    wards = Ward.objects.all().order_by('ward_no')
    departments = Contractor.objects.values_list('department', flat=True).distinct().order_by('department')
    
    # Calculate overall statistics
    total_contractors = Contractor.objects.count()
    active_contractors = Contractor.objects.filter(user__is_active=True).count()
    inactive_contractors = total_contractors - active_contractors
    
    context = {
        'page_obj': page_obj,
        'contractors_with_stats': page_obj.object_list,
        'wards': wards,
        'departments': departments,
        'total_contractors': total_contractors,
        'active_contractors': active_contractors,
        'inactive_contractors': inactive_contractors,
        'filters': {
            'q': search_query,
            'department': department_filter,
            'ward': ward_filter,
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'sort_by': sort_by,
            'order': order,
            'per_page': per_page,
        },
        'paginator': paginator,
    }
    
    return render(request, 'admin_portal/manage_contractors.html', context)


@staff_required
@require_POST
def create_contractor(request):
    """
    Create a new contractor with user account.
    
    POST data:
    - username: Contractor's login username
    - password: Account password
    - contractor_name: Display name
    - contractor_phone: Contact phone
    - contractor_email: Email address
    - department: Work department
    - wards: List of ward IDs (ManyToMany)
    """
    try:
        # Get form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        contractor_name = request.POST.get('contractor_name')
        contractor_phone = request.POST.get('contractor_phone')
        contractor_email = request.POST.get('contractor_email')
        department = request.POST.get('department')
        ward_ids = request.POST.getlist('wards')
        
        # Validate required fields
        if not all([username, password, contractor_name, contractor_phone, contractor_email, department]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required'
            }, status=400)
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'error': f'Username "{username}" already exists'
            }, status=400)
        
        # Create User account (regular user, not staff)
        user = User.objects.create_user(
            username=username,
            password=password,
            email=contractor_email,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )
        
        # Create Contractor profile
        contractor = Contractor.objects.create(
            user=user,
            contractor_name=contractor_name,
            contractor_phone=contractor_phone,
            contractor_email=contractor_email,
            department=department
        )
        
        # Assign wards
        if ward_ids:
            wards = Ward.objects.filter(id__in=ward_ids)
            contractor.wards.set(wards)
        
        messages.success(
            request,
            f'Contractor "{contractor_name}" created successfully with username "{username}"'
        )
        
        return JsonResponse({
            'success': True,
            'contractor_id': contractor.id,
            'message': 'Contractor created successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def update_contractor(request, contractor_id):
    """
    Update existing contractor details.
    
    Can update contractor info and ward assignments.
    Cannot change username (would require password reset flow).
    """
    try:
        contractor = get_object_or_404(Contractor, id=contractor_id)
        
        # Update contractor fields
        contractor.contractor_name = request.POST.get('contractor_name', contractor.contractor_name)
        contractor.contractor_phone = request.POST.get('contractor_phone', contractor.contractor_phone)
        contractor.contractor_email = request.POST.get('contractor_email', contractor.contractor_email)
        contractor.department = request.POST.get('department', contractor.department)
        contractor.save()
        
        # Update wards
        ward_ids = request.POST.getlist('wards')
        if ward_ids:
            wards = Ward.objects.filter(id__in=ward_ids)
            contractor.wards.set(wards)
        
        # Update user email
        contractor.user.email = contractor.contractor_email
        contractor.user.save()
        
        messages.success(request, f'Contractor "{contractor.contractor_name}" updated successfully')
        
        return JsonResponse({
            'success': True,
            'message': 'Contractor updated successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def delete_contractor(request, contractor_id):
    """
    Delete contractor and associated user account.
    
    Note: Tickets assigned to this contractor will have contractor set to NULL.
    """
    try:
        contractor = get_object_or_404(Contractor, id=contractor_id)
        contractor_name = contractor.contractor_name
        
        # Delete user (will cascade delete contractor due to OneToOne)
        contractor.user.delete()
        
        messages.success(request, f'Contractor "{contractor_name}" deleted successfully')
        
        return JsonResponse({
            'success': True,
            'message': 'Contractor deleted successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def reset_contractor_password(request, contractor_id):
    """
    Reset contractor password.
    
    Admin provides new password. No email sent - admin communicates directly.
    """
    try:
        contractor = get_object_or_404(Contractor, id=contractor_id)
        new_password = request.POST.get('new_password')
        
        if not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Password is required'
            }, status=400)
        
        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'error': 'Password must be at least 8 characters'
            }, status=400)
        
        # Set new password
        contractor.user.set_password(new_password)
        contractor.user.save()
        
        messages.success(
            request,
            f'Password reset successfully for {contractor.contractor_name}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def toggle_contractor_status(request, contractor_id):
    """
    Activate or deactivate contractor account without deleting.
    
    Toggles user.is_active field.
    """
    try:
        contractor = get_object_or_404(Contractor, id=contractor_id)
        
        # Toggle active status
        contractor.user.is_active = not contractor.user.is_active
        contractor.user.save()
        
        status_text = 'activated' if contractor.user.is_active else 'deactivated'
        
        messages.success(
            request,
            f'Contractor {contractor.contractor_name} {status_text} successfully'
        )
        
        return JsonResponse({
            'success': True,
            'is_active': contractor.user.is_active,
            'message': f'Contractor {status_text} successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def bulk_delete_contractors(request):
    """
    Delete multiple contractors at once.
    
    POST data:
    - contractor_ids: List of contractor IDs to delete
    """
    try:
        contractor_ids = request.POST.getlist('contractor_ids[]')
        
        if not contractor_ids:
            return JsonResponse({
                'success': False,
                'error': 'No contractors selected'
            }, status=400)
        
        # Get contractors
        contractors = Contractor.objects.filter(id__in=contractor_ids)
        count = contractors.count()
        
        # Delete associated users (cascades to contractors)
        for contractor in contractors:
            if contractor.user:
                contractor.user.delete()
        
        messages.success(request, f'{count} contractor(s) deleted successfully')
        
        return JsonResponse({
            'success': True,
            'deleted_count': count,
            'message': f'{count} contractor(s) deleted successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def bulk_toggle_contractor_status(request):
    """
    Activate or deactivate multiple contractors.
    
    POST data:
    - contractor_ids: List of contractor IDs
    - action: 'activate' or 'deactivate'
    """
    try:
        contractor_ids = request.POST.getlist('contractor_ids[]')
        action = request.POST.get('action')
        
        if not contractor_ids:
            return JsonResponse({
                'success': False,
                'error': 'No contractors selected'
            }, status=400)
        
        if action not in ['activate', 'deactivate']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            }, status=400)
        
        # Get contractors and update status
        contractors = Contractor.objects.filter(id__in=contractor_ids).select_related('user')
        is_active = (action == 'activate')
        count = 0
        
        for contractor in contractors:
            if contractor.user:
                contractor.user.is_active = is_active
                contractor.user.save()
                count += 1
        
        action_text = 'activated' if is_active else 'deactivated'
        messages.success(request, f'{count} contractor(s) {action_text} successfully')
        
        return JsonResponse({
            'success': True,
            'updated_count': count,
            'message': f'{count} contractor(s) {action_text} successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
def export_contractors(request):
    """
    Export contractors to CSV file.
    
    Supports all filters from manage_contractors view.
    """
    # Get same filters as manage_contractors view
    search_query = request.GET.get('q', '').strip()
    department_filter = request.GET.get('department', '')
    ward_filter = request.GET.get('ward', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset with same filters
    contractors_qs = Contractor.objects.select_related('user').prefetch_related('wards')
    
    if search_query:
        contractors_qs = contractors_qs.filter(
            Q(contractor_name__icontains=search_query) |
            Q(contractor_email__icontains=search_query) |
            Q(contractor_phone__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    if department_filter:
        contractors_qs = contractors_qs.filter(department=department_filter)
    
    if ward_filter:
        contractors_qs = contractors_qs.filter(wards__id=ward_filter).distinct()
    
    if status_filter == 'active':
        contractors_qs = contractors_qs.filter(user__is_active=True)
    elif status_filter == 'inactive':
        contractors_qs = contractors_qs.filter(user__is_active=False)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            contractors_qs = contractors_qs.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            contractors_qs = contractors_qs.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="contractors_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Contractor Name',
        'Username',
        'Email',
        'Phone',
        'Department',
        'Assigned Wards',
        'Status',
        'Tickets Assigned',
        'Tickets Completed',
        'Completion Rate (%)',
        'Last Login',
        'Created At'
    ])
    
    # Write data rows
    for contractor in contractors_qs:
        # Calculate statistics
        total_assigned = Ticket.objects.filter(contractor=contractor).count()
        total_completed = Ticket.objects.filter(contractor=contractor, status='RESOLVED').count()
        completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        
        # Get ward names
        wards_list = ', '.join([f'Ward {w.ward_no}' for w in contractor.wards.all()])
        
        writer.writerow([
            contractor.contractor_name,
            contractor.user.username if contractor.user else '-',
            contractor.contractor_email,
            contractor.contractor_phone,
            contractor.department,
            wards_list if wards_list else 'None',
            'Active' if contractor.user and contractor.user.is_active else 'Inactive',
            total_assigned,
            total_completed,
            f'{completion_rate:.1f}',
            contractor.user.last_login.strftime('%Y-%m-%d %H:%M') if contractor.user and contractor.user.last_login else 'Never',
            contractor.contractor_email,
            contractor.contractor_phone,
            contractor.department,
            wards_list if wards_list else 'None',
            'Active' if contractor.user and contractor.user.is_active else 'Inactive',
            total_assigned,
            total_completed,
            f'{completion_rate:.1f}',
            contractor.user.last_login.strftime('%Y-%m-%d %H:%M') if contractor.user and contractor.user.last_login else 'Never',
            contractor.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response


# ============================================================================
# WARD MANAGEMENT VIEWS
# ============================================================================

@staff_required
def manage_wards(request):
    """
    Manage wards with comprehensive search, filter, sort, and pagination.
    
    Features:
    - Search by ward number, ward name, admin name
    - Filter by contractor count, ticket count, date range
    - Sort by any field (ascending/descending)
    - Pagination with configurable page size
    - Statistics per ward (contractors, tickets)
    - Export to CSV
    """
    try:
        # Get all wards
        wards = Ward.objects.all()
        
        # Search functionality
        search_query = request.GET.get('search', '').strip()
        if search_query:
            wards = wards.filter(
                Q(ward_no__icontains=search_query) |
                Q(ward_name__icontains=search_query) |
                Q(ward_admin_name__icontains=search_query)
            )
        
        # Filter by contractor count
        min_contractors = request.GET.get('min_contractors', '').strip()
        max_contractors = request.GET.get('max_contractors', '').strip()
        
        # Filter by ticket count
        min_tickets = request.GET.get('min_tickets', '').strip()
        max_tickets = request.GET.get('max_tickets', '').strip()
        
        # Filter by date range
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                wards = wards.filter(created_at__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                wards = wards.filter(created_at__lte=date_to_obj)
            except ValueError:
                pass
        
        # Sorting
        sort_field = request.GET.get('sort', 'ward_no')
        order = request.GET.get('order', 'asc')

        # If sorting by ward_no we will sort numerically later after
        # we compute contractors/tickets counts to handle ward_no stored
        # as CharField (e.g. '1', '10', '2'). For other fields use ORM
        # ordering which is more efficient.
        if sort_field != 'ward_no':
            orm_sort_field = f'-{sort_field}' if order == 'desc' else sort_field
            wards = wards.order_by(orm_sort_field)
        
        # Calculate statistics for each ward
        wards_with_stats = []
        for ward in wards:
            # Count contractors assigned to this ward
            contractors_count = ward.contractors.count()
            
            # Count tickets for this ward
            tickets_count = Ticket.objects.filter(ward=ward).count()
            
            # Apply contractor/ticket count filters
            skip_ward = False
            if min_contractors and contractors_count < int(min_contractors):
                skip_ward = True
            if max_contractors and contractors_count > int(max_contractors):
                skip_ward = True
            if min_tickets and tickets_count < int(min_tickets):
                skip_ward = True
            if max_tickets and tickets_count > int(max_tickets):
                skip_ward = True
            
            if not skip_ward:
                wards_with_stats.append({
                    'ward': ward,
                    'contractors_count': contractors_count,
                    'tickets_count': tickets_count,
                })
        
        # If sorting requested by ward_no, perform numeric sort here on the
        # assembled list (wards_with_stats). This avoids lexicographic string
        # ordering issues when ward_no is a CharField.
        if sort_field == 'ward_no':
            import re

            def _ward_no_key(item: dict):
                raw = str(item['ward'].ward_no)
                m = re.match(r"^(\d+)", raw)
                if m:
                    return int(m.group(1))
                # Place non-numeric ward_no at the end
                return float('inf')

            reverse_sort = True if order == 'desc' else False
            wards_with_stats.sort(key=_ward_no_key, reverse=reverse_sort)

        # Pagination
        per_page = request.GET.get('per_page', '12')
        if per_page == 'all':
            per_page = len(wards_with_stats)
        else:
            per_page = int(per_page)
        
        paginator = Paginator(wards_with_stats, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        # Get total counts for dashboard
        total_wards = len(wards_with_stats)
        total_contractors_in_wards = sum([w['contractors_count'] for w in wards_with_stats])
        total_tickets_in_wards = sum([w['tickets_count'] for w in wards_with_stats])
        
        context = {
            'page_obj': page_obj,
            'wards_with_stats': wards_with_stats,
            'total_wards': total_wards,
            'total_contractors': total_contractors_in_wards,
            'total_tickets': total_tickets_in_wards,
            'filters': {
                'search': search_query,
                'min_contractors': min_contractors,
                'max_contractors': max_contractors,
                'min_tickets': min_tickets,
                'max_tickets': max_tickets,
                'date_from': date_from,
                'date_to': date_to,
                'sort': request.GET.get('sort', 'ward_no'),
                'order': order,
                'per_page': request.GET.get('per_page', '12'),
            }
        }
        
        return render(request, 'admin_portal/manage_wards.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading wards: {str(e)}")
        return redirect('admin_portal:dashboard')


@staff_required
def create_ward(request):
    """
    Create a new ward.
    
    Validates:
    - Ward number uniqueness
    - Phone number format
    - Required fields
    """
    if request.method == 'POST':
        try:
            ward_no = request.POST.get('ward_no', '').strip()
            ward_name = request.POST.get('ward_name', '').strip()
            ward_admin_name = request.POST.get('ward_admin_name', '').strip()
            ward_admin_no = request.POST.get('ward_admin_no', '').strip()
            ward_address = request.POST.get('ward_address', '').strip()
            
            # Validation
            if not all([ward_no, ward_name, ward_admin_name, ward_admin_no]):
                return JsonResponse({
                    'success': False,
                    'error': 'Ward number, name, admin name, and admin number are required'
                }, status=400)
            
            # Check ward number uniqueness
            if Ward.objects.filter(ward_no=ward_no).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Ward number {ward_no} already exists'
                }, status=400)
            
            # Validate phone number format (basic validation)
            import re
            phone_pattern = r'^\+?[\d\s\-\(\)]+$'
            if not re.match(phone_pattern, ward_admin_no):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid phone number format'
                }, status=400)
            
            # Create ward
            ward = Ward.objects.create(
                ward_no=ward_no,
                ward_name=ward_name,
                ward_admin_name=ward_admin_name,
                ward_admin_no=ward_admin_no,
                ward_address=ward_address
            )
            
            messages.success(request, f'Ward {ward_no} created successfully')
            return JsonResponse({
                'success': True,
                'ward_id': ward.id,
                'message': 'Ward created successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@staff_required
def update_ward(request, ward_id):
    """
    Update an existing ward.
    
    Validates:
    - Ward exists
    - Ward number uniqueness (if changed)
    - Phone number format
    """
    if request.method == 'POST':
        try:
            ward = Ward.objects.get(id=ward_id)
            
            ward_no = request.POST.get('ward_no', '').strip()
            ward_name = request.POST.get('ward_name', '').strip()
            ward_admin_name = request.POST.get('ward_admin_name', '').strip()
            ward_admin_no = request.POST.get('ward_admin_no', '').strip()
            ward_address = request.POST.get('ward_address', '').strip()
            
            # Validation
            if not all([ward_no, ward_name, ward_admin_name, ward_admin_no]):
                return JsonResponse({
                    'success': False,
                    'error': 'Ward number, name, admin name, and admin number are required'
                }, status=400)
            
            # Check ward number uniqueness (if changed)
            if ward_no != ward.ward_no:
                if Ward.objects.filter(ward_no=ward_no).exists():
                    return JsonResponse({
                        'success': False,
                        'error': f'Ward number {ward_no} already exists'
                    }, status=400)
            
            # Validate phone number format
            import re
            phone_pattern = r'^\+?[\d\s\-\(\)]+$'
            if not re.match(phone_pattern, ward_admin_no):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid phone number format'
                }, status=400)
            
            # Update ward
            ward.ward_no = ward_no
            ward.ward_name = ward_name
            ward.ward_admin_name = ward_admin_name
            ward.ward_admin_no = ward_admin_no
            ward.ward_address = ward_address
            ward.save()
            
            messages.success(request, f'Ward {ward_no} updated successfully')
            return JsonResponse({
                'success': True,
                'message': 'Ward updated successfully'
            })
            
        except Ward.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Ward not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@staff_required
def delete_ward(request, ward_id):
    """
    Delete a ward.
    
    Prevents deletion if:
    - Ward has contractors assigned
    - Ward has tickets assigned
    
    Returns error with counts if deletion is blocked.
    """
    if request.method == 'POST':
        try:
            ward = Ward.objects.get(id=ward_id)
            
            # Check if ward has contractors assigned
            contractors_count = ward.contractors.count()
            if contractors_count > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot delete ward. {contractors_count} contractor(s) are assigned to this ward. Please reassign them first.'
                }, status=400)
            
            # Check if ward has tickets
            tickets_count = Ticket.objects.filter(ward=ward).count()
            if tickets_count > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot delete ward. {tickets_count} ticket(s) are associated with this ward.'
                }, status=400)
            
            # Safe to delete
            ward_no = ward.ward_no
            ward.delete()
            
            messages.success(request, f'Ward {ward_no} deleted successfully')
            return JsonResponse({
                'success': True,
                'message': 'Ward deleted successfully'
            })
            
        except Ward.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Ward not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@staff_required
def export_wards(request):
    """
    Export wards to CSV with current filters applied.
    
    Supports all filters from manage_wards view.
    Includes statistics (contractors, tickets).
    """
    try:
        # Get all wards
        wards = Ward.objects.all()
        
        # Apply same filters as manage_wards
        search_query = request.GET.get('search', '').strip()
        if search_query:
            wards = wards.filter(
                Q(ward_no__icontains=search_query) |
                Q(ward_name__icontains=search_query) |
                Q(ward_admin_name__icontains=search_query)
            )
        
        # Date filters
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                wards = wards.filter(created_at__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                wards = wards.filter(created_at__lte=date_to_obj)
            except ValueError:
                pass
        
        # Sorting
        sort_field = request.GET.get('sort', 'ward_no')
        order = request.GET.get('order', 'asc')
        
        if order == 'desc':
            sort_field = f'-{sort_field}'
        
        wards = wards.order_by(sort_field)
        
        # Calculate statistics
        wards_with_stats = []
        min_contractors = request.GET.get('min_contractors', '').strip()
        max_contractors = request.GET.get('max_contractors', '').strip()
        min_tickets = request.GET.get('min_tickets', '').strip()
        max_tickets = request.GET.get('max_tickets', '').strip()
        
        for ward in wards:
            contractors_count = ward.contractors.count()
            tickets_count = Ticket.objects.filter(ward=ward).count()
            
            # Apply count filters
            skip_ward = False
            if min_contractors and contractors_count < int(min_contractors):
                skip_ward = True
            if max_contractors and contractors_count > int(max_contractors):
                skip_ward = True
            if min_tickets and tickets_count < int(min_tickets):
                skip_ward = True
            if max_tickets and tickets_count > int(max_tickets):
                skip_ward = True
            
            if not skip_ward:
                wards_with_stats.append({
                    'ward': ward,
                    'contractors_count': contractors_count,
                    'tickets_count': tickets_count,
                })
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="wards_{timestamp}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Ward Number',
            'Ward Name',
            'Admin Name',
            'Admin Phone',
            'Address',
            'Contractors',
            'Tickets',
            'Created Date'
        ])
        
        # Write data rows
        for item in wards_with_stats:
            ward = item['ward']
            writer.writerow([
                ward.ward_no,
                ward.ward_name,
                ward.ward_admin_name,
                ward.ward_admin_no,
                ward.ward_address or '',
                item['contractors_count'],
                item['tickets_count'],
                ward.created_at.strftime('%Y-%m-%d') if ward.created_at else ''
            ])
        
        return response
        
    except Exception as e:
        messages.error(request, f"Error exporting wards: {str(e)}")
        return redirect('admin_portal:manage_wards')


@staff_required
def get_notifications(request):
    try:
        # Get unread notifications
        unread_notifications = Notification.objects.filter(
            is_read=False
        ).select_related('ticket').order_by('-created_at')[:10]
        
        # Get unread count
        unread_count = Notification.objects.filter(is_read=False).count()
        
        # Format notifications
        notifications_data = []
        for notification in unread_notifications:
            notifications_data.append({
                'id': notification.id,
                'type': notification.notification_type,
                'message': notification.message,
                'ticket_id': notification.ticket.id if notification.ticket else None,
                'ticket_number': notification.ticket.ticket_number if notification.ticket else None,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': notification.is_read
            })
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'notifications': notifications_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def mark_all_notifications_read(request):
    """
    Mark all notifications as read.
    """
    try:
        Notification.objects.filter(is_read=False).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'message': 'All notifications marked as read'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_required
@require_POST
def delete_notification(request, notification_id):
    """
    Delete a notification.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
