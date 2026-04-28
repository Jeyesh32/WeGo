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


# ---------------------------------------------------------------------------
# Core Property
# ---------------------------------------------------------------------------

class Property(TimestampedModel):
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="properties", null=True, blank=True)
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


# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Rate Plans
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Blackouts
# ---------------------------------------------------------------------------

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


# ===========================================================================
# HOTEL CONTENT MODELS  (sourced from external provider API / Agoda data)
# All models below are linked to Property via FK.
# ===========================================================================

# ---------------------------------------------------------------------------
# Images  (contentImages.hotelImages)
# ---------------------------------------------------------------------------

class HotelImage(UUIDPrimaryKeyModel):
    """
    Represents a single image entry from the provider's hotelImages list.

    JSON path: contentDetail.contentImages.hotelImages[]
    Fields captured: caption, group, groupId, groupEntityId, id (provider image id),
                     providerId, typeId, uploadedDate, highResolutionSizes
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="hotel_images",
    )
    # Provider-assigned numeric image id (not our PK)
    provider_image_id = models.BigIntegerField(db_index=True, default=0)
    caption = models.CharField(max_length=255, blank=True)
    # e.g. "property", "room", "dining", "facility", "nearby"
    group_id = models.CharField(max_length=80, blank=True)
    # Display label e.g. "Property views", "Rooms", "Facilities"
    group = models.CharField(max_length=120, blank=True)
    # Optional numeric FK within the group (e.g. facility entity id)
    group_entity_id = models.IntegerField(null=True, blank=True)
    # Numeric id of the OTA/provider who submitted the image, e.g. 332, 3038
    provider_id = models.IntegerField(null=True, blank=True)
    # Internal type classification, e.g. 5 (property), 7 (room)
    type_id = models.IntegerField(null=True, blank=True)
    uploaded_date = models.DateTimeField(null=True, blank=True)
    # Comma-separated list of sizes that are high-res, e.g. "main"
    high_resolution_sizes = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hotel_images"
        indexes = [
            models.Index(fields=["property"]),
            models.Index(fields=["group_id"]),
        ]

    def __str__(self):
        return f"{self.property_id} | {self.group} | {self.caption}"


class HotelImageUrl(UUIDPrimaryKeyModel):
    """
    Each image can have multiple sized URLs (main, gallery_preview, thumbnail, thumbnail-2x).

    JSON path: contentDetail.contentImages.hotelImages[].urls[]
    """
    image = models.ForeignKey(
        "properties.HotelImage",
        on_delete=models.CASCADE,
        related_name="urls",
    )
    # e.g. "main", "gallery_preview", "thumbnail", "thumbnail-2x"
    size_key = models.CharField(max_length=40)
    url = models.TextField()

    class Meta:
        db_table = "hotel_image_urls"
        unique_together = [("image", "size_key")]


# ---------------------------------------------------------------------------
# Videos  (contentImages.videos)
# ---------------------------------------------------------------------------

class HotelVideo(UUIDPrimaryKeyModel):
    """
    Property-level video (HLS stream or direct URL).

    JSON path: contentDetail.contentImages.videos[]
    Fields: id, location, generated_type
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="hotel_videos",
    )
    provider_video_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    # HLS playlist URL or direct mp4 link
    location = models.TextField()
    # e.g. null, "ai_generated"
    generated_type = models.CharField(max_length=60, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hotel_videos"
        indexes = [models.Index(fields=["property"])]


# ---------------------------------------------------------------------------
# Review Snippets  (contentReviewSummaries.snippets)
# ---------------------------------------------------------------------------

class HotelReviewSnippet(UUIDPrimaryKeyModel):
    """
    Individual guest review snippet displayed on the property page.

    JSON path: contentDetail.contentReviewSummaries.snippets[]
    Fields: countryCode, countryName, date, demographicId, demographicName,
            reviewer, reviewRating, snippet
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="review_snippets",
    )
    # Large numeric id assigned by the provider
    snippet_id = models.CharField(max_length=40, blank=True)
    country_code = models.CharField(max_length=4, blank=True)
    country_name = models.CharField(max_length=120, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # 1=Business, 2=Couple, 3=Solo, 4=Family w/ young children, 6=Group
    demographic_id = models.SmallIntegerField(null=True, blank=True)
    demographic_name = models.CharField(max_length=80, blank=True)
    reviewer = models.CharField(max_length=120, blank=True)
    # Score out of 10 (can be decimal e.g. 9.2)
    review_rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    snippet = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hotel_review_snippets"
        indexes = [
            models.Index(fields=["property"]),
            models.Index(fields=["reviewed_at"]),
        ]


# ---------------------------------------------------------------------------
# Review Scores  (contentReviewScore)
# ---------------------------------------------------------------------------

class HotelReviewScore(UUIDPrimaryKeyModel):
    """
    Combined / per-provider review score summary.

    JSON path: contentDetail.contentReviewScore
    combinedReviewScore.cumulative → is_combined=True, provider_id=None
    providerReviewScore[]          → is_combined=False, provider_id=<id>

    Fields: score, max_score, review_count, is_default, trending_past_14_days,
            trending_past_30_days
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="review_scores",
    )
    # True = the combined score; False = per-provider score
    is_combined = models.BooleanField(default=False)
    # Null for the combined score row
    provider_id = models.IntegerField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=4, decimal_places=2, default=10)
    review_count = models.IntegerField(default=0)
    trending_past_14_days = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    trending_past_30_days = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hotel_review_scores"
        indexes = [models.Index(fields=["property"])]


