from django.db import models


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
    


class Permission(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
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