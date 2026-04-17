"""
Data migration: creates the West Midlands Region and assigns all existing
organisations to it. Subsequent seed runs also assign to this region.
"""
from django.db import migrations


def assign_west_midlands_region(apps, schema_editor):
    Region = apps.get_model("core", "Region")
    Organization = apps.get_model("organizations", "Organization")

    region, _ = Region.objects.get_or_create(
        slug="west-midlands",
        defaults={
            "name": "West Midlands",
            "description": (
                "The West Midlands Combined Authority area, covering Wolverhampton, "
                "Birmingham, Coventry, Dudley, Sandwell, Solihull, and Walsall."
            ),
            "brand_color_primary": "#2563eb",
            "brand_color_accent": "#16a34a",
            "contact_email": "info@support2thrive.org.uk",
            "lat_center": 52.4862,
            "lng_center": -1.8904,
            "is_active": True,
        },
    )
    Organization.objects.filter(region__isnull=True).update(region=region)


def reverse_assign(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.all().update(region=None)


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_add_region_fk"),
        ("core", "0002_add_region_model"),
    ]

    operations = [
        migrations.RunPython(assign_west_midlands_region, reverse_assign),
    ]
