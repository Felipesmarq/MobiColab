# Fontes externas

Arquivos de fontes externas que a camada bronze do pipeline lê (RD03). O conteúdo desta pasta **não vai para o git**: cada arquivo é baixado ou gerado de novo por script, e a bronze guarda a cópia imutável com a data de extração.

| Pasta | Fonte | Como obter |
| --- | --- | --- |
| `gtfs/grande-recife.zip` | GTFS oficial do Grande Recife ([ADR 0029](../../docs/decisoes/0029-gtfs-oficial-do-grande-recife.md)) | Baixar `https://www.granderecife.pe.gov.br/gtfs/gtfs.zip` e rodar `python manage.py importar_gtfs dados/externos/gtfs/grande-recife.zip` |
| `temperatura/inmet_A301.csv` | Temperatura horária do INMET, estação Recife | Baixar o ano em `portal.inmet.gov.br/dadoshistoricos` pelo navegador e rodar `python manage.py importar_inmet <zip>` |
| `temperatura/temperatura_mock.csv` | Temperatura sintética das horas sem medição | Gerado pelo `gerar_mock` |
| `inmet/` (opcional) | CSV bruto da estação, se quiser guardar | Extraído do ZIP anual |
