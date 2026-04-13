"""
Referral views:
  - Public: dynamic referral form for a specific org (volunteer or self-referral)
  - Portal: org manager inbox — list, detail, acknowledge, status update, CSV export, print view
"""
import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.audit.models import AuditEntry
from apps.organizations.models import Organization

from .models import Referral, ReferralDelivery, ReferralFormField
from .services import create_referral, queue_deliveries


# ---------------------------------------------------------------------------
# Public: dynamic referral form
# ---------------------------------------------------------------------------

def referral_form(request, org_slug):
    """
    Render the custom referral form for an org. Accessible to any logged-in user.
    Anonymous self-referrals are also accepted (consent makes this legal).
    """
    org = get_object_or_404(Organization, slug=org_slug, status="active", accepts_referrals=True)
    fields = ReferralFormField.objects.filter(
        organization=org, is_active=True
    ).order_by("display_order")

    if request.method == "POST":
        errors = {}
        form_data = {}
        pii_dict = {}

        for field in fields:
            key = field.slug
            value = request.POST.get(key, "").strip()
            if field.is_required and not value and field.field_type != "consent":
                errors[key] = _("This field is required.")
            if field.field_type == "consent":
                pii_dict["consent"] = bool(request.POST.get(key))
            elif field.is_pii:
                pii_dict[key] = value
            else:
                form_data[key] = value

        # Consent is always required — captured from custom field or hardcoded checkbox
        if "consent" not in pii_dict:
            pii_dict["consent"] = bool(request.POST.get("consent"))
        if not pii_dict.get("consent"):
            errors["consent"] = _("You must give consent to submit a referral.")

        if errors:
            return render(request, "public/referrals/form.html", {
                "org": org,
                "fields": fields,
                "errors": errors,
                "posted": request.POST,
            })

        referring_user = request.user if request.user.is_authenticated else None
        consent_text = org.referral_instructions or _("I consent to my information being shared.")

        referral = create_referral(
            org=org,
            form_data=form_data,
            pii_dict=pii_dict,
            referring_user=referring_user,
            priority=request.POST.get("priority", "normal"),
            consent_statement=str(consent_text),
        )
        queue_deliveries(referral)

        return redirect("referrals:submitted", ref=referral.reference_number)

    return render(request, "public/referrals/form.html", {
        "org": org,
        "fields": fields,
        "errors": {},
        "posted": {},
    })


def referral_submitted(request, ref):
    """Confirmation page shown after a referral is submitted."""
    referral = get_object_or_404(Referral, reference_number=ref)
    return render(request, "public/referrals/submitted.html", {"referral": referral})


# ---------------------------------------------------------------------------
# Portal: org manager inbox
# ---------------------------------------------------------------------------

def _require_org_manager(request):
    """Return the org for which this user is a manager, or None."""
    if not request.user.is_authenticated:
        return None
    return getattr(request.user, "organization", None)


@login_required
def portal_referral_list(request):
    org = _require_org_manager(request)
    if org is None:
        messages.error(request, _("Access denied."))
        return redirect("core:home")

    base_qs = Referral.objects.filter(organization=org)
    # Unacknowledged count is always over the full org inbox, not the filtered view
    unacknowledged_count = base_qs.filter(
        acknowledged_at__isnull=True, status="submitted"
    ).count()

    qs = base_qs.order_by("-created_at")

    # Filters
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)

    return render(request, "portal/referrals/list.html", {
        "org": org,
        "referrals": qs,
        "status_choices": Referral.STATUS_CHOICES,
        "priority_choices": Referral.PRIORITY_CHOICES,
        "selected_status": status,
        "selected_priority": priority,
        "unacknowledged_count": unacknowledged_count,
    })


@login_required
def portal_referral_detail(request, ref):
    org = _require_org_manager(request)
    if org is None:
        messages.error(request, _("Access denied."))
        return redirect("core:home")

    referral = get_object_or_404(Referral, reference_number=ref, organization=org)
    pii = referral.get_pii()

    AuditEntry.log(
        action="referral_pii_accessed",
        actor=request.user,
        target=referral,
        metadata={"ip": request.META.get("REMOTE_ADDR")},
    )

    return render(request, "portal/referrals/detail.html", {
        "org": org,
        "referral": referral,
        "pii": pii,
        "history": referral.status_history.all(),
        "deliveries": referral.deliveries.all(),
        "status_choices": Referral.STATUS_CHOICES,
    })


@login_required
@require_POST
def portal_acknowledge(request, ref):
    org = _require_org_manager(request)
    if org is None:
        return redirect("core:home")
    referral = get_object_or_404(Referral, reference_number=ref, organization=org)
    if not referral.acknowledged_at:
        referral.transition_status("acknowledged", actor=request.user, note="Acknowledged via portal")
        messages.success(request, _("Referral acknowledged."))
    return redirect("referrals:portal_detail", ref=ref)


@login_required
@require_POST
def portal_update_status(request, ref):
    org = _require_org_manager(request)
    if org is None:
        return redirect("core:home")
    referral = get_object_or_404(Referral, reference_number=ref, organization=org)
    new_status = request.POST.get("status")
    note = request.POST.get("note", "")
    valid = [s for s, _ in Referral.STATUS_CHOICES]
    if new_status in valid and new_status != referral.status:
        referral.transition_status(new_status, actor=request.user, note=note)
        messages.success(request, _("Status updated."))
    return redirect("referrals:portal_detail", ref=ref)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@login_required
def portal_referral_csv(request):
    """Download all referrals for the org as a CSV (PII decrypted for authorised manager)."""
    org = _require_org_manager(request)
    if org is None:
        return redirect("core:home")

    AuditEntry.log(
        action="referral_pii_accessed",
        actor=request.user,
        target=org,
        metadata={"type": "csv_export", "ip": request.META.get("REMOTE_ADDR")},
    )

    referrals = Referral.objects.filter(organization=org).order_by("-created_at")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Reference", "Status", "Priority", "Submitted",
        "Acknowledged", "Form Data", "PII (decrypted)",
    ])
    for r in referrals:
        pii = r.get_pii()
        writer.writerow([
            r.reference_number,
            r.status,
            r.priority,
            r.created_at.strftime("%Y-%m-%d %H:%M"),
            r.acknowledged_at.strftime("%Y-%m-%d %H:%M") if r.acknowledged_at else "",
            str(r.form_data),
            str(pii),
        ])

    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="referrals-{org.slug}-{timezone.now():%Y%m%d}.csv"'
    )
    return response


# ---------------------------------------------------------------------------
# Print view
# ---------------------------------------------------------------------------

@login_required
def portal_referral_print(request, ref):
    """Printer-friendly referral sheet for paper filing."""
    org = _require_org_manager(request)
    if org is None:
        return redirect("core:home")
    referral = get_object_or_404(Referral, reference_number=ref, organization=org)
    pii = referral.get_pii()

    AuditEntry.log(
        action="referral_pii_accessed",
        actor=request.user,
        target=referral,
        metadata={"type": "print", "ip": request.META.get("REMOTE_ADDR")},
    )

    return render(request, "portal/referrals/print.html", {
        "referral": referral,
        "org": org,
        "pii": pii,
    })
