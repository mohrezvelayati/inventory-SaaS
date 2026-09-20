from decimal import Decimal

from django.db import transaction
from django.test import TestCase

from notifications.models import NotificationEvent
from notifications.services import create_sale_completed_event
from sales.models import Sale
from sales.services import complete_sale
from tests.factories import (
    create_product,
    create_sale,
    create_sale_item,
    create_store,
    create_user,
    create_variant,
)


class SaleNotificationOutboxTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(self.user)

        product = create_product(self.store)
        self.variant = create_variant(
            product,
            current_stock=2,
            sale_price=Decimal("1000"),
        )
        self.sale = create_sale(
            self.store,
            self.membership,
            total_amount=Decimal("1000"),
        )
        create_sale_item(
            self.sale,
            self.variant,
            quantity=1,
            final_price=Decimal("1000"),
        )

    def test_completing_sale_creates_pending_notification_event(self):
        complete_sale(
            sale=self.sale,
            user=self.user,
        )

        self.sale.refresh_from_db()

        event = NotificationEvent.objects.get(
            sale=self.sale,
            event_type=NotificationEvent.EventType.SALE_COMPLETED,
        )

        self.assertEqual(
            event.status,
            NotificationEvent.Status.PENDING,
        )
        self.assertEqual(
            event.payload["sale_id"],
            self.sale.id,
        )
        self.assertEqual(
            event.payload["store_id"],
            self.store.id,
        )
        self.assertEqual(
            event.payload["total_amount"],
            "1000",
        )
        self.assertEqual(
            event.payload["completed_at"],
            self.sale.completed_at.isoformat(),
        )

    def test_sale_completed_event_creation_is_idempotent(self):
        complete_sale(
            sale=self.sale,
            user=self.user,
        )
        self.sale.refresh_from_db()

        first_event = NotificationEvent.objects.get(
            sale=self.sale,
        )
        second_event = create_sale_completed_event(
            sale=self.sale,
        )

        self.assertEqual(
            first_event.id,
            second_event.id,
        )
        self.assertEqual(
            NotificationEvent.objects.filter(
                sale=self.sale,
            ).count(),
            1,
        )

    def test_sale_and_notification_event_roll_back_together(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                complete_sale(
                    sale=self.sale,
                    user=self.user,
                )
                raise RuntimeError("Force outer rollback.")

        self.sale.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(
            self.sale.status,
            Sale.StatusChoices.DRAFT,
        )
        self.assertIsNone(self.sale.completed_at)
        self.assertEqual(
            self.variant.current_stock,
            2,
        )
        self.assertFalse(
            NotificationEvent.objects.filter(
                sale=self.sale,
            ).exists()
        )
