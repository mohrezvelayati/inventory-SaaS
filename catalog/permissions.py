from rest_framework.permissions import BasePermission


from stores.models import MembershipPermission, StoreMembership
from stores.services import get_current_membership, MembershipResolutionError


class CanCreateVariant(BasePermission):
    permission_code = 'create_variant'

    def has_permission(self, request, view):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return False

        if membership.role == StoreMembership.RoleChoices.MANAGER:
            return True
        

        return MembershipPermission.objects.filter(
            membership=membership,
            permission__code=self.permission_code,
        ).exists()