from rest_framework import generics, permissions

from apps.properties.models import Property, Room
from apps.properties.serializers import PropertySerializer, RoomSerializer
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


class PropertyListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Property.objects.select_related("vendor").prefetch_related(
            "rooms__rate_plans__hourly_rates"
        ).order_by("-created_at")
        city = self.request.query_params.get("city")
        status_value = self.request.query_params.get("status")
        if city:
            queryset = queryset.filter(city__iexact=city)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class PropertyDetailView(generics.RetrieveAPIView):
    queryset = Property.objects.select_related("vendor").prefetch_related("rooms__rate_plans__hourly_rates")
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]


class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Room.objects.select_related("property").prefetch_related("rate_plans__hourly_rates").order_by("-created_at")
        property_id = self.request.query_params.get("property_id")
        status_value = self.request.query_params.get("status")
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class RoomDetailView(generics.RetrieveAPIView):
    queryset = Room.objects.select_related("property").prefetch_related("rate_plans__hourly_rates")
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]


def sample_agoda_api_view(request, pk):
    """
    Returns the exact structure like Sample-Hotel.json reconstructed from the DB.
    """
    prop = get_object_or_404(Property, pk=pk)
    meta = prop.metadata or {}
    
    # 1. Images
    hotel_images = []
    for img in prop.hotel_images.all().prefetch_related("urls"):
        urls = [{"key": u.size_key, "value": u.url} for u in img.urls.all()]
        hotel_images.append({
            "id": img.provider_image_id,
            "caption": img.caption,
            "groupId": img.group_id,
            "group": img.group,
            "groupEntityId": img.group_entity_id,
            "providerId": img.provider_id,
            "typeId": img.type_id,
            "uploadedDate": img.uploaded_date.isoformat() if img.uploaded_date else None,
            "highResolutionSizes": img.high_resolution_sizes.split(",") if img.high_resolution_sizes else [],
            "urls": urls,
        })
        
    videos = []
    for vid in prop.hotel_videos.all():
        videos.append({
            "id": vid.provider_video_id,
            "location": vid.location,
            "generated_type": vid.generated_type,
        })

    # 2. Reviews
    snippets = []
    for snip in prop.review_snippets.all():
        snippets.append({
            "snippetId": snip.snippet_id,
            "countryCode": snip.country_code,
            "countryName": snip.country_name,
            "date": snip.reviewed_at.isoformat() if snip.reviewed_at else None,
            "demographicId": snip.demographic_id,
            "demographicName": snip.demographic_name,
            "reviewer": snip.reviewer,
            "reviewRating": float(snip.review_rating) if snip.review_rating else None,
            "snippet": snip.snippet,
        })

    rec_score = prop.recommendation_score
    recommendationScores = {}
    if rec_score:
        recommendationScores = {
            "frequentTravellerRecommendationScore": rec_score.frequent_traveller_score,
            "recommendationScore": rec_score.general_score,
        }

    positiveMentions = {"facilityClassesSentiment": []}
    for pm in prop.positive_mentions.all():
        positiveMentions["facilityClassesSentiment"].append({
            "id": pm.facility_class_id,
            "name": pm.name,
            "noOfPositiveMentioned": pm.no_of_positive_mentioned,
            "facilityIds": pm.facility_ids,
        })

    # 3. Highlights
    fav_features = []
    for ff in prop.favorite_features.all():
        fav_features.append({
            "id": ff.feature_id,
            "category": ff.category,
            "name": ff.name,
            "symbol": ff.symbol,
            "tooltip": ff.tooltip,
        })

    # 4. Local Info (Nearby places)
    nearby_props = []
    for cat in prop.nearby_place_categories.all().prefetch_related("places"):
        places = []
        for p in cat.places.all():
            places.append({
                "name": p.name,
                "abbr": p.abbr,
                "distanceInKm": float(p.distance_km) if p.distance_km else None,
                "duration": p.duration_seconds,
                "durationIcon": p.duration_icon,
                "geoInfo": {
                    "latitude": float(p.latitude) if p.latitude else None,
                    "longitude": float(p.longitude) if p.longitude else None,
                },
                "landmarkId": p.landmark_id,
                "typeId": p.type_id,
                "typeName": p.type_name,
            })
        nearby_props.append({
            "id": cat.category_key,
            "categoryName": cat.category_name,
            "categorySymbol": cat.category_symbol,
            "places": places,
        })

    # Reconstruct Final JSON Document
    content_detail = {
        "propertyId": meta.get("provider_property_id"),
        "contentImages": {
            "hotelImages": hotel_images,
            "videos": videos,
        },
        "contentReviewSummaries": {
            "snippets": snippets,
            "recommendationScores": recommendationScores,
            "positiveMentions": positiveMentions,
        },
        "contentSummary": {
            "displayName": prop.property_name,
            "propertyType": prop.property_type,
            "rating": float(prop.star_rating) if prop.star_rating else None,
            "address": {
                "address1": prop.address_line_1,
                "address2": prop.address_line_2,
                "city": {"name": prop.city},
                "postalCode": prop.postal_code,
                "countryCode": prop.country_code,
                "area": meta.get("area", {}),
            },
            "geoInfo": {
                "latitude": prop.location.y if prop.location else None,
                "longitude": prop.location.x if prop.location else None,
            },
            "isLuxuryHotel": meta.get("is_luxury"),
            "accommodation": {"accommodationType": meta.get("accommodation_type")},
        },
        "contentHighlights": {
            "favoriteFeatures": fav_features,
            # (locationHighlights and labels omitted for brevity)
        },
        "contentLocalInformation": {
            "nearbyProperties": nearby_props,
        },
        "contentInformation": meta.get("contentInformation", {}),
        "contentFeatures": meta.get("contentFeatures", {}),
    }

    payload = {
        "data": {
            "propertyDetailsSearch": {
                "propertyDetails": [
                    {
                        "propertyId": meta.get("provider_property_id"),
                        "contentDetail": content_detail,
                    }
                ]
            }
        }
    }
    
    return JsonResponse(payload)

