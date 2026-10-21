# 0001 — Registrar decisões em ADRs

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RD10

## Contexto

O RD10 exige um histórico de decisões criado no momento em que cada decisão é tomada, desde a fase 0. Com um grupo grande, decisões tomadas em conversa se perdem e voltam a ser discutidas.

## Decisão

Toda decisão relevante (arquitetura, modelo de dados, ferramentas, processo, escopo) vira um arquivo curto em `docs/decisoes/`, numerado em sequência (`NNNN-titulo.md`), com contexto, decisão, alternativas e consequências. A spec descreve o *quê*; os ADRs guardam o *porquê*. O índice fica em `README.md`.

Um ADR aceito não é editado para mudar de ideia: cria-se um novo que o substitui, e o antigo passa a status "substituída por NNNN".

## Alternativas consideradas

- Manter as decisões numa tabela dentro da spec — descartada: mistura o estado atual com o histórico e não guarda alternativas nem motivos.
- Registrar só no Trello ou no WhatsApp — descartada: não fica versionado junto do código.

## Consequências

- Cada PR que toma uma decisão relevante inclui o ADR correspondente.
- A documentação final (RD10) aponta para esta pasta.
