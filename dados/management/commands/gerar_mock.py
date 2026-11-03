from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dados.mock.config import CAMINHO_PADRAO, ConfigInvalida, carregar_config
from dados.mock.gerador import GeracaoInvalida, gerar, limpar_mock


class Command(BaseCommand):
    help = "Gera relatos e confirmações mockados a partir de dados/mock/config.yaml (RD02)."

    def add_arguments(self, parser):
        parser.add_argument("--config", type=Path, default=CAMINHO_PADRAO)
        parser.add_argument("--dias", type=int, help="Sobrescreve periodo.dias")
        parser.add_argument("--semente", type=int, help="Sobrescreve reprodutibilidade.semente")
        parser.add_argument(
            "--fim",
            type=date.fromisoformat,
            help="Último dia do período (AAAA-MM-DD; padrão: hoje)",
        )
        parser.add_argument(
            "--limpar", action="store_true", help="Apaga os dados mockados anteriores antes"
        )

    def handle(self, *args, **opcoes):
        try:
            config = carregar_config(opcoes["config"])
        except ConfigInvalida as erro:
            raise CommandError(str(erro)) from erro
        if opcoes["dias"]:
            config.valores["periodo.dias"] = opcoes["dias"]
        if opcoes["semente"] is not None:
            config.valores["reprodutibilidade.semente"] = opcoes["semente"]

        if opcoes["limpar"]:
            apagados = limpar_mock()
            self.stdout.write(f"Dados mockados anteriores apagados ({apagados} usuários).")

        try:
            resultado = gerar(config, fim=opcoes["fim"])
        except GeracaoInvalida as erro:
            raise CommandError(str(erro)) from erro

        self.stdout.write(
            self.style.WARNING("DADOS MOCKADOS — não representam o comportamento dos passageiros.")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{resultado.usuarios} usuários, {resultado.relatos} relatos "
                f"({resultado.substituidos} substituídos, {resultado.removidos} removidos), "
                f"{resultado.confirmacoes} confirmações e {resultado.contestacoes} contestações."
            )
        )
        self.stdout.write(
            f"Temperatura: {resultado.horas_temperatura} horas em {resultado.arquivo_temperatura}"
        )
