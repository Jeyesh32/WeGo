from rest_framework import serializers

from apps.properties.models import Property, Room, RoomHourlyRate, RoomRatePlan


class RoomHourlyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomHourlyRate
        fields = ["id", "duration_minutes", "price", "compare_at_price", "extra_guest_price", "is_active"]


class RoomRatePlanSerializer(serializers.ModelSerializer):
    hourly_rates = RoomHourlyRateSerializer(many=True, read_only=True)

    class Meta:
        model = RoomRatePlan
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "currency_code",
            "tax_inclusive",
            "cancellation_policy",
            "is_active",
            "hourly_rates",
        ]


class RoomSerializer(serializers.ModelSerializer):
    rate_plans = RoomRatePlanSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "property",
            "room_name",
            "slug",
            "description",
            "max_adults",
            "max_children",
            "size_sqft",
            "bed_summary",
            "bathroom_count",
            "floor_label",
            "quantity",
            "status",
            "featured",
            "rating_avg",
            "rating_count",
            "metadata",
            "rate_plans",
        ]


class PropertySerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "vendor",
            "property_name",
            "slug",
            "property_type",
            "short_description",
            "description",
            "address_line_1",
            "address_line_2",
            "landmark",
            "city",
            "state",
            "postal_code",
            "country_code",
            "location",
            "timezone",
            "currency_code",
            "minimum_booking_minutes",
            "maximum_booking_minutes",
            "instant_booking_enabled",
            "featured",
            "status",
            "star_rating",
            "rating_avg",
            "rating_count",
            "seo_title",
            "seo_description",
            "metadata",
            "rooms",
        ]
