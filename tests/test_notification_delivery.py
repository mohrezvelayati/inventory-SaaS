from unittest.mock import patch

from celery.exceptions import Retry
from django.test import TestCase

from notifications.email import EmailDeliveryError
from notifications.models import NotificationEvent
from notifications.services import deliver_notification_event
from notifications.tasks import deliver_notification_event_task
from sales.models import Sale
from tests.factories import create_sale, create_store, create_user


class NotificationDeliveryTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(
            self.user,
            notification_email="manager@example.com",
        )
        self.sale = create_sale(
            self.store,
            self.membership,
            status=Sale.StatusChoices.COMPLETED,
        )
        self.event = NotificationEvent.objects.create(
            sale=self.sale,
            event_type=NotificationEvent.EventType.SALE_COMPLETED,
            payload={
                "sale_id": self.sale.id,
                "store_name": self.store.name,
                "total_amount": "1000",
                "channel_label": "حضوری",
                "completed_at": "2026-09-20T12:30:00+00:00",
                "recipient_email": "manager@example.com",
            },
        )

    @patch("notifications.services.send_sale_completed_email")
    def test_successful_delivery_marks_event_as_sent(self, send_email_mock):
        result = deliver_notification_event(event_id=self.event.id)

        self.event.refresh_from_db()

        self.assertEqual(result, "sent")
        self.assertEqual(
            self.event.status,
            NotificationEvent.Status.SENT,
        )
        self.assertEqual(self.event.attempt_count, 1)
        self.assertEqual(self.event.last_error, "")
        self.assertIsNotNone(self.event.sent_at)
        send_email_mock.assert_called_once_with(
            recipient_email="manager@example.com",
            payload=self.event.payload,
        )

    @patch("notifications.services.send_sale_completed_email")
    def test_sent_event_is_not_delivered_again(self, send_email_mock):
        self.event.status = NotificationEvent.Status.SENT
        self.event.attempt_count = 1
        self.event.save(update_fields=["status", "attempt_count"])

        result = deliver_notification_event(event_id=self.event.id)

        self.event.refresh_from_db()

        self.assertEqual(result, "already_sent")
        self.assertEqual(self.event.attempt_count, 1)
        send_email_mock.assert_not_called()

    @patch(
        "notifications.services.send_sale_completed_email",
        side_effect=EmailDeliveryError("SMTP is unavailable."),
    )
    def test_failed_delivery_records_failure_before_raising(
        self,
        send_email_mock,
    ):
        with self.assertRaises(EmailDeliveryError):
            deliver_notification_event(event_id=self.event.id)

        self.event.refresh_from_db()

        self.assertEqual(
            self.event.status,
            NotificationEvent.Status.FAILED,
        )
        self.assertEqual(self.event.attempt_count, 1)
        self.assertIn("SMTP is unavailable", self.event.last_error)
        self.assertIsNone(self.event.sent_at)
        send_email_mock.assert_called_once()

    @patch(
        "notifications.tasks.deliver_notification_event",
        side_effect=EmailDeliveryError("SMTP is unavailable."),
    )
    def test_task_retries_temporary_email_failure(self, deliver_mock):
        with patch.object(
            deliver_notification_event_task,
            "retry",
            side_effect=Retry(),
        ) as retry_mock:
            with self.assertRaises(Retry):
                deliver_notification_event_task.run(self.event.id)

        deliver_mock.assert_called_once_with(event_id=self.event.id)
        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["countdown"], 10)
        self.assertIsInstance(
            retry_mock.call_args.kwargs["exc"],
            EmailDeliveryError,
        )
