"""
Multi-step onboarding wizard for org managers.

URL pattern:  /portal/onboarding/<step>/
Steps: about → services → referral_config → scraping → review

The middleware (see apps/accounts/middleware.py or config/middleware.py)
redirects org_managers with incomplete onboarding to the wizard on every
portal request. Once complete, the org is set to status=active.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.audit.models import AuditEntry
from apps.referrals.models import ReferralFormField

from .forms import (
    OnboardingAboutForm,
    OnboardingReferralConfigForm,
    OnboardingScrapingForm,
    OnboardingSupportStreamsForm,
    OrganizationServiceForm,
    ReferralFormFieldForm,
)
from .models import OrgOnboardingState, Organization, OrganizationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_org_for_manager(request):
    """Return the org managed by the current user, or None."""
    return Organization.objects.filter(
        users=request.user
    ).first() if hasattr(Organization, "users") else getattr(request.user, "organization", None)


def _get_or_create_state(org):
    state, _ = OrgOnboardingState.objects.get_or_create(organization=org)
    return state


STEP_ORDER = ["about", "services", "referral_config", "scraping", "review"]


def _next_step(current):
    idx = STEP_ORDER.index(current)
    if idx + 1 < len(STEP_ORDER):
        return STEP_ORDER[idx + 1]
    return None


def _prev_step(current):
    idx = STEP_ORDER.index(current)
    if idx > 0:
        return STEP_ORDER[idx - 1]
    return None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

@login_required
def onboarding_wizard(request, step=None):
    """Route to the correct step view."""
    # Resolve the org for this manager
    org = None
    if request.user.role == "org_manager":
        org = getattr(request.user, "organization", None)
    elif request.user.is_staff:
        # Admins can preview any step; require ?org= param
        org_id = request.GET.get("org")
        if org_id:
            org = get_object_or_404(Organization, pk=org_id)

    if org is None:
        messages.error(request, _("No organisation found for your account."))
        return redirect("core:home")

    state = _get_or_create_state(org)

    if step is None:
        # Resume from first incomplete step
        step = state.next_incomplete_step() or "review"

    if step not in STEP_ORDER:
        return redirect("organizations:onboarding", step="about")

    view_map = {
        "about": _step_about,
        "services": _step_services,
        "referral_config": _step_referral_config,
        "scraping": _step_scraping,
        "review": _step_review,
    }
    return view_map[step](request, org, state, step)


# ---------------------------------------------------------------------------
# Shared context helper
# ---------------------------------------------------------------------------

def _wizard_context(org, state, step, form, extra=None):
    ctx = {
        "org": org,
        "state": state,
        "step": step,
        "step_index": STEP_ORDER.index(step),
        "total_steps": len(STEP_ORDER),
        "prev_step": _prev_step(step),
        "next_step": _next_step(step),
        "step_labels": {
            "about": _("About"),
            "services": _("Services"),
            "referral_config": _("Referrals"),
            "scraping": _("Scraping"),
            "review": _("Review"),
        },
        "form": form,
    }
    if extra:
        ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# Step 1 — About
# ---------------------------------------------------------------------------

def _step_about(request, org, state, step):
    if request.method == "POST":
        form = OnboardingAboutForm(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            state.mark_step_complete("about")
            AuditEntry.log(
                action="onboarding_step_completed",
                actor=request.user,
                target=org,
                delta={"step": [None, "about"]},
            )
            messages.success(request, _("About page saved."))
            return redirect("organizations:onboarding_step", step="services")
    else:
        form = OnboardingAboutForm(instance=org)

    return render(
        request,
        "portal/onboarding/step_about.html",
        _wizard_context(org, state, step, form),
    )


# ---------------------------------------------------------------------------
# Step 2 — Services
# ---------------------------------------------------------------------------

def _step_services(request, org, state, step):
    ServiceFormSet = modelformset_factory(
        OrganizationService,
        form=OrganizationServiceForm,
        extra=1,
        can_delete=True,
    )
    streams_form = OnboardingSupportStreamsForm(instance=org)
    qs = OrganizationService.objects.filter(organization=org)

    if request.method == "POST":
        formset = ServiceFormSet(request.POST, queryset=qs, prefix="services")
        streams_form = OnboardingSupportStreamsForm(request.POST, instance=org)
        if formset.is_valid() and streams_form.is_valid():
            streams_form.save()
            instances = formset.save(commit=False)
            for obj in instances:
                obj.organization = org
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            state.mark_step_complete("services")
            AuditEntry.log(
                action="onboarding_step_completed",
                actor=request.user,
                target=org,
                delta={"step": [None, "services"]},
            )
            messages.success(request, _("Services saved."))
            return redirect("organizations:onboarding_step", step="referral_config")
    else:
        formset = ServiceFormSet(queryset=qs, prefix="services")

    return render(
        request,
        "portal/onboarding/step_services.html",
        _wizard_context(org, state, step, None, {
            "formset": formset,
            "streams_form": streams_form,
        }),
    )


# ---------------------------------------------------------------------------
# Step 3 — Referral Config
# ---------------------------------------------------------------------------

def _step_referral_config(request, org, state, step):
    FieldFormSet = modelformset_factory(
        ReferralFormField,
        form=ReferralFormFieldForm,
        extra=1,
        can_delete=True,
    )
    qs = ReferralFormField.objects.filter(organization=org).order_by("display_order")

    if request.method == "POST":
        form = OnboardingReferralConfigForm(request.POST, instance=org)
        formset = FieldFormSet(request.POST, queryset=qs, prefix="fields")
        if form.is_valid() and formset.is_valid():
            form.save()
            instances = formset.save(commit=False)
            for obj in instances:
                obj.organization = org
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            state.mark_step_complete("referral_config")
            AuditEntry.log(
                action="onboarding_step_completed",
                actor=request.user,
                target=org,
                delta={"step": [None, "referral_config"]},
            )
            messages.success(request, _("Referral settings saved."))
            return redirect("organizations:onboarding_step", step="scraping")
    else:
        form = OnboardingReferralConfigForm(instance=org)
        formset = FieldFormSet(queryset=qs, prefix="fields")

    return render(
        request,
        "portal/onboarding/step_referral_config.html",
        _wizard_context(org, state, step, form, {"field_formset": formset}),
    )


# ---------------------------------------------------------------------------
# Step 4 — Scraping Config
# ---------------------------------------------------------------------------

def _step_scraping(request, org, state, step):
    if request.method == "POST":
        form = OnboardingScrapingForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            state.mark_step_complete("scraping")
            AuditEntry.log(
                action="onboarding_step_completed",
                actor=request.user,
                target=org,
                delta={"step": [None, "scraping"]},
            )
            messages.success(request, _("Scraping config saved."))
            return redirect("organizations:onboarding_step", step="review")
    else:
        form = OnboardingScrapingForm(instance=org)

    return render(
        request,
        "portal/onboarding/step_scraping.html",
        _wizard_context(org, state, step, form),
    )


# ---------------------------------------------------------------------------
# Step 5 — Review & Publish
# ---------------------------------------------------------------------------

def _step_review(request, org, state, step):
    if request.method == "POST":
        # Complete onboarding → activate org
        state.mark_step_complete("review")
        if state.is_complete:
            org.status = "active"
            org.save(update_fields=["status"])
            AuditEntry.log(
                action="onboarding_completed",
                actor=request.user,
                target=org,
                delta={"status": ["pending", "active"]},
            )
            messages.success(
                request,
                _("Onboarding complete! Your organisation is now active on the platform."),
            )
            return redirect("organizations:portal_dashboard")
        else:
            # Not all steps done — redirect to first incomplete
            next_step = state.next_incomplete_step()
            messages.warning(
                request,
                _("Please complete all steps before publishing."),
            )
            return redirect("organizations:onboarding_step", step=next_step)

    services = OrganizationService.objects.filter(organization=org, is_active=True)
    referral_fields = ReferralFormField.objects.filter(organization=org, is_active=True)
    step_label_map = {s: label for s, label in OrgOnboardingState.STEPS}
    # "review" itself is completed on POST (publish) — exclude it from the incomplete warning list
    required_step_keys = [s for s, _ in OrgOnboardingState.STEPS if s != "review"]
    incomplete_steps = [s for s in required_step_keys if s not in state.completed_steps]
    incomplete_step_items = [(s, step_label_map.get(s, s)) for s in incomplete_steps]

    return render(
        request,
        "portal/onboarding/step_review.html",
        _wizard_context(org, state, step, None, {
            "services": services,
            "referral_fields": referral_fields,
            "incomplete_steps": incomplete_steps,
            "incomplete_step_items": incomplete_step_items,
            "can_publish": len(incomplete_steps) == 0,
        }),
    )


# ---------------------------------------------------------------------------
# Portal dashboard (post-onboarding landing page)
# ---------------------------------------------------------------------------

@login_required
def portal_dashboard(request):
    org = getattr(request.user, "organization", None)
    if org is None:
        return redirect("core:home")
    state, _ = OrgOnboardingState.objects.get_or_create(organization=org)
    if not state.is_complete:
        return redirect("organizations:onboarding")
    return render(request, "portal/dashboard.html", {"org": org, "state": state})
