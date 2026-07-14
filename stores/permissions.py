from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from stores.services import get_user_stores
from stores.models import MembershipPermission


class CanCreateProduct(BasePermission):
    """
    Custom permission to check if the user has the permission to create a product in their store.
    """

    permission_code = 'create_product'

    def has_permission(self, request, view):
        user = request.user
        memberships = user.memberships.first()

        if not memberships:
            return False
        
        if memberships.role == 'manager':
            return True
        
        return MembershipPermission.objects.filter(
            membership=memberships,
            permission__code=self.permission_code
        ).exists()