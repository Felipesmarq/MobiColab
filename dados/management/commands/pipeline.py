from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dados.pipeline import bronze, ouro, prata, qualidade


class Command(BaseCommand):
    help = "Executa o pipeline de dados bronze → prata → ouro e os testes de qualidade (RD03)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sem-bronze",
            action="store_true",
            help="Não lê a origem; só reconstrói as camadas seguintes a partir da bronze",
        )

    def handle(self, *args, **opcoes):
        # Tudo numa transação: se a qualidade falhar, nada desta execução fica gravado.
        with transaction.atomic():
            if not opcoes["sem_bronze"]:
                self.stdout.write("Bronze (versões novas / linhas lidas):")
                for tabela, (lidas, novas) in bronze.executar().items():
                    self.stdout.write(f"  bronze.{tabela}: {novas} / {lidas}")
            self.stdout.write("Prata (linhas):")
            for tabela, linhas in prata.executar().items():
                self.stdout.write(f"  prata.{tabela}: {linhas}")
            self.stdout.write("Ouro (linhas):")
            for tabela, linhas in ouro.executar().items():
                self.stdout.write(f"  ouro.{tabela}: {linhas}")

            falhas = qualidade.verificar()
            if falhas:
                lista = "\n".join(f"  - {falha}" for falha in falhas)
                raise CommandError(
                    f"{len(falhas)} teste(s) de qualidade falharam; nada foi gravado:\n{lista}"
                )
        self.stdout.write(self.style.SUCCESS("Testes de qualidade: tudo certo."))
        self.stdout.write(self.style.SUCCESS("Pipeline concluído."))
