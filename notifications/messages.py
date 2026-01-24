from django.utils.timezone import localdate

from booking.models import Booking
from payment.models import Payment


def generate_booking_creation_message(instance: Booking) -> str:
    message = (
        "🆕 New booking created\n"
        f"User: {instance.user.email}\n"
        f"Room: {instance.room.number}\n"
        f"Check-in: {instance.check_in_date}\n"
        f"Check-out: {instance.check_out_date}\n"
        f"Price per night: {instance.price_per_night}"
    )
    return message


def generate_booking_cancellation_message(instance: Booking) -> str:
    message = (
        "❌ Booking Canceled\n"
        f"User: {instance.user.email}\n"
        f"Room: {instance.room.number}\n"
        f"Dates: {instance.check_in_date} - {instance.check_out_date}"
    )
    return message


def generate_success_payment_message(booking: Booking, payment: Payment) -> str:
    message = (
        f"✅ Payment Successful\n"
        f"Booking ID: {booking.id}\n"
        f"User: {booking.user.email}\n"
        f"Room: {booking.room.number}\n"
        f"Check-in: {booking.check_in_date}\n"
        f"Check-out: {booking.check_out_date}\n"
        f"Amount Paid: ${payment.money_to_pay}"
    )
    return message


def generate_no_show_message(instance: Booking) -> str:
    message = (
        f"⚠️ NO SHOW ALERT ⚠️\n"
        f"\n"
        f"📋 Booking ID: {instance.id}\n"
        f"🚪 Room: {instance.room.number} ({instance.room.type})\n"
        f"👤 Guest: {instance.user.first_name} {instance.user.last_name}\n"
        f"📧 Email: {instance.user.email}\n"
        f"📅 Check-in Date: {instance.check_in_date}\n"
        f"📅 Check-out Date: {instance.check_out_date}\n"
        f"💰 Price per night: ${instance.price_per_night}\n"
        f"📊 Status: {instance.status}\n"
        f"\n"
        f"⏰ Marked at: {localdate()}"
    )
    return message
