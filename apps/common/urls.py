from django.urls import path

from apps.common.views import db_health_check, db_smoke_test

urlpatterns = [
    path("health/db/", db_health_check, name="db-health-check"),
    path("dev/db-smoke-test/", db_smoke_test, name="db-smoke-test"),
]
