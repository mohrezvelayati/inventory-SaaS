from io import StringIO
from unittest.mock import call, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from notifications.models import NotificationEvent
from sales.models import Sale
from tests.factories import create_sale, create_store, create_user


class RetryNotificationsCommandTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(self.user)

    def create_event(self, *, status):
        sale = create_sale(
            self.store,
            self.membership,
            status=Sale.StatusChoices.COMPLETED,
        )
        return NotificationEvent.objects.create(
            sale=sale,
            event_type=NotificationEvent.EventType.SALE_COMPLETED,
            status=status,
            payload={"recipient_email": "manager@example.com"},
        )

    @patch(
        "notifications.management.commands.retry_notifications."
        "deliver_notification_event_task.delay"
    )
    def test_queues_only_pending_events_by_default(self, delay_mock):
        pending_event = self.create_event(
            status=NotificationEvent.Status.PENDING,
        )
        self.create_event(status=NotificationEvent.Status.FAILED)
        self.create_event(status=NotificationEvent.Status.SENT)
        output = StringIO()

        call_command("retry_notifications", stdout=output)

        delay_mock.assert_called_once_with(pending_event.id)
        self.assertIn("Queued 1 notification event(s).", output.getvalue())

    @patch(
        "notifications.management.commands.retry_notifications."
        "deliver_notification_event_task.delay"
    )
    def test_include_failed_and_limit_select_oldest_events(self, delay_mock):
        first_event = self.create_event(
            status=NotificationEvent.Status.PENDING,
        )
        second_event = self.create_event(
            status=NotificationEvent.Status.FAILED,
        )
        self.create_event(status=NotificationEvent.Status.PENDING)
        self.create_event(status=NotificationEvent.Status.SENT)

        call_command(
            "retry_notifications",
            "--include-failed",
            "--limit=2",
        )

        self.assertEqual(
            delay_mock.call_args_list,
            [call(first_event.id), call(second_event.id)],
        )

    @patch(
        "notifications.management.commands.retry_notifications."
        "deliver_notification_event_task.delay",
        side_effect=OSError("Redis is unavailable."),
    )
    def test_broker_failure_stops_command_without_changing_event(
        self,
        delay_mock,
    ):
        event = self.create_event(
            status=NotificationEvent.Status.PENDING,
        )

        with self.assertRaisesMessage(
            CommandError,
            f"Could not queue notification event {event.id}",
        ):
            call_command("retry_notifications")

        event.refresh_from_db()
        self.assertEqual(event.status, NotificationEvent.Status.PENDING)
        self.assertEqual(event.attempt_count, 0)
        delay_mock.assert_called_once_with(event.id)

    def test_rejects_non_positive_limit(self):
        with self.assertRaisesMessage(
            CommandError,
            "--limit must be greater than zero.",
        ):
            call_command("retry_notifications", "--limit=0")
