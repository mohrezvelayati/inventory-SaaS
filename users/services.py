import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from users.models import PasswordResetChallenge, User
from users.sms import SMSDeliveryError, send_password_reset_code


logger = logging.getLogger(__name__)


class PasswordResetError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def normalize_phone_number(phone_number):
    return phone_number.strip()


def _privacy_hash(value):
    return salted_hmac("inventory-security-identifier", value).hexdigest()


def _otp_hash(phone_number, code):
    return salted_hmac("inventory-password-reset-otp", f"{phone_number}:{code}").hexdigest()


def _blacklist_user_tokens(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def request_password_reset(*, phone_number, requester_ip):
    now = timezone.now()
    phone_number = normalize_phone_number(phone_number)
    phone_hash = _privacy_hash(phone_number)
    ip_hash = _privacy_hash(requester_ip or "unknown")
    hour_ago = now - timedelta(hours=1)

    if PasswordResetChallenge.objects.filter(
        phone_hash=phone_hash,
        created_at__gte=hour_ago,
    ).count() >= 5:
        raise PasswordResetError("rate_limited")
    if PasswordResetChallenge.objects.filter(
        requester_ip_hash=ip_hash,
        created_at__gte=hour_ago,
    ).count() >= 20:
        raise PasswordResetError("rate_limited")

    PasswordResetChallenge.objects.filter(
        phone_hash=phone_hash,
        consumed_at__isnull=True,
    ).update(consumed_at=now)

    user = User.objects.filter(phone_number=phone_number).first()
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = PasswordResetChallenge.objects.create(
        user=user,
        phone_hash=phone_hash,
        requester_ip_hash=ip_hash,
        code_hash=_otp_hash(phone_number, code),
        expires_at=now + timedelta(seconds=settings.PASSWORD_RESET_OTP_TTL_SECONDS),
    )

    if user is None:
        challenge.delivery_status = PasswordResetChallenge.DeliveryStatus.SENT
        challenge.save(update_fields=["delivery_status"])
        return

    try:
        send_password_reset_code(phone_number=phone_number, code=code)
    except SMSDeliveryError:
        challenge.delivery_status = PasswordResetChallenge.DeliveryStatus.FAILED
        challenge.save(update_fields=["delivery_status"])
        logger.error("Password reset SMS delivery failed", extra={"challenge_id": challenge.id})
        return

    challenge.delivery_status = PasswordResetChallenge.DeliveryStatus.SENT
    challenge.save(update_fields=["delivery_status"])


def confirm_password_reset(*, phone_number, code, new_password):
    now = timezone.now()
    phone_number = normalize_phone_number(phone_number)
    phone_hash = _privacy_hash(phone_number)
    error_code = None

    with transaction.atomic():
        challenge = (
            PasswordResetChallenge.objects.select_for_update()
            .filter(phone_hash=phone_hash, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

        if challenge is None or challenge.user is None or challenge.expires_at <= now:
            error_code = "invalid_or_expired"
        elif challenge.attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
            error_code = "too_many_attempts"
        elif not hmac.compare_digest(challenge.code_hash, _otp_hash(phone_number, code)):
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            error_code = (
                "too_many_attempts"
                if challenge.attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS
                else "invalid_or_expired"
            )
        else:
            try:
                validate_password(new_password, user=challenge.user)
            except DjangoValidationError as exc:
                raise ValidationError({"new_password": list(exc.messages)}) from exc

            user = User.objects.select_for_update().get(pk=challenge.user_id)
            user.set_password(new_password)
            user.save(update_fields=["password"])
            challenge.consumed_at = now
            challenge.save(update_fields=["consumed_at"])
            PasswordResetChallenge.objects.filter(
                phone_hash=phone_hash,
                consumed_at__isnull=True,
            ).update(consumed_at=now)
            _blacklist_user_tokens(user)

    if error_code:
        raise PasswordResetError(error_code)


@transaction.atomic
def change_password(*, user, current_password, new_password):
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.check_password(current_password):
        raise ValidationError({"current_password": ["Current password is incorrect."]})
    try:
        validate_password(new_password, user=locked_user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": list(exc.messages)}) from exc
    locked_user.set_password(new_password)
    locked_user.save(update_fields=["password"])
    _blacklist_user_tokens(locked_user)
