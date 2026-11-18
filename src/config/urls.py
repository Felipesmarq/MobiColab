from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import path

from contas.views import cadastro
from relatos.api import ConfirmacaoApi, EnvioRelatoApi, StatusLinhaApi
from relatos.views import enviar_relato, status_da_linha, votar_relato
from transporte.api import BuscaLinhaApi
from transporte.views import inicio


def saude(request):
    """Usado pelo healthcheck do Compose e para conferir que o app subiu."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("saude/", saude, name="saude"),
    path("", inicio, name="inicio"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="contas/entrar.html"),
        name="login",
    ),
    path("cadastro/", cadastro, name="cadastro"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("linhas/<int:pk>/", status_da_linha, name="linha_status"),
    path("linhas/<int:pk>/relatar/", enviar_relato, name="enviar_relato"),
    path("relatos/<int:pk>/confirmar/", votar_relato, name="votar_relato"),
    path("api/linhas/", BuscaLinhaApi.as_view(), name="api_linhas"),
    path("api/linhas/<int:pk>/status/", StatusLinhaApi.as_view(), name="api_status_linha"),
    path("api/relatos/", EnvioRelatoApi.as_view(), name="api_relatos"),
    path("api/relatos/<int:pk>/confirmacoes/", ConfirmacaoApi.as_view(), name="api_confirmacoes"),
]
