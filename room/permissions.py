from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Allow read-only access for everyone, write access only for admin users."""

    def has_permission(self, request, view):
        """Return True for SAFE methods, otherwise require staff user."""
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
