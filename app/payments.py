"""Payment provider interface.

The MVP ships a simulated M-Pesa provider so the full booking-to-payment flow
can be demoed without Safaricom credentials. To go live, implement
`DarajaMpesa.request_payment` with the Daraja STK Push API and set
PAYMENT_PROVIDER=daraja. Nothing else in the app needs to change.
"""
import re
import secrets
from dataclasses import dataclass


@dataclass
class PaymentRequest:
    ok: bool
    reference: str | None
    message: str


class SimulatedMpesa:
    name = "simulated"

    def request_payment(self, phone: str, amount: int, account_ref: str) -> PaymentRequest:
        ref = "SIM" + secrets.token_hex(4).upper()
        return PaymentRequest(
            ok=True,
            reference=ref,
            message=f"Demo mode: a KES {amount:,} M-Pesa prompt would be sent to {phone}.",
        )


class DarajaMpesa:
    name = "daraja"

    def __init__(self, consumer_key: str, consumer_secret: str, shortcode: str, passkey: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.passkey = passkey

    def request_payment(self, phone: str, amount: int, account_ref: str) -> PaymentRequest:
        # 1. GET an OAuth token, 2. POST /mpesa/stkpush/v1/processrequest,
        # 3. handle the result on a callback route and mark the booking paid.
        raise NotImplementedError("Connect Daraja credentials to enable live payments.")


def get_provider(config) -> SimulatedMpesa | DarajaMpesa:
    if config.get("PAYMENT_PROVIDER") == "daraja":
        return DarajaMpesa(
            config["MPESA_CONSUMER_KEY"], config["MPESA_CONSUMER_SECRET"],
            config["MPESA_SHORTCODE"], config["MPESA_PASSKEY"],
        )
    return SimulatedMpesa()


def normalize_phone(raw: str) -> str | None:
    """Return a phone number in international digits-only form, or None.

    Kenyan numbers (07.., 01.., 7.., +254..) become 2547XXXXXXXX / 2541XXXXXXXX,
    which is the format M-Pesa expects. Other international numbers written
    with a leading + are kept as digits.
    """
    if not raw:
        return None
    has_plus = raw.strip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if re.fullmatch(r"0[17]\d{8}", digits):
        return "254" + digits[1:]
    if re.fullmatch(r"[17]\d{8}", digits):
        return "254" + digits
    if re.fullmatch(r"254[17]\d{8}", digits):
        return digits
    if has_plus and 8 <= len(digits) <= 15:
        return digits
    return None
