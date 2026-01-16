from rest_framework import serializers

from payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "booking",
            "status",
            "type",
            "money_to_pay",
            "session_url",
        )
        read_only_fields = (
            "id",
            "money_to_pay",
            "status",
            "session_url",
            "type"
        )
