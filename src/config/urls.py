from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def saude(request):
    """Usado pelo healthcheck do Compose e para conferir que o app subiu."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("saude/", saude, name="saude"),
]
