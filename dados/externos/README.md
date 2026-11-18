# Fontes externas

Arquivos de fontes externas que a camada bronze do pipeline lê (RD03). O conteúdo desta pasta **não vai para o git**: cada arquivo é baixado ou gerado de novo por script, e a bronze guarda a cópia imutável com a data de extração.

| Pasta | Fonte | Como obter |
| --- | --- | --- |
| `gtfs/grande-recife.zip` | GTFS oficial do Grande Recife ([ADR 0029](../../docs/decisoes/0029-gtfs-oficial-do-grande-recife.md)) | Baixar `https://www.granderecife.pe.gov.br/gtfs/gtfs.zip` e rodar `python manage.py importar_gtfs dados/externos/gtfs/grande-recife.zip` |
| `temperatura/*.csv` | Temperatura horária: mock (`gerar_mock`) ou INMET | Colunas `data_hora` (ISO 8601, com fuso), `temperatura_c`, `fonte` |
