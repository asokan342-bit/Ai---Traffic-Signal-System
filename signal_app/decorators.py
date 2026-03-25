from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def admin_only(view_func):
    """
    Decorator that restricts access to admin users only.
    Checks UserProfile.role == 'admin' or Django superuser status.
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Superusers always have access
        if user.is_superuser:
            return view_func(self, request, *args, **kwargs)

        # Check UserProfile role
        try:
            profile = user.profile
            if profile.role == 'admin':
                return view_func(self, request, *args, **kwargs)
        except Exception:
            pass

        return Response(
            {'error': 'Admin access required. Your role does not permit this action.'},
            status=status.HTTP_403_FORBIDDEN
        )
    return wrapper
