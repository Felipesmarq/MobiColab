# 0012 — Linha única por código, com sentido no relato e itinerário por parada

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF02, RF03, RF04

## Contexto

A primeira versão da spec tinha `Linha.sentido`, o que fazia "060 ida" e "060 volta" serem duas linhas. Para o passageiro, a linha é uma só, e "ida/volta" não diz nada — ele pensa "sentido Cidade Universitária". Além disso, uma parada precisa saber quais linhas passam por ela, mas uma parada de um lado da rua só atende um sentido.

## Decisão

- `Linha` é única pelo `codigo` e guarda `destino_ida` e `destino_volta` (o bairro ou ponto para onde vai; `destino_volta` vazio para linhas circulares).
- `Sentido` é um `TextChoices` com `IDA` e `VOLTA`, alinhado ao `direction_id` do GTFS (0 e 1).
- `Parada` ↔ `Linha` é muitos-para-muitos, via `LinhaParada`, que guarda `sentido` e `ordem` no itinerário. Únicos: (linha, sentido, ordem) e (linha, parada, sentido).
- `Relato` tem o campo `sentido`. A interface mostra "060 → Cidade Universitária".

## Alternativas consideradas

- Uma linha por sentido — descartada: não corresponde ao modelo mental do passageiro e duplica nome, modal e operadora.
- Muitos-para-muitos simples sem sentido — descartada: não distingue as paradas de cada lado da rua.

## Consequências

- O MVP passa a ter seis models (antes eram cinco).
- O endpoint de status recebe o sentido: `/api/linhas/{id}/status/?sentido=ida`.
- A importação do GTFS (fase 1) preenche `LinhaParada` a partir de `trips` e `stop_times`.
