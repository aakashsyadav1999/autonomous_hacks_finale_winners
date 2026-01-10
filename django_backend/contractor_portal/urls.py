"""
URL configuration for contractor portal.

Routes:
- login: Contractor login page
- logout: Logout and return to login
- dashboard: Contractor dashboard with assigned tickets
- ticket/<id>/: Ticket detail view
- ticket/<id>/submit/: Submit work completion (POST)
"""

from django.urls import path
from contractor_portal import views

app_name = 'contractor_portal'

urlpatterns = [
    # Authentication
    path('login/', views.contractor_login, name='login'),
    path('logout/', views.contractor_logout, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Ticket management
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/submit/', views.submit_completion, name='submit_completion'),
]
