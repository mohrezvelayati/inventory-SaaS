from celery import shared_task

from notifications.email import EmailDeliveryError
from notifications.services import deliver_notification_event


@shared_task(
    bind=True,
    name="notifications.deliver_notification_event",
    max_retries=3,
)
def deliver_notification_event_task(self, event_id):
    try:
        return deliver_notification_event(
            event_id=event_id,
        )
    except EmailDeliveryError as error:
        countdown = min(
            10 * (2 ** self.request.retries),
            60,
        )

        raise self.retry(
            exc=error,
            countdown=countdown,
        ) from error