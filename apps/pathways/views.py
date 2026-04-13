from django.shortcuts import get_object_or_404, render

from .models import Pathway


def pathway_list(request):
    """Public listing of all published pathways."""
    pathways = Pathway.objects.filter(is_published=True).prefetch_related(
        "sections"
    ).order_by("display_order", "title")
    return render(request, "public/pathways/list.html", {"pathways": pathways})


def pathway_detail(request, slug):
    """Full pathway page with sections and guide items."""
    pathway = get_object_or_404(Pathway, slug=slug, is_published=True)
    sections = pathway.sections.prefetch_related("guide_items").order_by("display_order")
    return render(request, "public/pathways/detail.html", {
        "pathway": pathway,
        "sections": sections,
    })
