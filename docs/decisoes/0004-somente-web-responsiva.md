# 0004 — Somente versão web responsiva no MVP

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RNF01, RNF03

## Contexto

O público usa o celular no ponto ou dentro do veículo. O prazo é curto e o grupo já trabalha com Django.

## Decisão

O MVP é uma aplicação web responsiva, mobile-first (360 px, uso com uma mão). Sem PWA e sem app nativo.

## Alternativas consideradas

- App nativo — descartada: exige outra stack, publicação nas lojas e mais tempo.
- PWA com envio offline — descartada para o MVP: o RNF03 é atendido com mensagem clara e formulário preservado; o modo offline fica para depois.

## Consequências

- Interface server-rendered com HTMX e Tailwind (seção 8 da spec).
- Sem notificações push no MVP.
