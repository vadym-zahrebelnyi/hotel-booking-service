import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from payment.models import Payment
from booking.models import Booking
from payment.stripe_helper import create_checkout_session

stripe.api_key = settings.STRIPE_SECRET_KEY


class TestStripeSessionView(APIView):
    def post(self, request):
        booking = Booking.objects.first()  # тимчасово

        payment = Payment.objects.create(
            booking=booking,
            type=Payment.PaymentType.BOOKING,
            money_to_pay=booking.price_per_night
        )

        session_url = create_checkout_session(
            payment,
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel",
        )

        return Response({
            "session_url": session_url
        })
