from rest_framework import serializers

from apps.payments.models import Payment, Refund


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "amount", "reason", "provider_reference", "refunded_at", "created_at"]
        read_only_fields = ["created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "booking",
            "payer_user",
            "provider",
            "provider_reference",
            "status",
            "amount",
            "currency_code",
            "paid_at",
            "failure_reason",
            "metadata",
            "refunds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
