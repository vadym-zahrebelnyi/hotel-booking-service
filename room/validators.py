from datetime import date

from rest_framework.exceptions import ValidationError


def validate_date_range_provided(date_from, date_to):
    """
    Validate that both date_from and date_to are provided.
    """
    if not date_from or not date_to:
        raise ValidationError("date_from and date_to are required")


def validate_date_format(date_from, date_to):
    """
    Validate that dates are in valid format.
    """
    if not date_from or not date_to:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD.")


def validate_date_range_order(date_from, date_to):
    """
    Validate that date_from is before date_to.
    """
    if date_from > date_to:
        raise ValidationError("date_from must be before date_to")


def validate_calendar_request(date_from_str, date_to_str, date_from, date_to):
    """
    Comprehensive validation for calendar request.
    """
    validate_date_range_provided(date_from_str, date_to_str)
    validate_date_format(date_from, date_to)
    validate_date_range_order(date_from, date_to)
