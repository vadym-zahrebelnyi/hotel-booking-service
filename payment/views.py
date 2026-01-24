"""
Payment views module.

This module contains API views responsible for:
- listing payments,
- handling Stripe webhook events,
- processing successful and cancelled payments,
- renewing expired Stripe payment sessions.

Stripe is used as a payment provider.
"""

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
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


@extend_schema(
    summary="List payments",
    description="Retrieve a list of all payments ordered by newest first.",
    responses={200: PaymentSerializer(many=True)},
)
class PaymentListView(generics.ListAPIView):
    """
    API view for retrieving a list of all payments.

    Requires authentication via JWT.
    Returns payments ordered by descending ID.
    """

    queryset = Payment.objects.all().order_by("-id")
    serializer_class = PaymentSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(
    summary="Stripe webhook endpoint",
    description=(
        "Receives webhook events from Stripe and processes "
        "`checkout.session.completed` events."
    ),
    request=None,
    responses={
        200: OpenApiResponse(description="Event processed successfully"),
        400: OpenApiResponse(description="Invalid Stripe signature or request"),
        401: OpenApiResponse(description="Stripe authentication error"),
        502: OpenApiResponse(description="Stripe service error"),
    },
)
class StripeWebhook(APIView):
    """
    Stripe webhook endpoint.

    Receives and processes webhook events sent by Stripe.
    Validates the event signature and handles successful
    checkout session completion.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        """
        Handle Stripe webhook POST requests.

        Verifies the Stripe webhook signature, processes the
        `checkout.session.completed` event, updates the payment
        status, and updates the related booking status.
        """

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        event = None
        payment = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError:
            return Response(
                {"detail": "Invalid Stripe signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.AuthenticationError as e:
            return Response(
                {"detail": "Stripe authentication failed", "error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except stripe.error.InvalidRequestError as e:
            return Response(
                {"detail": "Invalid Stripe request", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.StripeError as e:
            return Response(
                {"detail": "Stripe service error", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if event["type"] == "checkout.session.completed":
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
    """
    API view for handling successful payment redirects.

    Used after Stripe checkout to confirm payment status
    and return booking-related information.
    """

    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Payment success callback",
        description="Returns payment and booking information after successful Stripe checkout.",
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Stripe checkout session ID",
                required=True,
            )
        ],
        responses={
            200: OpenApiResponse(description="Payment confirmed"),
            400: OpenApiResponse(description="Missing session_id"),
            404: OpenApiResponse(description="Payment not found"),
        },
    )
    def get(self, request):
        """
        Retrieve payment status using a Stripe session ID.

        Query Parameters:
            session_id (str): Stripe checkout session ID.

        Returns:
            Response: Payment status and booking ID.
        """

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
    """
    API view for handling cancelled payment redirects.

    Returned when a user cancels Stripe checkout.
    """

    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Payment cancelled",
        description="Returned when a Stripe payment is cancelled by the user.",
        responses={200: OpenApiResponse(description="Payment cancelled")},
    )
    def get(self, request):
        """
        Return a message indicating that the payment was cancelled.

        Returns:
            Response: Cancellation confirmation message.
        """

        return Response(
            {"detail": "Payment was cancelled. You can complete it later."},
            status=status.HTTP_200_OK,
        )


class PaymentRenewView(APIView):
    """
    API view for renewing an existing payment session.

    Creates a new Stripe checkout session if the previous one expired.
    """

    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Renew payment session",
        description="Creates a new Stripe checkout session for an existing payment.",
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(description="Invalid payment state"),
            404: OpenApiResponse(description="Payment not found"),
        },
    )
    def post(self, request, pk):
        """
        Renew a Stripe payment session for an existing payment.

        Args:
            pk (int): Payment primary key.

        Returns:
            Response: Updated payment data or error message.
        """

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
