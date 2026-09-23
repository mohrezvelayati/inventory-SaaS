from django.core.management.base import BaseCommand, CommandError

from notifications.models import NotificationEvent
from notifications.tasks import deliver_notification_event_task


class Command(BaseCommand):
    help = "Queue pending notification events for another delivery attempt."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-failed",
            action="store_true",
            help="Also queue events whose previous delivery failed.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of events to queue (default: 100).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit <= 0:
            raise CommandError("--limit must be greater than zero.")

        statuses = [NotificationEvent.Status.PENDING]
        if options["include_failed"]:
            statuses.append(NotificationEvent.Status.FAILED)

        event_ids = list(
            NotificationEvent.objects
            .filter(status__in=statuses)
            .order_by("created_at", "id")
            .values_list("id", flat=True)[:limit]
        )

        queued_count = 0

        for event_id in event_ids:
            try:
                deliver_notification_event_task.delay(event_id)
            except Exception as error:
                raise CommandError(
                    "Could not queue notification event "
                    f"{event_id} after queueing {queued_count} event(s)."
                ) from error

            queued_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {queued_count} notification event(s)."
            )
        )
