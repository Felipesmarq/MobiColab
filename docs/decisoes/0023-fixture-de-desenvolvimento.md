# 0023 — Fixture de linhas reais para desenvolvimento

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF02, fase 0

## Contexto

A importação completa das linhas fica para a fase 1, mas o Admin e os testes precisam de dados desde a fase 0. A spec prevê um piloto em linhas que passam pela CESAR, no Bairro do Recife.

## Decisão

`transporte/fixtures/linhas_dev.json` traz algumas linhas reais que passam pelo Bairro do Recife (Cais de Santa Rita / Forte do Brum), incluindo ônibus, BRT e metrô, e algumas paradas. Nomes, destinos e coordenadas são **aproximados** e servem só para desenvolvimento.

## Alternativas consideradas

- Linhas inventadas — descartada: dados plausíveis facilitam a revisão de design e os testes de uso.

## Consequências

- A escolha oficial das linhas do piloto continua como próxima ação do grupo (seção 12 da spec).
- A importação da fase 1 substitui esses registros pelo `gtfs_route_id`.
