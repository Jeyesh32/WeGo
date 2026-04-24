from django.contrib.postgres.operations import BtreeGistExtension, CITextExtension, CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        CreateExtension("pgcrypto"),
        CreateExtension("postgis"),
        CITextExtension(),
        BtreeGistExtension(),
    ]
