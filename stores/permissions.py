from rest_framework.permissions import BasePermission

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
    



class HasPermission(BasePermission):

    required_permission = None

    def has_permission(self, request, view):
        membership = (request.user.memberships.first())

        if not membership:
            return False
        
        # Manager has everything
        if membership.role == 'manager':
            return True
        
        return MembershipPermission.objects.filter(
            membership = membership,
            permission__code=self.required_permission
        ).exists()