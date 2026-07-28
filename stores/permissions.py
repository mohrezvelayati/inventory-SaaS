from rest_framework.permissions import BasePermission

from stores.services import get_current_membership, MembershipResolutionError
from stores.models import MembershipPermission, StoreMembership




class CanCreateProduct(BasePermission):
    """
    Custom permission to check if the user has the permission to create a product in their store.
    """

    permission_code = 'create_product'

    def has_permission(self, request, view):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return False

        if membership.role == StoreMembership.RoleChoices.MANAGER:
            return True
        
        return MembershipPermission.objects.filter(
            membership=membership,
            permission__code=self.permission_code
        ).exists()
    



class HasPermission(BasePermission):

    required_permission = None

    def has_permission(self, request, view):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return False

        if membership.role == StoreMembership.RoleChoices.MANAGER:
            return True

        if self.required_permission is None:
            return False
        
        return MembershipPermission.objects.filter(
            membership = membership,
            permission__code=self.required_permission
        ).exists()