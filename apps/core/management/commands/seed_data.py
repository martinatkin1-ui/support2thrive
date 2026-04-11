from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import GeographicArea, SupportStream
from apps.organizations.models import Organization, OrganizationService


SUPPORT_STREAMS = [
    ("Housing", "Support with finding and maintaining accommodation", 1),
    ("Homelessness", "Emergency and long-term support for people who are homeless or at risk", 2),
    ("Addiction & Recovery", "Substance misuse, alcohol recovery, and harm reduction services", 3),
    ("Mental Health", "Counselling, peer support, and clinical mental health services", 4),
    ("Jobs & Employment", "Job readiness, skills training, CV support, and employment services", 5),
    ("Benefits & Welfare", "Benefits advice, welfare rights, and financial support", 6),
    ("Physical Health", "GP access, sexual health, and physical wellbeing services", 7),
    ("Legal Aid", "Legal advice, immigration support, and advocacy", 8),
    ("Food & Essentials", "Food banks, food services, and essential supplies", 9),
    ("Domestic Abuse", "Support for survivors of domestic abuse and violence", 10),
    ("Immigration", "Immigration advice, asylum support, and NRPF services", 11),
    ("Education & Training", "Adult education, skills training, and learning opportunities", 12),
    ("Prison Leavers", "Resettlement support for people leaving prison", 13),
    ("Young People", "Services specifically for children and young people", 14),
    ("Older People", "Services for older adults and elderly care", 15),
]

GEOGRAPHIC_AREAS = [
    "West Midlands",
    "Wolverhampton",
    "Birmingham",
    "Dudley",
    "Sandwell",
    "Walsall",
    "Coventry",
    "Solihull",
]

