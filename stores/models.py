from django.db import models
from django.db.models import Q


class Store(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    



class StoreMembership(models.Model):
    
    class RoleChoices(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        SELLER = 'seller', 'Seller'
        ADMIN = 'admin', 'Admin'


    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_store_membership_user',
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.store.name} ({self.role})"


class StoreInvitation(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REVOKED = 'revoked', 'Revoked'

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    invited_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sent_store_invitations',
    )
    phone_number = models.CharField(max_length=11)
    role = models.CharField(
        max_length=20,
        choices=(
            (StoreMembership.RoleChoices.SELLER, 'Seller'),
            (StoreMembership.RoleChoices.ADMIN, 'Admin'),
        ),
    )
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        related_name='accepted_store_invitations',
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(role__in=['seller', 'admin']),
                name='store_invitation_role_is_invitable',
            ),
            models.UniqueConstraint(
                fields=['store', 'phone_number'],
                condition=Q(status='pending'),
                name='unique_pending_invitation_per_store_phone',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.store.name} ({self.role})"
    


class Permission(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    



class MembershipPermission(models.Model):
    membership = models.ForeignKey(StoreMembership, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='memberships')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['membership', 'permission'],
                name='unique_membership_permission'
            )
        ]

    def __str__(self):
        return f"{self.membership} - {self.permission.name}"
