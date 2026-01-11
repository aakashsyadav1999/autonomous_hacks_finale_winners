"""
Custom decorators for Admin Portal authentication and authorization.

Provides function-based and class-based view decorators to restrict
access to staff users only (is_staff=True, is_superuser=False).
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator


def staff_required(view_func):
    """
    Decorator for function-based views requiring staff user authentication.
    
    Checks that the user is:
    1. Authenticated (logged in)
    2. Staff user (is_staff=True)
    3. NOT a superuser (is_superuser=False)
    
    Args:
        view_func: View function to decorate
    
    Returns:
        Decorated view function
    
    Raises:
        PermissionDenied: If user is not staff or is superuser
    
    Example:
        @staff_required
        def my_admin_view(request):
            # Only accessible by staff users
            return render(request, 'admin_portal/page.html')
    """
    @wraps(view_func)
    @login_required(login_url='/admin-portal/login/')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You must be a staff user to access this page.")
        
        if request.user.is_superuser:
            raise PermissionDenied("Superusers should use the Django admin interface.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def staff_required_class(cls):
    """
    Class decorator for class-based views requiring staff user authentication.
    
    Applies staff_required check to the dispatch method of a class-based view.
    
    Args:
        cls: View class to decorate
    
    Returns:
        Decorated view class
    
    Example:
        @staff_required_class
        class MyAdminView(View):
            # Only accessible by staff users
            def get(self, request):
                return render(request, 'admin_portal/page.html')
    """
    @method_decorator(login_required(login_url='/admin-portal/login/'), name='dispatch')
    class WrappedClass(cls):
        def dispatch(self, request, *args, **kwargs):
            if not request.user.is_staff:
                raise PermissionDenied("You must be a staff user to access this page.")
            
            if request.user.is_superuser:
                raise PermissionDenied("Superusers should use the Django admin interface.")
            
            return super().dispatch(request, *args, **kwargs)
    
    return WrappedClass
