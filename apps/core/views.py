from django.shortcuts import render

from .models import SupportStream


def home(request):
    support_streams = SupportStream.objects.all()
    return render(request, "public/home.html", {
        "support_stream_names": [s.name for s in support_streams],
    })
