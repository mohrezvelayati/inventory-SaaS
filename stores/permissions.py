from rest_framework.permissions import BasePermission

from stores.models import StoreMembership


class IsStoreManager(BasePermission):
    """
    Custom permission to only allow store managers to access certain views.
    """

    def has_permission(self, request, view):
        # Check if the user is the owner of the store
        return StoreMembership.objects.filter(
            user=request.user,
            role=StoreMembership.RoleChoices.MANAGER
        ).exists()