import json
import uuid

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from apps.content.models import PlatformSetting


@require_GET
def db_health_check(request: HttpRequest) -> JsonResponse:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_schema(), version()")
        current_database, current_schema, version = cursor.fetchone()

    return JsonResponse(
        {
            "ok": True,
            "database": current_database,
            "schema": current_schema,
            "postgres_version": version,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def db_smoke_test(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = json.loads(request.body or "{}")
        test_key = payload.get("key") or f"smoke_test_{uuid.uuid4().hex[:12]}"
        test_value = payload.get(
            "value",
            {"message": "Database write/read check from Django", "source": "db_smoke_test"},
        )

        setting, created = PlatformSetting.objects.update_or_create(
            key=test_key,
            defaults={"value": test_value},
        )

        return JsonResponse(
            {
                "ok": True,
                "action": "created" if created else "updated",
                "record": {
                    "key": setting.key,
                    "value": setting.value,
                    "updated_at": setting.updated_at.isoformat(),
                },
            },
            status=201 if created else 200,
        )

    key = request.GET.get("key")
    if key:
        try:
            setting = PlatformSetting.objects.get(key=key)
        except PlatformSetting.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Record not found", "key": key}, status=404)

        return JsonResponse(
            {
                "ok": True,
                "record": {
                    "key": setting.key,
                    "value": setting.value,
                    "updated_at": setting.updated_at.isoformat(),
                },
            }
        )

    records = list(
        PlatformSetting.objects.order_by("-updated_at").values("key", "value", "updated_at")[:10]
    )
    for record in records:
        record["updated_at"] = record["updated_at"].isoformat()

    return JsonResponse({"ok": True, "count": len(records), "records": records})
