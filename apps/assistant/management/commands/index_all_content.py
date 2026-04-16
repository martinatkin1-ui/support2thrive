"""
Management command: index_all_content
Bootstrap command to index all existing platform content into LightRAG.
Run once after initial setup (or to rebuild the index after migrations).

Usage:
  python manage.py index_all_content                  # all content
  python manage.py index_all_content --orgs-only      # organisations only
  python manage.py index_all_content --pathways-only  # pathways only
  python manage.py index_all_content --dry-run        # print what would be indexed

This dispatches Celery tasks — Celery worker must be running.
"""
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _


class Command(BaseCommand):
    help = "Index all platform content (orgs, pathways) into LightRAG knowledge graph."

    def add_arguments(self, parser):
        parser.add_argument(
            "--orgs-only",
            action="store_true",
            help="Index only organisations and their services.",
        )
        parser.add_argument(
            "--pathways-only",
            action="store_true",
            help="Index only pathways.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be indexed without dispatching tasks.",
        )

    def handle(self, *args, **options):
        from apps.assistant.tasks import index_organization, index_pathway
        from apps.organizations.models import Organization
        from apps.pathways.models import Pathway

        dry_run = options["dry_run"]
        orgs_only = options["orgs_only"]
        pathways_only = options["pathways_only"]

        org_count = 0
        pathway_count = 0

        if not pathways_only:
            orgs = Organization.objects.filter(status="active")
            org_count = orgs.count()
            self.stdout.write(f"Found {org_count} active organisations.")
            if not dry_run:
                for org in orgs:
                    index_organization.delay(org.pk)
                    self.stdout.write(f"  Queued: {org.name} (id={org.pk})")
            else:
                for org in orgs:
                    self.stdout.write(f"  [dry-run] Would index: {org.name} (id={org.pk})")

        if not orgs_only:
            pathways = Pathway.objects.filter(is_published=True)
            pathway_count = pathways.count()
            self.stdout.write(f"Found {pathway_count} published pathways.")
            if not dry_run:
                for pathway in pathways:
                    index_pathway.delay(pathway.pk)
                    self.stdout.write(f"  Queued: {pathway.title} (id={pathway.pk})")
            else:
                for pathway in pathways:
                    self.stdout.write(f"  [dry-run] Would index: {pathway.title} (id={pathway.pk})")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run complete. Would queue {org_count} orgs + {pathway_count} pathways."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Queued {org_count} orgs + {pathway_count} pathways for indexing. "
                f"Monitor with: celery -A config inspect active"
            ))
