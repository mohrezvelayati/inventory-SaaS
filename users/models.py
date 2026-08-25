from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    
    REQUIRED_FIELDS = ['phone_number']

    def __str__(self):
        return self.username


class PasswordResetChallenge(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_challenges",
        null=True,
        blank=True,
    )
    phone_hash = models.CharField(max_length=64, db_index=True)
    requester_ip_hash = models.CharField(max_length=64, db_index=True)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"password-reset:{self.pk}:{self.delivery_status}"
