class PendingPaymentExists(Exception):
    """Thrown when there is already a PENDING payment for the booking"""

    def __init__(
        self, booking_id: int | None = None, message: str | None = None
    ) -> None:
        if message is None:
            message = (
                f"Pending payment already exists for booking {booking_id}"
                if booking_id
                else "Pending payment already exists."
            )
        super().__init__(message)
        self.booking_id = booking_id
