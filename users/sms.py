import json
from urllib import error, parse, request

from django.conf import settings


class SMSDeliveryError(Exception):
    pass


fake_outbox = []


def send_password_reset_code(*, phone_number, code):
    backend = settings.SMS_BACKEND
    if backend == "fake":
        fake_outbox.append({"phone_number": phone_number, "code": code})
        return
    if backend == "disabled":
        raise SMSDeliveryError("SMS delivery is disabled")
    if backend != "kavenegar":
        raise SMSDeliveryError("Unknown SMS backend")
    if not settings.KAVENEGAR_API_KEY:
        raise SMSDeliveryError("Kavenegar is not configured")

    endpoint = (
        "https://api.kavenegar.com/v1/"
        f"{settings.KAVENEGAR_API_KEY}/verify/lookup.json"
    )
    payload = parse.urlencode(
        {
            "receptor": phone_number,
            "token": code,
            "template": settings.KAVENEGAR_TEMPLATE,
        }
    ).encode()

    try:
        with request.urlopen(endpoint, data=payload, timeout=10) as response:
            response_data = json.loads(response.read().decode())
    except (error.URLError, TimeoutError, ValueError) as exc:
        raise SMSDeliveryError("SMS provider request failed") from exc

    if response_data.get("return", {}).get("status") != 200:
        raise SMSDeliveryError("SMS provider rejected the request")
