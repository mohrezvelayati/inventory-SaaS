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
        unique_together = ('store', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.store.name} ({self.role})"