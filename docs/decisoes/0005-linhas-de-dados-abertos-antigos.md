# 0005 — Linhas e paradas a partir dos dados abertos antigos de PE

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RD02, RF02

## Contexto

Não há GTFS atualizado do Grande Recife disponível publicamente. O portal de dados abertos de Pernambuco tem uma versão antiga de linhas e paradas.

## Decisão

O MVP usa a versão antiga dos dados abertos de PE para linhas e paradas. O GTFS atualizado foi pedido à Prefeitura e substitui a base quando chegar. Se faltar alguma linha, o Admin permite cadastro manual.

## Alternativas consideradas

- Esperar o GTFS atualizado — descartada: travaria o desenvolvimento.
- Cadastrar tudo à mão — descartada: são centenas de linhas e milhares de paradas.

## Consequências

- Algumas linhas e itinerários podem estar desatualizados; a análise registra isso como limitação.
- `Linha.gtfs_route_id` e `Parada.gtfs_stop_id` permitem atualizar a base sem duplicar registros.
