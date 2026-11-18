# 0029 — GTFS oficial do Grande Recife como fonte de linhas e paradas

- **Data:** 18/11/2026
- **Fase:** 1
- **Status:** aceita (substitui a [0005](0005-linhas-de-dados-abertos-antigos.md))
- **Requisitos ligados:** RD02, RF02, RNF08, ADR 0016

## Contexto

O ADR 0005 partiu de que não havia GTFS atualizado público e adotou a versão antiga dos dados abertos de PE. Na validação das fontes (#25), essa versão não está mais nos portais de dados abertos de Pernambuco nem do Recife.

Em compensação, o próprio Grande Recife Consórcio de Transporte publica um GTFS estático atualizado:
- **Endereço:** `https://www.granderecife.pe.gov.br/gtfs/gtfs.zip`, catalogado no Transitland como `f-7nx-granderecife`.
- **Versão validada:** `v2026.11.16`.
- **Conteúdo:** 400 linhas, 11 operadoras (inclusive o metrô da CBTU), 7.237 paradas e 87 mil viagens.

## Decisão

- O MVP passa a usar esse GTFS como fonte de linhas, operadoras, paradas e itinerários, importado por `manage.py importar_gtfs`.
- O arquivo fica em `dados/externos/gtfs/grande-recife.zip` (fora do git) e é baixado de novo para atualizar. A importação é idempotente pelos IDs do GTFS.
- O pedido de "GTFS atualizado" à Prefeitura deixa de ser necessário.

## Alternativas consideradas

- **Manter a versão antiga dos dados abertos de PE:** descartada. Não está mais publicada e é menos completa que o GTFS oficial.
- **Cadastrar linhas à mão:** descartada pelo mesmo motivo da 0005 (centenas de linhas, milhares de paradas).

## Consequências

- **Operadora:** passa a existir para todas as linhas, o que permite testar a H2 por operadora.
- **Paradas:** a maioria tem como nome só o código ("130220"). O importador tira o código do fim dos nomes ("Terminal De Piedade - 010307" vira "Terminal De Piedade") e usa como destino a última parada com nome. Quando nenhuma tem nome, usa o nome da linha.
- **BRT:** o feed não marca linhas BRT (`route_type 3` para todo ônibus, sem "BRT" no nome). Todas entram como ônibus até haver uma lista de linhas BRT. O mapeamento da ADR 0016 continua valendo.
- **VLT:** as 2 rotas de VLT (`route_type 0`) ficam de fora, como previsto para novos modais (RNF08).
- **Fixture de desenvolvimento:** `linhas_dev.json` continua só para desenvolvimento e testes. Os códigos dela não batem todos com o feed (`SUL` × `Sul`; a 1076 é ônibus "Parador", não BRT).
- **Memória:** a importação do feed completo leva cerca de 13 s e usa cerca de 2 GB de memória, porque lê o `stop_times.txt` (200 MB) inteiro. Funciona, mas é um ponto a otimizar.
