from decimal import Decimal

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def to_cents(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("0.01")) * 100)


def create_checkout_session(amount, name):
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": name,
                    },
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }
        ],
        success_url="https://localhost:8000/api/payments/success/",
        cancel_url="https://localhost:8000/api/payments/cancel/",
    )

    return session
