from django.db import models
from django.contrib.postgres.search import SearchVectorField

from apps.common.fields import GeographyPointField
from apps.common.models import TimestampedModel, UUIDPrimaryKeyModel


class PropertyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    PUBLISHED = "published", "Published"
    UNPUBLISHED = "unpublished", "Unpublished"
    ARCHIVED = "archived", "Archived"


class RoomStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    MAINTENANCE = "maintenance", "Maintenance"
    ARCHIVED = "archived", "Archived"


class MediaOwnerType(models.TextChoices):
    PLATFORM = "platform", "Platform"
    VENDOR = "vendor", "Vendor"
    PROPERTY = "property", "Property"
    ROOM = "room", "Room"
    USER = "user", "User"
    BLOG = "blog", "Blog"
    PAGE = "page", "Page"


class Property(TimestampedModel):
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="properties")
    property_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True)
    property_type = models.CharField(max_length=80, default="hotel")
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country_code = models.CharField(max_length=2)
    location = GeographyPointField()
    timezone = models.CharField(max_length=64, default="UTC")
    currency_code = models.CharField(max_length=3, default="USD")
    base_check_in_minutes = models.IntegerField(default=0)
    base_check_out_minutes = models.IntegerField(default=0)
    minimum_booking_minutes = models.IntegerField(default=120)
    maximum_booking_minutes = models.IntegerField(null=True, blank=True)
    instant_booking_enabled = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=PropertyStatus.choices, default=PropertyStatus.DRAFT)
    star_rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    search_document = SearchVectorField(null=True, blank=True)

    class Meta:
        db_table = "properties"
        indexes = [
            models.Index(fields=["vendor"]),
            models.Index(fields=["status", "city"]),
            models.Index(fields=["featured"]),
        ]


class PropertyAmenity(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    icon_name = models.CharField(max_length=80, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "property_amenities"


class PropertyAmenityMap(models.Model):
    property = models.ForeignKey("properties.Property", on_delete=models.CASCADE)
    amenity = models.ForeignKey("properties.PropertyAmenity", on_delete=models.CASCADE)

    class Meta:
        db_table = "property_amenity_map"
        unique_together = [("property", "amenity")]


class Room(TimestampedModel):
    property = models.ForeignKey("properties.Property", on_delete=models.CASCADE, related_name="rooms")
    room_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True)
    room_code = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    max_adults = models.IntegerField(default=2)
    max_children = models.IntegerField(default=0)
    size_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bed_summary = models.CharField(max_length=120, blank=True)
    bathroom_count = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    floor_label = models.CharField(max_length=40, blank=True)
    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.DRAFT)
    featured = models.BooleanField(default=False)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "rooms"
        indexes = [models.Index(fields=["property"]), models.Index(fields=["status"])]


class RoomAmenity(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    icon_name = models.CharField(max_length=80, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room_amenities"


class RoomAmenityMap(models.Model):
    room = models.ForeignKey("properties.Room", on_delete=models.CASCADE)
    amenity = models.ForeignKey("properties.RoomAmenity", on_delete=models.CASCADE)

    class Meta:
        db_table = "room_amenity_map"
        unique_together = [("room", "amenity")]


class MediaAsset(UUIDPrimaryKeyModel):
    owner_type = models.CharField(max_length=20, choices=MediaOwnerType.choices)
    owner_id = models.UUIDField()
    storage_bucket = models.CharField(max_length=120, blank=True)
    storage_path = models.TextField(blank=True)
    public_url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "media_assets"
        indexes = [models.Index(fields=["owner_type", "owner_id"])]


class RoomRatePlan(TimestampedModel):
    room = models.ForeignKey("properties.Room", on_delete=models.CASCADE, related_name="rate_plans")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    currency_code = models.CharField(max_length=3, default="USD")
    tax_inclusive = models.BooleanField(default=False)
    cancellation_policy = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room_rate_plans"


class RoomHourlyRate(TimestampedModel):
    rate_plan = models.ForeignKey("properties.RoomRatePlan", on_delete=models.CASCADE, related_name="hourly_rates")
    duration_minutes = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    extra_guest_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room_hourly_rates"
        unique_together = [("rate_plan", "duration_minutes")]


class RoomDailyRate(TimestampedModel):
    rate_plan = models.ForeignKey("properties.RoomRatePlan", on_delete=models.CASCADE, related_name="daily_rates")
    weekday = models.SmallIntegerField()
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room_daily_rates"
        unique_together = [("rate_plan", "weekday")]


class PropertyBlackout(UUIDPrimaryKeyModel):
    property = models.ForeignKey("properties.Property", on_delete=models.CASCADE, related_name="blackouts")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "property_blackouts"


class RoomBlackout(UUIDPrimaryKeyModel):
    room = models.ForeignKey("properties.Room", on_delete=models.CASCADE, related_name="blackouts")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "room_blackouts"
