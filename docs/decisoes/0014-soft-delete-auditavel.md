# 0014 — Remoção de relato por soft delete auditável

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF07, RN07

## Contexto

A moderação remove relatos abusivos, mas o histórico é preservado (RN07). A primeira versão previa só um booleano `removido`, que não diz quando nem por quem.

## Decisão

`Relato` recebe `removido_em` (data/hora, nullable), `removido_por` (FK para `Usuario`, nullable) e `motivo_remocao` (texto curto). Um relato está removido quando `removido_em` está preenchido.

## Alternativas consideradas

- Booleano `removido` — descartada: não serve para auditoria nem para o painel de qualidade dos dados.
- Apagar o registro — descartada: viola a RN07.

## Consequências

- O pipeline (prata) filtra por `removido_em` nulo.
- O painel de qualidade pode mostrar volume de remoções por período.
