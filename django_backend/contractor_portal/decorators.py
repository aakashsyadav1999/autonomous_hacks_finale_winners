"""
Contractor Portal Authentication Decorators.

Custom decorators to restrict access to contractor users only.
Contractors are regular Django users (not staff, not superuser)
who have an associated Contractor profile.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.decorators import method_decorator


def contractor_required(view_func):
    """
    Decorator to restrict view access to contractors only.
    
    Checks that:
    1. User is authenticated
    2. User has an associated Contractor profile
    3. User is a regular user (not staff, not superuser)
    
    Usage:
        @contractor_required
        def my_view(request):
            contractor = request.user.contractor_profile
            ...
    
    Args:
        view_func: View function to wrap
    
    Returns:
        Wrapped view function with contractor authentication
    
    Raises:
        PermissionDenied: If user is not a contractor
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has contractor profile
        if not hasattr(request.user, 'contractor_profile'):
            messages.error(
                request,
                'You do not have contractor access. Please contact administrator.'
            )
            raise PermissionDenied("User is not a contractor")
        
        # Ensure user is not staff or superuser
        if request.user.is_staff or request.user.is_superuser:
            messages.error(
                request,
                'Staff/admin users should use the admin portal.'
            )
            return redirect('admin_portal:dashboard')
        
        # All checks passed, execute view
        return view_func(request, *args, **kwargs)
    
    return wrapper


def contractor_required_class(cls):
    """
    Class decorator to restrict class-based views to contractors only.
    
    Applies contractor authentication to all HTTP methods.
    
    Usage:
        @contractor_required_class
        class MyView(View):
            def get(self, request):
                contractor = request.user.contractor_profile
                ...
    
    Args:
        cls: View class to decorate
    
    Returns:
        Decorated class with contractor authentication
    """
    # Apply decorator to dispatch method (called for all HTTP methods)
    cls.dispatch = method_decorator(contractor_required)(cls.dispatch)
    return cls
