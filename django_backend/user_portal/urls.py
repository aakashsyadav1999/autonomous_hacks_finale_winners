"""
URL Configuration for User Portal API.

Template Pages:
    GET  /capture/ - Photo capture page
    GET  /track/ - Ticket tracking page

API Endpoints (mounted at /api/user/):
    POST capture-photo/ - Capture photo with location
    POST submit-complaint/ - Submit complaint for AI validation
    GET  track-ticket/ - Track ticket status
    POST rate-ticket/ - Rate resolved ticket
"""

from django.urls import path
from user_portal import views

app_name = 'user_portal'

urlpatterns = [
        # API endpoints
    path('capture-photo/', views.CapturePhotoView.as_view(), name='capture_photo'),
    path('submit-complaint/', views.SubmitComplaintView.as_view(), name='submit_complaint'),
    path('track-ticket/', views.TrackTicketView.as_view(), name='track_ticket'),
    path('rate-ticket/', views.RateTicketView.as_view(), name='rate_ticket'),
]

# Template views (separate URL pattern)
template_urlpatterns = [
    path('capture/', views.CapturePhotoTemplateView.as_view(), name='capture_page'),
    path('track/', views.TrackTicketTemplateView.as_view(), name='track_page'),
]
