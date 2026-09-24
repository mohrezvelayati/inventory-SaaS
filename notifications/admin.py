from django.contrib import admin

from notifications.models import NotificationEvent


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "sale",
        "status",
        "attempt_count",
        "created_at",
        "sent_at",
    )
    list_filter = (
        "event_type",
        "status",
    )
    search_fields = (
        "sale__id",
        "sale__store__name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
