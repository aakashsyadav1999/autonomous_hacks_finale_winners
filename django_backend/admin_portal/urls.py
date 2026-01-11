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
    
    # Contractor Management
    path('contractors/', views.manage_contractors, name='manage_contractors'),
    path('contractors/create/', views.create_contractor, name='create_contractor'),
    path('contractors/<int:contractor_id>/update/', views.update_contractor, name='update_contractor'),
    path('contractors/<int:contractor_id>/delete/', views.delete_contractor, name='delete_contractor'),
    path('contractors/<int:contractor_id>/reset-password/', views.reset_contractor_password, name='reset_contractor_password'),
    path('contractors/<int:contractor_id>/toggle-status/', views.toggle_contractor_status, name='toggle_contractor_status'),
    path('contractors/bulk-delete/', views.bulk_delete_contractors, name='bulk_delete_contractors'),
    path('contractors/bulk-toggle/', views.bulk_toggle_contractor_status, name='bulk_toggle_contractor_status'),
    path('contractors/export/', views.export_contractors, name='export_contractors'),
    
    # Ward Management
    path('wards/', views.manage_wards, name='manage_wards'),
    path('wards/create/', views.create_ward, name='create_ward'),
    path('wards/<int:ward_id>/update/', views.update_ward, name='update_ward'),
    path('wards/<int:ward_id>/delete/', views.delete_ward, name='delete_ward'),
    path('wards/export/', views.export_wards, name='export_wards'),
    
    # Notification System
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # Analytics
    path('api/analytics/predict/', views.predict_analytics, name='predict_analytics'),
]
