"""
Management command: import_hotels_from_mongo
============================================
Imports hotel content from MongoDB (Agoda.hotels) into the Django
properties models.

Usage
-----
    python manage.py import_hotels_from_mongo
    python manage.py import_hotels_from_mongo --host localhost --port 27017
    python manage.py import_hotels_from_mongo --limit 10         # test with 10 docs
    python manage.py import_hotels_from_mongo --property-id 293006
    python manage.py import_hotels_from_mongo --clear            # wipe content tables first

Requirements
------------
    pip install pymongo

Data path in each MongoDB document
-----------------------------------
    doc["data"]["propertyDetailsSearch"]["propertyDetails"][0]
        └── propertyId
        └── contentDetail
                ├── contentImages
                │       ├── hotelImages[]
                │       │       └── urls[]
                │       └── videos[]
                ├── contentReviewSummaries
                │       ├── snippets[]
                │       ├── recommendationScores
                │       └── positiveMentions.facilityClassesSentiment[]
                ├── contentReviewScore
                │       ├── combinedReviewScore.cumulative
                │       └── providerReviewScore[]
                │               └── demographics.allGuest
                │                       ├── scoreDistribution[]
                │                       └── grades[]
                └── contentSummary
                        ├── displayName / propertyType / rating
                        ├── address  (address1, address2, countryCode, postalCode, city, area)
                        ├── geoInfo  (latitude, longitude)
                        └── isLuxuryHotel
                └── contentHighlights
                        ├── favoriteFeatures[]
                        ├── locationHighlights[]
                        ├── locations[]
                        └── atfPropertyHighlights[]
                └── contentLocalInformation
                        └── nearbyProperties[]
                                └── places[]
"""

import logging
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_str(val, max_len=None):
    """Return a clean string; truncate if max_len is given."""
    if val is None:
        return ""
    s = str(val).strip()
    if max_len:
        s = s[:max_len]
    return s