class HotelReviewScoreDistribution(UUIDPrimaryKeyModel):
    """
    Breakdown of review counts by score tier for a given HotelReviewScore.

    JSON path: providerReviewScore[].demographics.allGuest.scoreDistribution[]
    Fields: id (e.g. "exceptional"), review_count
    """
    review_score = models.ForeignKey(
        "properties.HotelReviewScore",
        on_delete=models.CASCADE,
        related_name="score_distributions",
    )
    # "exceptional", "excellent", "very_good", "good", "below_expectation"
    tier_id = models.CharField(max_length=40)
    review_count = models.IntegerField(default=0)

    class Meta:
        db_table = "hotel_review_score_distributions"
        unique_together = [("review_score", "tier_id")]


class HotelReviewGrade(UUIDPrimaryKeyModel):
    """
    Category-level sub-scores within a review demographic group.

    JSON path: providerReviewScore[].demographics.allGuest.grades[]
    Examples: overall, cleanliness, facilities, location, roomComfort,
              staffPerformance, valueForMoney
    """
    review_score = models.ForeignKey(
        "properties.HotelReviewScore",
        on_delete=models.CASCADE,
        related_name="grades",
    )
    # Identifier e.g. "overall", "cleanliness", "location"
    grade_id = models.CharField(max_length=60)
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    city_average = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "hotel_review_grades"
        unique_together = [("review_score", "grade_id")]


# ---------------------------------------------------------------------------
# Recommendation Score  (contentReviewSummaries.recommendationScores)
# ---------------------------------------------------------------------------

class HotelRecommendationScore(UUIDPrimaryKeyModel):
    """
    Frequent-traveller recommendation score.

    JSON path: contentDetail.contentReviewSummaries.recommendationScores
    Fields: frequentTravellerRecommendationScore, recommendationScore
    """
    property = models.OneToOneField(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="recommendation_score",
    )
    frequent_traveller_score = models.IntegerField(null=True, blank=True)
    general_score = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hotel_recommendation_scores"


# ---------------------------------------------------------------------------
# Positive Mentions  (contentReviewSummaries.positiveMentions.facilityClassesSentiment)
# ---------------------------------------------------------------------------

