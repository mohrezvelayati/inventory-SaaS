from django.db import models


class NotificationEvent(models.Model):
    class EventType(models.TextChoices):
        SALE_COMPLETED = "sale_completed", "Sale completed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    sale = models.ForeignKey(
        "sales.Sale",
        on_delete=models.CASCADE,
        related_name="notification_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payload = models.JSONField(default=dict)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_type", "sale"],
                name="unique_notification_sale_type",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="notify_status_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type}:sale={self.sale_id}:{self.status}"
