from django.core.management.base import BaseCommand
from django.db import transaction

from dados.pipeline import bronze, prata


class Command(BaseCommand):
    help = "Executa o pipeline de dados bronze → prata → ouro (RD03)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sem-bronze",
            action="store_true",
            help="Não lê a origem; só reconstrói as camadas seguintes a partir da bronze",
        )

    def handle(self, *args, **opcoes):
        with transaction.atomic():
            if not opcoes["sem_bronze"]:
                self.stdout.write("Bronze (versões novas / linhas lidas):")
                for tabela, (lidas, novas) in bronze.executar().items():
                    self.stdout.write(f"  bronze.{tabela}: {novas} / {lidas}")
            self.stdout.write("Prata (linhas):")
            for tabela, linhas in prata.executar().items():
                self.stdout.write(f"  prata.{tabela}: {linhas}")
        self.stdout.write(self.style.SUCCESS("Pipeline concluído."))
