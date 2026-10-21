# 0002 — Lotação em três níveis

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RN01, RF03

## Contexto

O relato precisa caber em até 3 toques (RF03). Escalas finas (ex.: 1 a 5) aumentam o tempo de resposta e a divergência entre passageiros sobre o mesmo veículo.

## Decisão

A lotação tem três valores: **vazio · moderado · lotado**. É a única dimensão obrigatória do relato.

## Alternativas consideradas

- Escala de 5 níveis — descartada: mais toques e mais ruído entre relatos do mesmo veículo.
- Percentual estimado — descartada: o passageiro não consegue estimar com precisão.

## Consequências

- O status agregado (RN03) escolhe entre três categorias, o que simplifica o cálculo e o dashboard.
- Análises de lotação (H1) trabalham com variável ordinal de três níveis.
