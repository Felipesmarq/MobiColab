# 0015 — Operadora como atributo da linha

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RD01 (H2), RD02

## Contexto

A hipótese H2 do RD01 diz que a taxa de ar-condicionado "não funcionando" varia entre linhas **e operadoras**. Pelo critério do RD01, cada hipótese precisa apontar a variável que a testa — e nenhum model tinha operadora.

## Decisão

`Linha.operadora` (texto, opcional), preenchido pelos dados abertos ou pelo `agency` do GTFS.

## Alternativas consideradas

- Tirar "operadoras" da H2 — descartada: é um campo barato e é um recorte que interessa à Prefeitura.
- Model `Operadora` separado — descartada para o MVP: não há atributos da operadora além do nome.

## Consequências

- Se a fonte não trouxer a operadora, a H2 é testada só por linha e isso fica registrado como limitação.
