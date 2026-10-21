from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from transporte.models import Linha, Sentido


# Valores de cada dimensão (RN01).
class Lotacao(models.TextChoices):
    VAZIO = "vazio", "Vazio"
    MODERADO = "moderado", "Moderado"
    LOTADO = "lotado", "Lotado"


class ConfortoTermico(models.TextChoices):
    FRIO = "frio", "Frio"
    AGRADAVEL = "agradavel", "Agradável"
    QUENTE = "quente", "Quente"


class ArCondicionado(models.TextChoices):
    FUNCIONANDO = "funcionando", "Funcionando"
    NAO_FUNCIONANDO = "nao_funcionando", "Não funcionando"
    SEM_AR = "sem_ar", "Sem ar"


class VagaPcd(models.TextChoices):
    DISPONIVEL = "disponivel", "Disponível"
    OCUPADA = "ocupada", "Ocupada"


def _no_dominio(campo, choices, opcional=False):
    """Restrição de banco que mantém o campo dentro dos valores da RN01."""
    valores = list(choices.values) + ([""] if opcional else [])
    return models.CheckConstraint(
        condition=Q(**{f"{campo}__in": valores}), name=f"relato_{campo}_valido"
    )


class Relato(models.Model):
    """Condições de uma linha, num sentido, informadas por um passageiro num instante.

    Nunca é apagado (RN07): a substituição (RN05, ADR 0013) marca `substituido_por`
    e a moderação (RF07, ADR 0014) preenche `removido_em`.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="relatos"
    )
    linha = models.ForeignKey(Linha, on_delete=models.PROTECT, related_name="relatos")
    sentido = models.CharField(max_length=5, choices=Sentido.choices)

    lotacao = models.CharField("lotação", max_length=10, choices=Lotacao.choices)
    conforto_termico = models.CharField(
        "conforto térmico", max_length=10, choices=ConfortoTermico.choices, blank=True
    )
    ar_condicionado = models.CharField(
        "ar-condicionado", max_length=16, choices=ArCondicionado.choices, blank=True
    )
    vaga_pcd = models.CharField("vaga PCD", max_length=10, choices=VagaPcd.choices, blank=True)
    prefixo_veiculo = models.CharField("prefixo do veículo", max_length=20, blank=True)

    criado_em = models.DateTimeField(default=timezone.now)

    substituido_por = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substituiu",
        verbose_name="substituído por",
    )

    removido_em = models.DateTimeField(null=True, blank=True)
    removido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relatos_removidos",
    )
    motivo_remocao = models.CharField("motivo da remoção", max_length=200, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["linha", "sentido", "criado_em"], name="relato_status_idx"),
            models.Index(fields=["criado_em"], name="relato_criado_em_idx"),
        ]
        constraints = [
            _no_dominio("lotacao", Lotacao),
            _no_dominio("conforto_termico", ConfortoTermico, opcional=True),
            _no_dominio("ar_condicionado", ArCondicionado, opcional=True),
            _no_dominio("vaga_pcd", VagaPcd, opcional=True),
            _no_dominio("sentido", Sentido),
        ]

    def __str__(self):
        return f"{self.linha.codigo} ({self.get_sentido_display()}) – {self.get_lotacao_display()}"

    @property
    def removido(self):
        return self.removido_em is not None


class Confirmacao(models.Model):
    """Voto de outro passageiro dizendo se um relato ainda vale (RF05, RN06)."""

    relato = models.ForeignKey(Relato, on_delete=models.CASCADE, related_name="confirmacoes")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="confirmacoes"
    )
    ainda_vale = models.BooleanField()
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "confirmação"
        verbose_name_plural = "confirmações"
        constraints = [
            models.UniqueConstraint(
                fields=["relato", "usuario"], name="confirmacao_unica_por_usuario"
            ),
        ]

    def __str__(self):
        voto = "ainda vale" if self.ainda_vale else "não vale mais"
        return f"{self.usuario} – {voto} – relato {self.relato_id}"