ORGANIZATIONS = [
    {
        "name": "Recovery Near You",
        "short_description": "Wolverhampton's substance misuse and addiction recovery service offering individual and group support.",
        "description": (
            "Recovery Near You provides comprehensive addiction and recovery support services in Wolverhampton. "
            "We offer individual and group sessions, substitute prescribing and detoxification programmes, "
            "blood-borne virus screening and vaccination, needle exchange programmes, and harm reduction services. "
            "Our multi-disciplinary team includes GPs, mental health nurses, and support workers providing "
            "one-to-one key work support."
        ),
        "city": "Wolverhampton",
        "streams": ["Addiction & Recovery", "Mental Health", "Physical Health"],
        "services": [
            ("Individual Recovery Support", "One-to-one key work sessions with dedicated recovery workers", "Addiction & Recovery", "self_referral"),
            ("Group Recovery Sessions", "Regular peer support group sessions for people in recovery", "Addiction & Recovery", "self_referral"),
            ("Needle Exchange", "Clean needle and equipment exchange programme", "Addiction & Recovery", "drop_in"),
            ("Health Screening", "Blood-borne virus screening and vaccination services", "Physical Health", "self_referral"),
        ],
    },
    {
        "name": "The Good Shepherd",
        "short_description": "Wolverhampton charity supporting people who are homeless with food, housing, and community activities.",
        "description": (
            "The Good Shepherd has been supporting people in Wolverhampton since 2003. We provide food services "
            "and a day centre, Housing First service, private sector lettings scheme, and the LEAP programme "
            "(Lived Experience into Action) offering peer support and volunteering opportunities. We offer "
            "one-to-one key work support covering health, training, employment, housing, and financial wellbeing."
        ),
        "city": "Wolverhampton",
        "email": "office@gsmwolverhampton.org.uk",
        "phone": "01902 399955",
        "address_line_1": "65 Waterloo Road",
        "postcode": "WV1 4QU",
        "streams": ["Homelessness", "Housing", "Food & Essentials", "Jobs & Employment"],
        "services": [
            ("Day Centre & Food Service", "Hot meals, food parcels, and day centre access", "Food & Essentials", "drop_in"),
            ("Housing First", "Intensive housing support for rough sleepers and homeless people", "Housing", "professional_referral"),
            ("LEAP Programme", "Lived Experience into Action - peer support and volunteering", "Jobs & Employment", "self_referral"),
            ("Key Work Support", "One-to-one support for health, training, employment, and housing needs", "Homelessness", "self_referral"),
        ],
    },
    {
        "name": "The Local NHS",
        "short_description": "NHS West Midlands providing primary care, community health, and specialist services across the region.",
        "description": (
            "NHS West Midlands coordinates healthcare across the region including primary medical services "
            "via GPs, community-based physical health services for adults and children, outpatient services, "
            "mental health services, public health, learning disability services, urgent care centres, "
            "and GP out-of-hours care. Serving over 6 million people across the West Midlands."
        ),
        "city": "Birmingham",
        "streams": ["Physical Health", "Mental Health", "Young People", "Older People"],
        "services": [
            ("Primary Care (GP)", "General practice medical services via registered GPs", "Physical Health", "self_referral"),
            ("Urgent Care", "Walk-in urgent care centres for non-emergency medical needs", "Physical Health", "drop_in"),
            ("Community Health", "Community-based health services including health visitors", "Physical Health", "gp_referral"),
        ],
    },
    {
        "name": "Black Country Healthcare NHS Foundation Trust",
        "short_description": "Specialist mental health, learning disability, and community healthcare across the Black Country.",
        "description": (
            "Black Country Healthcare NHS Foundation Trust provides specialist mental health, learning disability, "
            "and community healthcare services across Wolverhampton, Dudley, Walsall, and Sandwell. We offer "
            "adult and older adult mental health services, learning disability services, neurodevelopmental "
            "assessments, community recovery teams, eating disorders services, employment support, "
            "and health visiting."
        ),
        "city": "Dudley",
        "address_line_1": "Trafalgar House, 47-49 King Street",
        "postcode": "DY2 8PS",
        "streams": ["Mental Health", "Physical Health", "Jobs & Employment"],
        "services": [
            ("Adult Mental Health", "Community mental health services for adults", "Mental Health", "gp_referral"),
            ("Older Adult Mental Health", "Specialist mental health services for older people", "Mental Health", "gp_referral"),
            ("Learning Disability Services", "Assessment and support for people with learning disabilities", "Mental Health", "gp_referral"),
            ("Employment Support", "Help getting back into work while managing mental health", "Jobs & Employment", "self_referral"),
        ],
    },
    {
        "name": "Wolverhampton Council",
        "short_description": "City of Wolverhampton Council providing local government services, social care, and community support.",
        "description": (
            "The City of Wolverhampton Council provides a wide range of local government services "
            "including education, adult and children's social care, public health, community development, "
            "housing services, environmental services, and benefits support. As part of the West Midlands "
            "Combined Authority, the council works with health partners to deliver integrated services."
        ),
        "city": "Wolverhampton",
        "website": "https://www.wolverhampton.gov.uk",
        "streams": ["Housing", "Benefits & Welfare", "Education & Training", "Young People", "Older People"],
        "services": [
            ("Housing Services", "Council housing, homelessness prevention, and housing advice", "Housing", "self_referral"),
            ("Adult Social Care", "Social care assessments and support for vulnerable adults", "Older People", "self_referral"),
            ("Benefits Advice", "Council tax support, housing benefit, and welfare advice", "Benefits & Welfare", "self_referral"),
            ("Children's Services", "Safeguarding, family support, and children's social care", "Young People", "professional_referral"),
        ],
    },
    {
        "name": "Rethink Mental Illness",
        "short_description": "National mental health charity with West Midlands services including peer support, advocacy, and community groups.",
        "description": (
            "Rethink Mental Illness is a national charity providing over 90 diverse services across housing, "
            "advocacy, and community support. In the West Midlands, we operate the Walsall Sanctuary Community "
            "Mental Health Service (ages 17+), peer support groups and carer-led groups in Dudley, and are "
            "launching 'The Hub' at Wolverhampton Railway Station. We offer goal-based support, practical "
            "and emotional support, and coping strategy guidance."
        ),
        "city": "Wolverhampton",
        "phone": "0121 522 7007",
        "email": "info@rethink.org",
        "streams": ["Mental Health", "Housing"],
        "services": [
            ("Sanctuary Community Mental Health", "Goal-based mental health support, ages 17+", "Mental Health", "self_referral"),
            ("Peer Support Groups", "Regular peer support groups for people with mental health conditions", "Mental Health", "drop_in"),
            ("Carer Support Groups", "Support groups led by and for carers of people with mental illness", "Mental Health", "drop_in"),
            ("Advocacy", "Independent advocacy for people navigating mental health services", "Mental Health", "self_referral"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with initial support streams, geographic areas, and organizations"

    def handle(self, *args, **options):
        self.stdout.write("Seeding support streams...")
        stream_map = {}
        for name, description, order in SUPPORT_STREAMS:
            stream, created = SupportStream.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": description, "display_order": order},
            )
            stream_map[name] = stream
            if created:
                self.stdout.write(f"  Created: {name}")

        self.stdout.write("Seeding geographic areas...")
        wm, _ = GeographicArea.objects.get_or_create(
            slug="west-midlands", defaults={"name": "West Midlands"}
        )
        for area_name in GEOGRAPHIC_AREAS[1:]:
            GeographicArea.objects.get_or_create(
                slug=slugify(area_name),
                defaults={"name": area_name, "parent": wm},
            )

        self.stdout.write("Seeding organizations...")
        for org_data in ORGANIZATIONS:
            org, created = Organization.objects.get_or_create(
                slug=slugify(org_data["name"]),
                defaults={
                    "name": org_data["name"],
                    "short_description": org_data["short_description"],
                    "description": org_data["description"],
                    "city": org_data.get("city", "Wolverhampton"),
                    "email": org_data.get("email", ""),
                    "phone": org_data.get("phone", ""),
                    "website": org_data.get("website", ""),
                    "address_line_1": org_data.get("address_line_1", ""),
                    "postcode": org_data.get("postcode", ""),
                    "status": "active",
                },
            )
            if created:
                self.stdout.write(f"  Created org: {org_data['name']}")

                # Add support streams
                for stream_name in org_data.get("streams", []):
                    if stream_name in stream_map:
                        org.support_streams.add(stream_map[stream_name])

                # Add services
                for svc_name, svc_desc, svc_stream, svc_access in org_data.get("services", []):
                    if svc_stream in stream_map:
                        OrganizationService.objects.create(
                            organization=org,
                            name=svc_name,
                            description=svc_desc,
                            support_stream=stream_map[svc_stream],
                            access_model=svc_access,
                        )

        self.stdout.write(self.style.SUCCESS("Seed data complete!"))