class HotelPositiveMention(UUIDPrimaryKeyModel):
    """
    Facility categories most positively mentioned by reviewers.

    JSON path: contentDetail.contentReviewSummaries.positiveMentions.facilityClassesSentiment[]
    Fields: id, name, noOfPositiveMentioned, facilityIds
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="positive_mentions",
    )
    # Numeric class id, e.g. 2 = Breakfast, 25 = Housekeeping
    facility_class_id = models.IntegerField()
    name = models.CharField(max_length=120)
    no_of_positive_mentioned = models.IntegerField(default=0)
    # JSON array of individual facility ids, e.g. [351, 352, 353]
    facility_ids = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "hotel_positive_mentions"
        unique_together = [("property", "facility_class_id")]
        indexes = [models.Index(fields=["property"])]


# ---------------------------------------------------------------------------
# Favorite / Highlight Features  (contentHighlights.favoriteFeatures)
# ---------------------------------------------------------------------------

class HotelFavoriteFeature(UUIDPrimaryKeyModel):
    """
    Key selling-point features shown prominently on the property page.

    JSON path: contentDetail.contentHighlights.favoriteFeatures[]
    Fields: id, category, name, symbol, tooltip
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="favorite_features",
    )
    # Provider-assigned numeric feature id
    feature_id = models.IntegerField()
    # e.g. "transportation", "property-facility", "tourist-area"
    category = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=255)
    # Icon / symbol identifier e.g. "train-new", "free-wifi-in-all-rooms"
    symbol = models.CharField(max_length=120, blank=True)
    tooltip = models.TextField(blank=True, null=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "hotel_favorite_features"
        indexes = [models.Index(fields=["property"])]


# ---------------------------------------------------------------------------
# Location Highlights  (contentHighlights.locationHighlights & locations)
# ---------------------------------------------------------------------------

class HotelLocationHighlight(UUIDPrimaryKeyModel):
    """
    Notable nearby location tags (city-center distance, beach, financial center, etc.).

    JSON path: contentDetail.contentHighlights.locationHighlights[]
              and contentHighlights.locations[]
    Fields: name, symbol, tooltip, distanceKm, highlightType, message
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="location_highlights",
    )
    name = models.CharField(max_length=255)
    # Icon/symbol e.g. "train-new", "pin-beach", "pin-heart-of-the-city"
    symbol = models.CharField(max_length=120, blank=True)
    tooltip = models.TextField(blank=True, null=True)
    # e.g. "city-center" — only populated for locationHighlights entries
    highlight_type = models.CharField(max_length=80, blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        db_table = "hotel_location_highlights"
        indexes = [models.Index(fields=["property"])]


# ---------------------------------------------------------------------------
# ATF Property Highlights  (contentHighlights.atfPropertyHighlights)
# ---------------------------------------------------------------------------

class HotelAtfHighlight(UUIDPrimaryKeyModel):
    """
    Above-the-fold badge highlights shown on the property detail page.

    JSON path: contentDetail.contentHighlights.atfPropertyHighlights[]
    Fields: name, symbol, category, topicName, tooltip
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="atf_highlights",
    )
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=120, blank=True)
    # e.g. "topic-highlight"
    category = models.CharField(max_length=80, blank=True)
    # e.g. "Business Travelers", "Location", "Check-in/Out"
    topic_name = models.CharField(max_length=120, blank=True)
    tooltip = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "hotel_atf_highlights"
        indexes = [models.Index(fields=["property"])]


# ---------------------------------------------------------------------------
# Nearby Places  (contentLocalInformation.nearbyProperties)
# ---------------------------------------------------------------------------

class HotelNearbyPlaceCategory(UUIDPrimaryKeyModel):
    """
    Category grouping for nearby places (Airports, Public transportation, Attractions, etc.).

    JSON path: contentDetail.contentLocalInformation.nearbyProperties[]
    Fields: id, categoryName, categorySymbol
    """
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="nearby_place_categories",
    )
    # e.g. "airport", "transportation", "attraction"
    category_key = models.CharField(max_length=80)
    category_name = models.CharField(max_length=120)
    category_symbol = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "hotel_nearby_place_categories"
        unique_together = [("property", "category_key")]


class HotelNearbyPlace(UUIDPrimaryKeyModel):
    """
    Individual POI/landmark near the property.

    JSON path: contentDetail.contentLocalInformation.nearbyProperties[].places[]
    Fields: name, abbr, distanceInKm, duration, durationIcon, latitude, longitude,
            landmarkId, typeId, typeName
    """
    category = models.ForeignKey(
        "properties.HotelNearbyPlaceCategory",
        on_delete=models.CASCADE,
        related_name="places",
    )
    name = models.CharField(max_length=255)
    # e.g. "MAA", "TIR" for airports
    abbr = models.CharField(max_length=20, blank=True, null=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    # Travel duration in seconds (taxi / transit)
    duration_seconds = models.IntegerField(null=True, blank=True)
    # Icon key for the transport mode e.g. "taxi-service"
    duration_icon = models.CharField(max_length=80, blank=True, null=True)
    latitude = models.DecimalField(max_digits=18, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=10, null=True, blank=True)
    landmark_id = models.IntegerField(null=True, blank=True)
    type_id = models.IntegerField(null=True, blank=True)
    type_name = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        db_table = "hotel_nearby_places"
        indexes = [models.Index(fields=["category"])]
