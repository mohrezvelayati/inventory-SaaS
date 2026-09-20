from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase

from notifications.email import (
    EmailDeliveryError,
    send_sale_completed_email,
)


class SaleCompletedEmailTests(SimpleTestCase):
    def setUp(self):
        self.payload = {
            "sale_id": 42,
            "store_name": "Test Store",
            "total_amount": "5800000",
            "channel_label": "اینستاگرام",
            "completed_at": "2026-09-20T12:30:00+00:00",
        }

    def test_sends_plain_text_sale_email(self):
        sent_count = send_sale_completed_email(
            recipient_email="manager@example.com",
            payload=self.payload,
        )

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]

        self.assertEqual(
            message.subject,
            "فروش جدید ثبت شد",
        )
        self.assertEqual(
            message.to,
            ["manager@example.com"],
        )
        self.assertIn(
            "Test Store",
            message.body,
        )
        self.assertIn(
            "5800000",
            message.body,
        )

    @patch(
        "notifications.email.send_mail",
        return_value=0,
    )
    def test_zero_sent_messages_raises_delivery_error(self, send_mail_mock):
        with self.assertRaises(EmailDeliveryError):
            send_sale_completed_email(
                recipient_email="manager@example.com",
                payload=self.payload,
            )

        send_mail_mock.assert_called_once()
