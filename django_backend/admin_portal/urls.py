"""
URL Configuration for Admin Portal.

Maps URL patterns to views for staff-only admin interface.
"""

from django.urls import path
from admin_portal import views

app_name = 'admin_portal'

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Department pages
    path('department/<str:department>/', views.department_tickets, name='department_tickets'),
    
    # Ticket detail and operations (AJAX)
    path('api/ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('api/ticket/<int:ticket_id>/status/', views.update_ticket_status, name='update_ticket_status'),
    path('api/ticket/<int:ticket_id>/assign/', views.assign_ticket, name='assign_ticket'),
    path('api/ticket/<int:ticket_id>/note/', views.add_ticket_note, name='add_ticket_note'),
    
    # Bulk operations (AJAX)
    path('api/bulk/assign/', views.bulk_assign, name='bulk_assign'),
    path('api/bulk/status/', views.bulk_status_update, name='bulk_status_update'),
    
    # Export
    path('export/', views.export_tickets, name='export_tickets'),
]
