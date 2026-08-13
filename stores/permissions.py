from rest_framework.permissions import BasePermission

from stores.models import MembershipPermission, StoreMembership
from stores.services import get_current_membership, MembershipResolutionError



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


class CanManageMembers(HasPermission):
    def has_permission(self, request, view):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return False

        return membership.role == StoreMembership.RoleChoices.MANAGER
