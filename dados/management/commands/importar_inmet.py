from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dados import inmet
from dados.mock.gerador import PASTA_TEMPERATURA


class Command(BaseCommand):
    help = (
        "Converte a temperatura horária do INMET (CSV da estação ou ZIP anual) para "
        "dados/externos/temperatura/, no formato lido pelo pipeline (RD02, issue #26)."
    )

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="CSV de uma estação ou ZIP anual do INMET")
        parser.add_argument("--estacao", default=inmet.ESTACAO_RECIFE, help="Padrão: A301")
        parser.add_argument("--pasta", default=None, help="Padrão: dados/externos/temperatura")

    def handle(self, *args, **options):
        arquivo = Path(options["arquivo"])
        if not arquivo.is_file():
            raise CommandError(f"Arquivo não encontrado: {arquivo}")
        try:
            serie = inmet.ler(arquivo, estacao=options["estacao"])
        except ValueError as erro:
            raise CommandError(str(erro)) from erro
        if serie.empty:
            raise CommandError("Nenhuma hora com temperatura medida no arquivo.")

        destino = inmet.gravar(serie, options["pasta"] or PASTA_TEMPERATURA)
        resumo = inmet.lacunas(serie)
        primeira, ultima = serie["data_hora"].min(), serie["data_hora"].max()
        self.stdout.write(
            f"{serie.attrs['estacao']} {serie.attrs.get('nome_estacao', '')}: arquivo de "
            f"{resumo['inicio']:%d/%m/%Y %H}h a {resumo['fim']:%d/%m/%Y %H}h UTC; "
            f"{len(serie)} horas medidas, de {primeira:%d/%m/%Y %H}h a {ultima:%d/%m/%Y %H}h UTC. "
            f"Gravado em {destino}"
        )
        self.stdout.write(
            f"Lacunas: {resumo['lacunas']} ({resumo['horas_ausentes']} horas). "
            f"Até {inmet.LACUNA_INTERPOLAVEL_H} h, interpoladas na prata: "
            f"{resumo['horas_interpoladas']} h; maiores ficam ausentes: "
            f"{resumo['horas_que_ficam_ausentes']} h; maior lacuna: {resumo['maior_lacuna_h']} h."
        )
