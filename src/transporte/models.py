from django.db import models
from django.db.models import Q


class Modal(models.TextChoices):
    """Para adicionar um modal, siga docs/decisoes/0016-modais-extensiveis.md."""

    ONIBUS = "onibus", "Ônibus"
    BRT = "brt", "BRT"
    METRO = "metro", "Metrô"


class Sentido(models.TextChoices):
    """Equivale ao `direction_id` do GTFS: IDA = 0, VOLTA = 1 (ADR 0012)."""

    IDA = "ida", "Ida"
    VOLTA = "volta", "Volta"


class Linha(models.Model):
    """Uma linha cobre os dois sentidos; o destino de cada um é o que a interface mostra."""

    codigo = models.CharField("código", max_length=20, unique=True)
    nome = models.CharField(max_length=120)
    modal = models.CharField(max_length=10, choices=Modal.choices)
    operadora = models.CharField(max_length=120, blank=True)
    destino_ida = models.CharField("destino na ida", max_length=120)
    destino_volta = models.CharField(
        "destino na volta", max_length=120, blank=True, help_text="Vazio se a linha for circular."
    )
    ativa = models.BooleanField(default=True)
    gtfs_route_id = models.CharField("GTFS route_id", max_length=64, blank=True)

    class Meta:
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["gtfs_route_id"],
                condition=~Q(gtfs_route_id=""),
                name="linha_gtfs_route_id_unico",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} – {self.nome}"

    @property
    def eh_circular(self):
        return not self.destino_volta

    def destino(self, sentido):
        """Para onde o veículo vai no sentido dado ("060 → Cidade Universitária")."""
        if sentido == Sentido.VOLTA and self.destino_volta:
            return self.destino_volta
        return self.destino_ida


class Parada(models.Model):
    nome = models.CharField(max_length=160)
    lat = models.DecimalField("latitude", max_digits=9, decimal_places=6)
    lon = models.DecimalField("longitude", max_digits=9, decimal_places=6)
    eh_terminal = models.BooleanField("é Terminal Integrado", default=False)
    gtfs_stop_id = models.CharField("GTFS stop_id", max_length=64, blank=True)
    linhas = models.ManyToManyField(Linha, through="LinhaParada", related_name="paradas")

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["gtfs_stop_id"],
                condition=~Q(gtfs_stop_id=""),
                name="parada_gtfs_stop_id_unico",
            ),
        ]

    def __str__(self):
        return self.nome


class LinhaParada(models.Model):
    """Posição de uma parada no itinerário de uma linha, em um sentido."""

    linha = models.ForeignKey(Linha, on_delete=models.CASCADE, related_name="itinerario")
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE, related_name="itinerarios")
    sentido = models.CharField(max_length=5, choices=Sentido.choices)
    ordem = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "parada da linha"
        verbose_name_plural = "paradas da linha"
        ordering = ["linha", "sentido", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["linha", "sentido", "ordem"], name="linhaparada_ordem_unica"
            ),
            models.UniqueConstraint(
                fields=["linha", "parada", "sentido"], name="linhaparada_parada_unica"
            ),
        ]

    def __str__(self):
        return f"{self.linha.codigo} ({self.get_sentido_display()}) #{self.ordem} – {self.parada}"
