from django.apps import AppConfig


class DadosConfig(AppConfig):
    """Trilha de dados: gerador de mock e pipeline, como comandos do manage.py (ADR 0025)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dados"
    verbose_name = "Trilha de dados"
