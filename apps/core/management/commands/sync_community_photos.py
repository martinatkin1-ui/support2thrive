from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.flickr_feed import sync_community_photos_from_flickr


class Command(BaseCommand):
    help = (
        "Pull recent public Flickr photos for configured regional tags into "
        "CommunityPhoto (similar to the Real Python Picha tutorial pattern)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Max feed items to process (defaults to COMMUNITY_PHOTO_SYNC_LIMIT).",
        )

    def handle(self, *args, **options):
        tags = getattr(
            settings,
            "COMMUNITY_PHOTO_FLICKR_TAGS",
            "wolverhampton,westmidlands,community",
        )
        self.stdout.write(f"Using Flickr tags (one feed per segment, merged): {tags}")
        processed, err = sync_community_photos_from_flickr(limit=options["limit"])
        if err:
            self.stdout.write(self.style.ERROR(err))
        if processed:
            self.stdout.write(self.style.SUCCESS(f"Processed {processed} photo(s)."))
        elif not err:
            self.stdout.write(
                self.style.WARNING(
                    "No photos processed (no usable rows in the feed response)."
                )
            )
