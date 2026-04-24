from rest_framework import serializers

from apps.bookings.models import Booking, BookingGuest


class BookingGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingGuest
        fields = ["id", "full_name", "email", "phone", "is_primary"]


class BookingSerializer(serializers.ModelSerializer):
    guests = BookingGuestSerializer(many=True, required=False)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "customer_user",
            "vendor",
            "property",
            "room",
            "rate_plan",
            "hourly_rate",
            "staff",
            "status",
            "source_channel",
            "starts_at",
            "ends_at",
            "adult_count",
            "child_count",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "service_fee_amount",
            "total_amount",
            "currency_code",
            "special_requests",
            "cancellation_reason",
            "cancelled_at",
            "confirmed_at",
            "checked_in_at",
            "checked_out_at",
            "completed_at",
            "metadata",
            "guests",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        guests_data = validated_data.pop("guests", [])
        booking = Booking.objects.create(**validated_data)
        for guest in guests_data:
            BookingGuest.objects.create(booking=booking, **guest)
        return booking
