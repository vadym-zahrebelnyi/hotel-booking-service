import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from booking.models import Booking
from payment.models import Payment
from payment.serializers import PaymentSerializer
from payment.services.payment_service import renew_payment_session

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all().order_by("-id")
    serializer_class = PaymentSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhook(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        event = None
        payment = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if event["type"] != "checkout.session.completed":
            return Response(status=status.HTTP_200_OK)
        elif event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session["id"]

            try:
                payment = Payment.objects.get(session_id=session_id)
            except Payment.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if payment.status != Payment.PaymentStatus.PAID:
            payment.status = Payment.PaymentStatus.PAID
            payment.save(update_fields=["status"])

        booking = payment.booking
        if payment.type == Payment.PaymentType.CANCELLATION_FEE:
            booking.status = Booking.BookingStatus.CANCELLED
            booking.save(update_fields=["status"])
        if booking.status in (
            Booking.BookingStatus.BOOKED,
            Booking.BookingStatus.NO_SHOW,
        ):
            booking.status = Booking.BookingStatus.ACTIVE
            booking.save(update_fields=["status"])
        elif booking.status == Booking.BookingStatus.ACTIVE:
            booking.status = Booking.BookingStatus.COMPLETED
            today = timezone.localdate()
            booking.actual_check_out_date = today
            booking.save(update_fields=["status", "actual_check_out_date"])

        return Response(status=status.HTTP_200_OK)


class PaymentSuccessView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.filter(session_id=session_id).first()
        if not payment:
            return Response(
                {"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "detail": "Thank you for your payment! Your booking is being processed.",
                "payment_status": payment.status,
                "booking_id": payment.booking.id,
            },
            status=status.HTTP_200_OK,
        )


class PaymentCancelView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"detail": "Payment was cancelled. You can complete it later."},
            status=status.HTTP_200_OK,
        )


class PaymentRenewView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            payment = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = renew_payment_session(payment)
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
