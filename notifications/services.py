from django.db import transaction
from django.utils import timezone

from notifications.email import send_sale_completed_email
from notifications.models import NotificationEvent
from sales.models import Sale


def create_sale_completed_event(*, sale):
    if (
        sale.status != Sale.StatusChoices.COMPLETED
        or sale.completed_at is None
    ):
        raise ValueError(
            "A sale-completed notification requires a completed sale."
        )

    recipient_email = sale.store.notification_email.strip()

    if not recipient_email:
        return None

    event, _ = NotificationEvent.objects.get_or_create(
        sale=sale,
        event_type=NotificationEvent.EventType.SALE_COMPLETED,
        defaults={
            "payload": {
                "sale_id": sale.id,
                "store_id": sale.store_id,
                "store_name": sale.store.name,
                "seller_id": sale.seller_id,
                "customer_id": sale.customer_id,
                "recipient_email": recipient_email,
                "channel": sale.channel,
                "channel_label": sale.get_channel_display(),
                "total_amount": str(sale.total_amount),
                "completed_at": sale.completed_at.isoformat(),
            },
        },
    )

    return event


def deliver_notification_event(*, event_id):
    delivery_error = None
    result = None

    with transaction.atomic():
        try:
            event = (
                NotificationEvent.objects
                .select_for_update()
                .get(pk=event_id)
            )
        except NotificationEvent.DoesNotExist:
            return "missing"

        if event.status == NotificationEvent.Status.SENT:
            return "already_sent"

        event.attempt_count += 1

        try:
            send_sale_completed_email(
                recipient_email=event.payload["recipient_email"],
                payload=event.payload,
            )
        except Exception as error:
            event.status = NotificationEvent.Status.FAILED
            event.last_error = (
                f"{type(error).__name__}: {error}"
            )[:1000]
            event.sent_at = None
            delivery_error = error
            result = "failed"
        else:
            event.status = NotificationEvent.Status.SENT
            event.last_error = ""
            event.sent_at = timezone.now()
            result = "sent"

        event.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_error",
                "sent_at",
                "updated_at",
            ]
        )

    if delivery_error is not None:
        raise delivery_error

    return result


def enqueue_notification_event_after_commit(*, event):
    event_id = event.id

    def enqueue():
        from notifications.tasks import (
            deliver_notification_event_task,
        )

        deliver_notification_event_task.delay(event_id)

    transaction.on_commit(
        enqueue,
        robust=True,
    )
