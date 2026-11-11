from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.generic import TemplateView


def saude(request):
    """Usado pelo healthcheck do Compose e para conferir que o app subiu."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("saude/", saude, name="saude"),
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
]
