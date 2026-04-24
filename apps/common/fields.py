from django.db import models


class GeographyPointField(models.Field):
    description = "PostGIS geography(Point,4326)"

    def db_type(self, connection):
        return "geography(POINT,4326)"

    def get_prep_value(self, value):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)) and len(value) == 2:
            longitude, latitude = value
            return f"SRID=4326;POINT({longitude} {latitude})"
        if isinstance(value, dict) and {"longitude", "latitude"} <= set(value.keys()):
            return f"SRID=4326;POINT({value['longitude']} {value['latitude']})"
        raise ValueError("GeographyPointField expects WKT, [longitude, latitude], or {'longitude', 'latitude'}")

    def from_db_value(self, value, expression, connection):
        return value

    def to_python(self, value):
        return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
