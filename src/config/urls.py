from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import path

from contas import views as contas_views
from transporte import views as transporte_views
from transporte.api import BuscaLinhaApi


def saude(request):
    """Usado pelo healthcheck do Compose e para conferir que o app subiu."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("saude/", saude, name="saude"),
    path("", transporte_views.inicio, name="inicio"),
    path("linhas/<int:pk>/", transporte_views.linha_status, name="linha_status"),
    path("cadastro/", contas_views.cadastro, name="cadastro"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="contas/entrar.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/linhas/", BuscaLinhaApi.as_view(), name="api_linhas"),
]
