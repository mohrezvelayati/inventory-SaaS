from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail


class EmailDeliveryError(RuntimeError):
    pass


def send_sale_completed_email(*, recipient_email, payload):
    message = (
        f"فروش جدید در {payload['store_name']}\n\n"
        f"شماره فروش: {payload['sale_id']}\n"
        f"مبلغ: {payload['total_amount']}\n"
        f"کانال فروش: {payload['channel_label']}\n"
        f"زمان تکمیل: {payload['completed_at']}\n"
    )

    try:
        sent_count = send_mail(
            subject="فروش جدید ثبت شد",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except (SMTPException, OSError) as error:
        raise EmailDeliveryError(
            "Temporary email delivery failure."
        ) from error

    if sent_count != 1:
        raise EmailDeliveryError(
            "The email backend did not send the message."
        )

    return sent_count
