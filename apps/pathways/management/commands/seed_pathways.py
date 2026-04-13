"""
Seed the two core pathways: Prison Leavers and Homelessness Support.
Safe to re-run — uses get_or_create throughout.

Usage:
    python manage.py seed_pathways
"""
from django.core.management.base import BaseCommand

from apps.core.models import Region
from apps.pathways.models import Pathway, PathwayGuideItem, PathwaySection


PATHWAYS_DATA = [
    {
        "title": "Support for Prison Leavers",
        "slug": "prison-leavers",
        "audience_tag": "prison_leavers",
        "icon_name": "shield-check",
        "description": (
            "Leaving prison is a big moment. Whether you have support or are starting fresh, "
            "this guide walks you through everything you need to sort in your first days and weeks — "
            "from housing and benefits to health and staying connected."
        ),
        "meta_description": "Step-by-step support for people leaving prison in the West Midlands.",
        "display_order": 1,
        "sections": [
            {
                "title": "Your First 24 Hours",
                "icon_name": "clock",
                "body": "The first day out can feel overwhelming. Here's what to do right away.",
                "display_order": 1,
                "items": [
                    {
                        "title": "Collect your discharge money and belongings",
                        "body": "You should receive your discharge grant on release. If anything is missing, ask the gate staff before you leave.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Contact your probation officer",
                        "body": "If you're on licence, you must report to your probation officer on the day of release. Missing this could mean recall.",
                        "is_urgent": True,
                        "display_order": 2,
                    },
                    {
                        "title": "Find somewhere safe to sleep tonight",
                        "body": "If you have no fixed address, contact the local council's housing team or a local hostel as soon as possible.",
                        "link_url": "",
                        "link_label": "Find emergency housing",
                        "is_urgent": True,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Housing",
                "icon_name": "home",
                "body": "Finding stable housing is one of the most important steps in resettlement.",
                "display_order": 2,
                "items": [
                    {
                        "title": "Apply for council housing or housing benefit",
                        "body": "Contact your local council to apply for social housing. You can also apply for Housing Benefit or Universal Credit to help with rent.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Find a local hostel or supported housing",
                        "body": "If you need temporary accommodation, organisations in the West Midlands can help you find a hostel or supported housing placement.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                    {
                        "title": "Know your rights as a tenant",
                        "body": "Shelter and local legal aid organisations can advise you on your housing rights and help if you face eviction.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Benefits & Money",
                "icon_name": "banknotes",
                "body": "You may be entitled to benefits from your first day out. Don't delay — some have time limits.",
                "display_order": 3,
                "items": [
                    {
                        "title": "Claim Universal Credit immediately",
                        "body": "Apply for Universal Credit online as soon as you're released. There is a 5-week wait for your first payment, so apply on day one.",
                        "is_urgent": True,
                        "display_order": 1,
                    },
                    {
                        "title": "Open a bank account",
                        "body": "You'll need a bank account to receive benefits. Many banks offer basic accounts for people without a credit history.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                    {
                        "title": "Get a National Insurance number if you don't have one",
                        "body": "Contact HMRC to get or retrieve your National Insurance number — you'll need it for employment and benefits.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Health & Wellbeing",
                "icon_name": "heart",
                "body": "Register with a GP and get the health support you need.",
                "display_order": 4,
                "items": [
                    {
                        "title": "Register with a GP",
                        "body": "You have the right to register with any GP. If you have no address, you can still register — tell the GP surgery you are of no fixed abode.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Collect any ongoing medication",
                        "body": "If you were on medication in prison, make sure you have a supply for the first few days and get a prescription from your new GP.",
                        "is_urgent": True,
                        "display_order": 2,
                    },
                    {
                        "title": "Find support for addiction or mental health",
                        "body": "Local organisations offer free, confidential support for substance misuse and mental health — no referral needed.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Work & Training",
                "icon_name": "briefcase",
                "body": "Employment is one of the strongest factors in successful resettlement.",
                "display_order": 5,
                "items": [
                    {
                        "title": "Register with your local Jobcentre Plus",
                        "body": "Jobcentre Plus can help you find work and access training. Ask about the Restart scheme and other employment programmes.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Get help with your CV and job applications",
                        "body": "Local organisations offer free CV support, interview coaching, and help with job applications.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                    {
                        "title": "Understand your disclosure obligations",
                        "body": "For most jobs, spent convictions don't need to be disclosed. A legal advisor can help you understand what you need to tell employers.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
        ],
    },
    {
        "title": "Homelessness Support",
        "slug": "homelessness-support",
        "audience_tag": "homeless",
        "icon_name": "home",
        "description": (
            "Whether you're sleeping rough, sofa surfing, or worried about losing your home, "
            "help is available. This guide connects you with emergency support, housing options, "
            "and the services that can help you get back on your feet."
        ),
        "meta_description": "Emergency and long-term homelessness support across the West Midlands.",
        "display_order": 2,
        "sections": [
            {
                "title": "Emergency Help Tonight",
                "icon_name": "exclamation-triangle",
                "body": "If you need somewhere safe to sleep tonight, these are your first contacts.",
                "display_order": 1,
                "items": [
                    {
                        "title": "Contact your local council's housing team",
                        "body": "Every council has a duty to help if you're homeless or at risk of homelessness. Contact them as soon as possible — out of hours, an emergency line is available.",
                        "is_urgent": True,
                        "display_order": 1,
                    },
                    {
                        "title": "Find an emergency shelter or night shelter",
                        "body": "Night shelters and emergency hostels provide safe places to sleep. Local organisations can help you find one.",
                        "is_urgent": True,
                        "display_order": 2,
                    },
                    {
                        "title": "Call Shelter's helpline",
                        "body": "Shelter's free helpline is available 7 days a week for housing advice and emergency support.",
                        "link_url": "https://www.shelter.org.uk/get_help",
                        "link_label": "Shelter helpline",
                        "is_urgent": True,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Your Housing Rights",
                "icon_name": "scale",
                "body": "You have rights, even if you're homeless. Understanding them helps you get the support you're entitled to.",
                "display_order": 2,
                "items": [
                    {
                        "title": "Apply as homeless to your local council",
                        "body": "If you're homeless or at imminent risk, the council has a legal duty to help. Bring ID and any documents you have — but don't let lack of documents stop you applying.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Understand priority need",
                        "body": "Families with children, pregnant women, and people with serious health conditions are often in 'priority need'. A housing adviser can assess your situation.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                    {
                        "title": "Challenge a decision you disagree with",
                        "body": "If the council turns you away, you have the right to a review. Get free legal advice from a local law centre or Shelter.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
            {
                "title": "Food & Essentials",
                "icon_name": "shopping-bag",
                "body": "You shouldn't go hungry. Local food banks and community organisations can help.",
                "display_order": 3,
                "items": [
                    {
                        "title": "Find your nearest food bank",
                        "body": "Food banks provide emergency food parcels. You may need a referral from a GP, council, or support worker — but many welcome self-referrals.",
                        "link_url": "https://www.trusselltrust.org/get-help/find-a-foodbank/",
                        "link_label": "Find a food bank",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Access community meals",
                        "body": "Churches, community centres, and local charities often provide free hot meals — no questions asked.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                ],
            },
            {
                "title": "Benefits & Money",
                "icon_name": "banknotes",
                "body": "Being homeless doesn't stop you claiming benefits. You have the right to financial support.",
                "display_order": 4,
                "items": [
                    {
                        "title": "Claim Universal Credit",
                        "body": "You can claim Universal Credit even without a fixed address. Use a friend's address, a hostel, or a local organisation's address as your contact address.",
                        "is_urgent": True,
                        "display_order": 1,
                    },
                    {
                        "title": "Get a Post Office card account or basic bank account",
                        "body": "You need somewhere for benefits to be paid. Many banks offer basic accounts without requiring a credit history.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                ],
            },
            {
                "title": "Health & Wellbeing",
                "icon_name": "heart",
                "body": "Looking after your health is important, even when other things feel uncertain.",
                "display_order": 5,
                "items": [
                    {
                        "title": "Register with a GP — you can use any address",
                        "body": "You have a right to register with a GP even if you're of no fixed abode. Tell the surgery you're homeless and they must register you.",
                        "is_urgent": False,
                        "display_order": 1,
                    },
                    {
                        "title": "Access mental health support",
                        "body": "Homelessness is stressful. Talking to someone can help. Local organisations offer free, confidential counselling and peer support.",
                        "is_urgent": False,
                        "display_order": 2,
                    },
                    {
                        "title": "Find substance misuse support",
                        "body": "If you're struggling with alcohol or drugs, free help is available locally — no referral needed.",
                        "is_urgent": False,
                        "display_order": 3,
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the two core pathways: Prison Leavers and Homelessness Support"

    def handle(self, *args, **options):
        region = Region.objects.order_by("created_at").first()
        if not region:
            self.stderr.write("No Region found — run seed_data first.")
            return

        created_count = 0
        for pathway_data in PATHWAYS_DATA:
            sections_data = pathway_data.pop("sections")
            pathway, created = Pathway.objects.get_or_create(
                slug=pathway_data["slug"],
                defaults={**pathway_data, "region": region, "is_published": True},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created pathway: {pathway.title}")

            for section_data in sections_data:
                items_data = section_data.pop("items")
                section, _ = PathwaySection.objects.get_or_create(
                    pathway=pathway,
                    title=section_data["title"],
                    defaults=section_data,
                )
                for item_data in items_data:
                    PathwayGuideItem.objects.get_or_create(
                        section=section,
                        title=item_data["title"],
                        defaults=item_data,
                    )
                # restore for idempotency on re-run
                section_data["items"] = items_data

            # restore for idempotency on re-run
            pathway_data["sections"] = sections_data

        self.stdout.write(self.style.SUCCESS(
            f"Pathways seeded. {created_count} new pathway(s) created."
        ))