def _safe_decimal(val, default=None):
    """Coerce to float or return default."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    """Coerce to int or return default."""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_dt(val):
    """
    Parse an ISO-8601 datetime string that may include a UTC-offset suffix,
    e.g. "2018-11-21T18:28:00.000+07:00". Returns an aware datetime in UTC,
    or None on failure.
    """
    if not val:
        return None
    # Python 3.11+ handles %z with colon; for older versions strip the colon.
    try:
        # Try fromisoformat (Python 3.7+ but limited)
        # Strip fractional seconds beyond 6 digits if present
        s = str(val)
        # Normalise "+07:00" style offset (remove colon for strptime compat)
        if len(s) > 6 and s[-3] == ":" and s[-6] in ("+", "-"):
            s = s[:-3] + s[-2:]  # "...+0700"
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.astimezone(dt_timezone.utc)
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _make_slug(name, suffix=""):
    """Generate a unique-ish slug from a property name + optional suffix."""
    base = slugify(name)[:180]
    if suffix:
        return f"{base}-{suffix}"[:220]
    return base[:220]


# ---------------------------------------------------------------------------
# Per-section importers
# ---------------------------------------------------------------------------

def _import_images(property_obj, content_images, stats):
    """Import hotelImages and their URL variants."""
    from apps.properties.models import HotelImage, HotelImageUrl
    import uuid

    hotel_images = (content_images or {}).get("hotelImages") or []
    hi_instances = []
    url_instances = []

    for sort_idx, img in enumerate(hotel_images):
        uid = uuid.uuid4()
        hi_instances.append(HotelImage(
            id=uid,
            property=property_obj,
            provider_image_id=_safe_int(img.get("id"), default=0),
            caption=_safe_str(img.get("caption"), 255),
            group_id=_safe_str(img.get("groupId"), 80),
            group=_safe_str(img.get("group"), 120),
            group_entity_id=_safe_int(img.get("groupEntityId")),
            provider_id=_safe_int(img.get("providerId")),
            type_id=_safe_int(img.get("typeId")),
            uploaded_date=_parse_dt(img.get("uploadedDate")),
            high_resolution_sizes=",".join(img.get("highResolutionSizes") or []),
            sort_order=sort_idx,
        ))
        stats["images"] += 1

        for url_entry in (img.get("urls") or []):
            url_instances.append(HotelImageUrl(
                image_id=uid,
                size_key=_safe_str(url_entry.get("key"), 40),
                url=_safe_str(url_entry.get("value")),
            ))
            stats["image_urls"] += 1

    if hi_instances:
        HotelImage.objects.bulk_create(hi_instances, batch_size=500)
    if url_instances:
        HotelImageUrl.objects.bulk_create(url_instances, batch_size=500)


def _import_videos(property_obj, content_images, stats):
    """Import video HLS stream records."""
    from apps.properties.models import HotelVideo

    videos = (content_images or {}).get("videos") or []
    vid_instances = []

    for vid in videos:
        location = _safe_str(vid.get("location"))
        if not location:
            continue
        vid_instances.append(HotelVideo(
            property=property_obj,
            provider_video_id=_safe_int(vid.get("id")),
            location=location,
            generated_type=_safe_str(vid.get("generated_type"), 60) or None,
        ))
        stats["videos"] += 1

    if vid_instances:
        HotelVideo.objects.bulk_create(vid_instances, batch_size=500)


def _import_review_snippets(property_obj, review_summaries, stats):
    """Import guest review snippet cards."""
    from apps.properties.models import HotelReviewSnippet
    import uuid

    snippets = (review_summaries or {}).get("snippets") or []
    snip_instances = []

    for snip in snippets:
        # snippetId is a nested {"$numberLong": "..."} object in Mongo docs
        raw_sid = snip.get("snippetId") or {}
        if isinstance(raw_sid, dict):
            snippet_id = _safe_str(raw_sid.get("$numberLong"), 40)
        else:
            snippet_id = _safe_str(raw_sid, 40)

        snip_instances.append(HotelReviewSnippet(
            id=uuid.uuid4(),
            property=property_obj,
            snippet_id=snippet_id,
            country_code=_safe_str(snip.get("countryCode"), 4),
            country_name=_safe_str(snip.get("countryName"), 120),
            reviewed_at=_parse_dt(snip.get("date")),
            demographic_id=_safe_int(snip.get("demographicId")),
            demographic_name=_safe_str(snip.get("demographicName"), 80),
            reviewer=_safe_str(snip.get("reviewer"), 120),
            review_rating=_safe_decimal(snip.get("reviewRating")),
            snippet=_safe_str(snip.get("snippet")),
        ))
        stats["review_snippets"] += 1
        
    if snip_instances:
        HotelReviewSnippet.objects.bulk_create(snip_instances, batch_size=500)


def _import_recommendation_score(property_obj, review_summaries, stats):
    """Import frequentTravellerRecommendationScore."""
    from apps.properties.models import HotelRecommendationScore

    rec = (review_summaries or {}).get("recommendationScores") or {}

    HotelRecommendationScore.objects.update_or_create(
        property=property_obj,
        defaults=dict(
            frequent_traveller_score=_safe_int(rec.get("frequentTravellerRecommendationScore")),
            general_score=_safe_int(rec.get("recommendationScore")),
        ),
    )
    stats["recommendation_scores"] += 1


def _import_positive_mentions(property_obj, review_summaries, stats):
    """Import facilityClassesSentiment positive mentions."""
    from apps.properties.models import HotelPositiveMention

    sentiments = (
        ((review_summaries or {}).get("positiveMentions") or {}).get("facilityClassesSentiment") or []
    )

    for item in sentiments:
        HotelPositiveMention.objects.update_or_create(
            property=property_obj,
            facility_class_id=_safe_int(item.get("id"), 0),
            defaults=dict(
                name=_safe_str(item.get("name"), 120),
                no_of_positive_mentioned=_safe_int(item.get("noOfPositiveMentioned"), 0),
                facility_ids=item.get("facilityIds") or [],
            ),
        )
        stats["positive_mentions"] += 1


def _import_review_scores(property_obj, content_review_score, stats):
    from apps.properties.models import (
        HotelReviewScore,
        HotelReviewScoreDistribution,
        HotelReviewGrade,
    )
    import uuid

    if not content_review_score:
        return

    score_instances = []
    dist_instances = []
    grade_instances = []

    def _create_score(combined, provider_id, is_default, cumulative, trending, demographics):
        cumulative = cumulative or {}
        trending = trending or {}

        score_uid = uuid.uuid4()
        score_instances.append(HotelReviewScore(
            id=score_uid,
            property=property_obj,
            is_combined=combined,
            provider_id=provider_id,
            is_default=is_default,
            score=_safe_decimal(cumulative.get("score")),
            max_score=_safe_decimal(cumulative.get("maxScore"), 10),
            review_count=_safe_int(cumulative.get("reviewCount"), 0),
            trending_past_14_days=_safe_decimal(trending.get("past14DaysUplift")),
            trending_past_30_days=_safe_decimal(trending.get("past30DaysUplift")),
        ))
        stats["review_scores"] += 1

        all_guest = (demographics or {}).get("allGuest") or {}

        for dist in (all_guest.get("scoreDistribution") or []):
            dist_instances.append(HotelReviewScoreDistribution(
                review_score_id=score_uid,
                tier_id=_safe_str(dist.get("id"), 40),
                review_count=_safe_int(dist.get("reviewCount"), 0),
            ))
            stats["score_distributions"] += 1

        for grade in (all_guest.get("grades") or []):
            grade_instances.append(HotelReviewGrade(
                review_score_id=score_uid,
                grade_id=_safe_str(grade.get("id"), 60),
                score=_safe_decimal(grade.get("score")),
                city_average=_safe_decimal(grade.get("cityAverage")),
            ))
            stats["review_grades"] += 1

    combined_score = (
        (content_review_score.get("combinedReviewScore") or {}).get("cumulative") or {}
    )
    if combined_score:
        _create_score(True, None, False, combined_score, None, None)

    for prov in (content_review_score.get("providerReviewScore") or []):
        _create_score(
            False,
            _safe_int(prov.get("providerId")),
            bool(prov.get("isDefault")),
            prov.get("cumulative") or {},
            prov.get("trendingScore") or {},
            prov.get("demographics") or {},
        )

    if score_instances:
        HotelReviewScore.objects.bulk_create(score_instances, batch_size=500)
    if dist_instances:
        HotelReviewScoreDistribution.objects.bulk_create(dist_instances, batch_size=500)
    if grade_instances:
        HotelReviewGrade.objects.bulk_create(grade_instances, batch_size=500)


def _import_favorite_features(property_obj, content_highlights, stats):
    from apps.properties.models import HotelFavoriteFeature
    features = (content_highlights or {}).get("favoriteFeatures") or []
    instances = []

    for sort_idx, feat in enumerate(features):
        instances.append(HotelFavoriteFeature(
            property=property_obj,
            feature_id=_safe_int(feat.get("id"), 0),
            category=_safe_str(feat.get("category"), 80),
            name=_safe_str(feat.get("name"), 255),
            symbol=_safe_str(feat.get("symbol"), 120),
            tooltip=_safe_str(feat.get("tooltip")) or None,
            sort_order=sort_idx,
        ))
        stats["favorite_features"] += 1
    if instances: HotelFavoriteFeature.objects.bulk_create(instances, batch_size=500)


def _import_location_highlights(property_obj, content_highlights, stats):
    from apps.properties.models import HotelLocationHighlight
    instances = []

    for item in (content_highlights or {}).get("locationHighlights") or []:
        instances.append(HotelLocationHighlight(
            property=property_obj,
            name=_safe_str(item.get("message") or item.get("name"), 255),
            symbol="",
            tooltip=None,
            highlight_type=_safe_str(item.get("highlightType"), 80),
            distance_km=_safe_decimal(item.get("distanceKm")),
            message=_safe_str(item.get("message")),
        ))
        stats["location_highlights"] += 1

    for item in (content_highlights or {}).get("locations") or []:
        instances.append(HotelLocationHighlight(
            property=property_obj,
            name=_safe_str(item.get("name"), 255),
            symbol=_safe_str(item.get("symbol"), 120),
            tooltip=_safe_str(item.get("tooltip")) or None,
            highlight_type="",
            distance_km=None,
            message="",
        ))
        stats["location_highlights"] += 1
    if instances: HotelLocationHighlight.objects.bulk_create(instances, batch_size=500)


def _import_atf_highlights(property_obj, content_highlights, stats):
    from apps.properties.models import HotelAtfHighlight
    instances = []

    for item in (content_highlights or {}).get("atfPropertyHighlights") or []:
        instances.append(HotelAtfHighlight(
            property=property_obj,
            name=_safe_str(item.get("name"), 255),
            symbol=_safe_str(item.get("symbol"), 120),
            category=_safe_str(item.get("category"), 80),
            topic_name=_safe_str(item.get("topicName"), 120),
            tooltip=_safe_str(item.get("tooltip")) or None,
        ))
        stats["atf_highlights"] += 1
    if instances: HotelAtfHighlight.objects.bulk_create(instances, batch_size=500)


def _import_nearby_places(property_obj, content_local, stats):
    from apps.properties.models import HotelNearbyPlaceCategory, HotelNearbyPlace
    place_instances = []

    for cat in (content_local or {}).get("nearbyProperties") or []:
        cat_obj, _ = HotelNearbyPlaceCategory.objects.get_or_create(
            property=property_obj,
            category_key=_safe_str(cat.get("id"), 80),
            defaults=dict(
                category_name=_safe_str(cat.get("categoryName"), 120),
                category_symbol=_safe_str(cat.get("categorySymbol"), 120),
            ),
        )
        stats["nearby_categories"] += 1

        for place in (cat.get("places") or []):
            geo = place.get("geoInfo") or {}
            place_instances.append(HotelNearbyPlace(
                category=cat_obj,
                name=_safe_str(place.get("name"), 255),
                abbr=_safe_str(place.get("abbr"), 20) or None,
                distance_km=_safe_decimal(place.get("distanceInKm")),
                duration_seconds=_safe_int(place.get("duration")),
                duration_icon=_safe_str(place.get("durationIcon"), 80) or None,
                latitude=_safe_decimal(geo.get("latitude")),
                longitude=_safe_decimal(geo.get("longitude")),
                landmark_id=_safe_int(place.get("landmarkId")),
                type_id=_safe_int(place.get("typeId")),
                type_name=_safe_str(place.get("typeName"), 120) or None,
            ))
            stats["nearby_places"] += 1
            
    if place_instances:
        HotelNearbyPlace.objects.bulk_create(place_instances, batch_size=500)


# ---------------------------------------------------------------------------
# Property upsert
# ---------------------------------------------------------------------------

def _upsert_property(content_summary, content_info, content_features, clear_content):
    """
    Create or update the core Property row from contentSummary.
    Returns (property_obj, created: bool).
    """
    from apps.properties.models import Property, PropertyStatus

    property_name = _safe_str(
        content_summary.get("displayName") or content_summary.get("defaultName"),
        180,
    )
    if not property_name:
        raise ValueError("Property has no displayName — skipping.")

    provider_property_id = _safe_int(content_summary.get("propertyId"))
    address = content_summary.get("address") or {}
    geo = content_summary.get("geoInfo") or {}

    lat = _safe_decimal(geo.get("latitude"))
    lon = _safe_decimal(geo.get("longitude"))

    # Build slug from name + provider id to help uniqueness
    slug = _make_slug(property_name, suffix=str(provider_property_id) if provider_property_id else "")

    # GeographyPointField expects a WKT string "POINT(lon lat)"
    location_wkt = f"POINT({lon} {lat})" if (lat is not None and lon is not None) else "POINT(0 0)"

    defaults = dict(
        property_name=property_name,
        property_type=_safe_str(content_summary.get("propertyType") or "Hotel", 80),
        short_description=_safe_str((content_info.get("description") or {}).get("short")),
        address_line_1=_safe_str(address.get("address1"), 255),
        address_line_2=_safe_str(address.get("address2"), 255),
        city=_safe_str((address.get("city") or {}).get("name"), 120),
        state="",
        postal_code=_safe_str(address.get("postalCode"), 30),
        country_code=_safe_str(address.get("countryCode"), 2),
        location=location_wkt,
        star_rating=_safe_decimal(content_summary.get("rating")),
        status=PropertyStatus.PUBLISHED,
        metadata={
            "is_luxury": bool(content_summary.get("isLuxuryHotel")),
            "provider_property_id": provider_property_id,
            "accommodation_type": (content_summary.get("accommodation") or {}).get("accommodationType"),
            "area": content_summary.get("address", {}).get("area") or {},
            "contentInformation": content_info,
            "contentFeatures": content_features,
        },
    )

    prop, created = Property.objects.update_or_create(
        slug=slug,
        defaults=defaults,
    )

    # Wipe all child content tables when --clear flag is used or on recreation
    if clear_content or not created:
        _delete_content(prop)

    return prop, created


def _delete_content(property_obj):
    """Remove all previously imported content rows for this property."""
    from apps.properties.models import (
        HotelImage,
        HotelVideo,
        HotelReviewSnippet,
        HotelReviewScore,
        HotelRecommendationScore,
        HotelPositiveMention,
        HotelFavoriteFeature,
        HotelLocationHighlight,
        HotelAtfHighlight,
        HotelNearbyPlaceCategory,
    )

    HotelImage.objects.filter(property=property_obj).delete()
    HotelVideo.objects.filter(property=property_obj).delete()
    HotelReviewSnippet.objects.filter(property=property_obj).delete()
    HotelReviewScore.objects.filter(property=property_obj).delete()
    HotelRecommendationScore.objects.filter(property=property_obj).delete()
    HotelPositiveMention.objects.filter(property=property_obj).delete()
    HotelFavoriteFeature.objects.filter(property=property_obj).delete()
    HotelLocationHighlight.objects.filter(property=property_obj).delete()
    HotelAtfHighlight.objects.filter(property=property_obj).delete()
    HotelNearbyPlaceCategory.objects.filter(property=property_obj).delete()


# ---------------------------------------------------------------------------
# Main processor for a single MongoDB document
# ---------------------------------------------------------------------------

def _process_document(doc, clear_content, stats):
    """
    Process one MongoDB hotel document.
    A document may contain a list of propertyDetails — each is imported separately.
    """
    try:
        property_details_list = (
            doc.get("data", {})
               .get("propertyDetailsSearch", {})
               .get("propertyDetails") or []
        )
    except AttributeError:
        logger.warning("Document has unexpected shape — skipping.")
        return

    for detail in property_details_list:
        content_detail = detail.get("contentDetail") or {}
        content_summary = content_detail.get("contentSummary") or {}

        # Fallback: propertyId at the root level
        if not content_summary.get("propertyId"):
            content_summary["propertyId"] = detail.get("propertyId")

        provider_id = content_summary.get("propertyId")
        
        # SKIP LOGIC: If we already have it and are NOT clearing, just jump to the next one!
        if not clear_content and provider_id:
            from apps.properties.models import Property
            try:
                # Check JSON metadata for our unique ID
                if Property.objects.filter(metadata__provider_property_id=int(provider_id)).exists():
                    logger.info(f"Skipped existing property ID: {provider_id}")
                    stats["properties_updated"] = stats.get("properties_updated", 0) + 1 # Optional: track skipped
                    continue
            except (ValueError, TypeError):
                pass
        
        try:
            with transaction.atomic():
                prop, created = _upsert_property(
                    content_summary, 
                    content_detail.get("contentInformation") or {}, 
                    content_detail.get("contentFeatures") or {}, 
                    clear_content
                )

                action = "Created" if created else "Updated"
                logger.info(f"{action} property: {prop.property_name} (slug={prop.slug})")
                stats["properties_created" if created else "properties_updated"] += 1

                # Content images
                _import_images(prop, content_detail.get("contentImages"), stats)
                _import_videos(prop, content_detail.get("contentImages"), stats)

                # Reviews
                review_summaries = content_detail.get("contentReviewSummaries") or {}
                _import_review_snippets(prop, review_summaries, stats)
                _import_recommendation_score(prop, review_summaries, stats)
                _import_positive_mentions(prop, review_summaries, stats)
                _import_review_scores(prop, content_detail.get("contentReviewScore"), stats)

                # Highlights
                highlights = content_detail.get("contentHighlights") or {}
                _import_favorite_features(prop, highlights, stats)
                _import_location_highlights(prop, highlights, stats)
                _import_atf_highlights(prop, highlights, stats)

                # Local information
                _import_nearby_places(prop, content_detail.get("contentLocalInformation"), stats)

        except Exception as exc:
            name = content_summary.get("displayName", "unknown")
            logger.error(f"Failed to import property '{name}': {exc}", exc_info=True)
            stats["errors"] += 1


# ---------------------------------------------------------------------------
# Management Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Import hotel data from MongoDB (Agoda.hotels) into the Django "
        "properties models. Requires pymongo to be installed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="localhost",
            help="MongoDB host (default: localhost)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=27017,
            help="MongoDB port (default: 27017)",
        )
        parser.add_argument(
            "--db",
            default="Agoda",
            help="MongoDB database name (default: Agoda)",
        )
        parser.add_argument(
            "--collection",
            default="hotels",
            help="MongoDB collection name (default: hotels)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max documents to process (0 = all)",
        )
        parser.add_argument(
            "--property-id",
            type=int,
            default=None,
            help="Import only the document whose propertyId matches this value",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help=(
                "Delete and re-import all content rows for each property "
                "instead of skipping existing ones."
            ),
        )

    def handle(self, *args, **options):  # noqa: PLR0912
        # ----------------------------------------------------------------
        # 1. Import pymongo lazily so the rest of the codebase doesn't depend on it
        # ----------------------------------------------------------------
        try:
            from pymongo import MongoClient
        except ImportError:
            raise CommandError(
                "pymongo is not installed. Run: pip install pymongo"
            )

        # ----------------------------------------------------------------
        # 2. Skip Vendor code
        # ----------------------------------------------------------------

        # ----------------------------------------------------------------
        # 3. Connect to MongoDB
        # ----------------------------------------------------------------
        host = options["host"]
        port = options["port"]
        db_name = options["db"]
        collection_name = options["collection"]

        self.stdout.write(f"Connecting to MongoDB at {host}:{port} …")
        try:
            client = MongoClient(host, port, serverSelectionTimeoutMS=5000)
            # Ping to verify connection
            client.admin.command("ping")
        except Exception as exc:
            raise CommandError(f"Cannot connect to MongoDB: {exc}")

        collection = client[db_name][collection_name]
        self.stdout.write(
            self.style.SUCCESS(f"Connected -> {db_name}.{collection_name}")
        )

        # ----------------------------------------------------------------
        # 4. Build Mongo query / cursor
        # ----------------------------------------------------------------
        mongo_filter = {}

        if options["property_id"]:
            pid = options["property_id"]
            # The propertyId can sit at different nesting levels; search both
            mongo_filter = {
                "$or": [
                    {"data.propertyDetailsSearch.propertyDetails.propertyId": pid},
                    {"data.propertyDetailsSearch.propertyDetails.contentDetail.contentSummary.propertyId": pid},
                ]
            }
            self.stdout.write(f"Filtering for propertyId={pid}")

        cursor = collection.find(mongo_filter)
        if options["limit"]:
            cursor = cursor.limit(options["limit"])
            self.stdout.write(f"Limiting to {options['limit']} document(s)")

        # ----------------------------------------------------------------
        # 5. Process documents
        # ----------------------------------------------------------------
        stats = {
            "properties_created": 0,
            "properties_updated": 0,
            "images": 0,
            "image_urls": 0,
            "videos": 0,
            "review_snippets": 0,
            "recommendation_scores": 0,
            "positive_mentions": 0,
            "review_scores": 0,
            "score_distributions": 0,
            "review_grades": 0,
            "favorite_features": 0,
            "location_highlights": 0,
            "atf_highlights": 0,
            "nearby_categories": 0,
            "nearby_places": 0,
            "errors": 0,
        }

        doc_count = 0
        for doc in cursor:
            doc_count += 1
            self.stdout.write(f"Processing document #{doc_count} …", ending="\r")
            _process_document(doc, options["clear"], stats)

        client.close()

        # ----------------------------------------------------------------
        # 6. Summary report
        # ----------------------------------------------------------------
        self.stdout.write("\n" + "=" * 56)
        self.stdout.write(self.style.SUCCESS("Import complete!"))
        self.stdout.write(f"  MongoDB documents processed : {doc_count}")
        self.stdout.write(f"  Properties created          : {stats['properties_created']}")
        self.stdout.write(f"  Properties updated          : {stats['properties_updated']}")
        self.stdout.write(f"  Images                      : {stats['images']}")
        self.stdout.write(f"  Image URL variants          : {stats['image_urls']}")
        self.stdout.write(f"  Videos                      : {stats['videos']}")
        self.stdout.write(f"  Review snippets             : {stats['review_snippets']}")
        self.stdout.write(f"  Recommendation scores       : {stats['recommendation_scores']}")
        self.stdout.write(f"  Positive mentions           : {stats['positive_mentions']}")
        self.stdout.write(f"  Review score rows           : {stats['review_scores']}")
        self.stdout.write(f"  Score distributions         : {stats['score_distributions']}")
        self.stdout.write(f"  Review grade rows           : {stats['review_grades']}")
        self.stdout.write(f"  Favorite features           : {stats['favorite_features']}")
        self.stdout.write(f"  Location highlights         : {stats['location_highlights']}")
        self.stdout.write(f"  ATF highlights              : {stats['atf_highlights']}")
        self.stdout.write(f"  Nearby place categories     : {stats['nearby_categories']}")
        self.stdout.write(f"  Nearby places               : {stats['nearby_places']}")
        if stats["errors"]:
            self.stdout.write(
                self.style.ERROR(f"  Errors (skipped)            : {stats['errors']}")
            )
        self.stdout.write("=" * 56)
