# 0022 — Repositório público com licença MIT

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** —

## Contexto

Em conta gratuita do GitHub, proteção de branch só funciona em repositório público. O projeto tem a Prefeitura do Recife como parceira e não contém segredos nem dados pessoais (o MVP usa dados mockados).

## Decisão

O repositório `Felipesmarq/MobiColab` é **público**, com licença **MIT**.

## Alternativas consideradas

- Repositório privado — descartada: sem proteção de branch no plano gratuito.
- Sem licença — descartada: juridicamente equivale a "todos os direitos reservados", o que impede a Prefeitura de reaproveitar o código.

## Consequências

- Nenhum segredo ou dado real de usuário entra no repositório (`.env` no `.gitignore`).
