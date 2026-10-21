# 0016 — Modais como TextChoices, fáceis de estender

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RNF08

## Contexto

O MVP cobre ônibus, BRT e metrô. O VLT e outros modais ficam para depois, mas o projeto precisa estar preparado para recebê-los.

## Decisão

`Modal` é um `TextChoices` em `src/transporte/models.py` com `ONIBUS`, `BRT` e `METRO`. O mapeamento do `route_type` do GTFS para `Modal` fica concentrado num único lugar (`src/transporte/modais.py`).

**Como adicionar um modal (ex.: VLT):**

1. Acrescentar o valor em `Modal` (ex.: `VLT = "vlt", "VLT"`).
2. Acrescentar o mapeamento GTFS em `src/transporte/modais.py`.
3. Rodar `python manage.py makemigrations` — a migration só muda as opções, sem alterar tabelas.
4. Atualizar a tabela de glossário da spec e, se houver, o ícone na interface.

## Alternativas consideradas

- Tabela `Modal` editável no Admin — descartada: um modal novo quase sempre exige código (ícone, mapeamento GTFS, regras), então editar só no Admin não basta.

## Consequências

- Adicionar um modal é uma tarefa pequena, sem migração de dados.
