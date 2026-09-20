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
