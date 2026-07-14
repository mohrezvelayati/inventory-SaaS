from rest_framework.permissions import BasePermission
from stores.models import MembershipPermission



class CanCreateVariant(BasePermission):
    
    permission_code = 'create_variant'

    def has_permission(self, request, view):
        membership = (
            request.user
            .memberships.
            first()
        )

        if not membership:
            return False
        
        if membership.role == 'manager':
            return True
        

        return MembershipPermission.objects.filter(
            membership=membership,
            permission_code=self.permission_code
        ).exists()