# 0020 — Integração contínua no GitHub Actions

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RNF06, RNF07, RD03

## Contexto

A `main` é protegida e todo merge passa por PR. O CI precisa pegar os erros mais comuns antes da revisão.

## Decisão

O workflow `.github/workflows/ci.yml` roda em todo PR e push na `main`:

1. `ruff check` e `ruff format --check`.
2. `python manage.py makemigrations --check --dry-run` (migration esquecida falha).
3. `pytest` com cobertura, contra um serviço PostgreSQL 16.
4. `docker compose build`.

O mínimo de 80% de cobertura em `src/relatos/regras.py` (RNF06) entra na fase 1, quando o arquivo existir. Os testes de qualidade do pipeline (RD03) entram no mesmo workflow.

## Alternativas consideradas

- Testes com SQLite no CI — descartada: o comportamento difere do PostgreSQL (schemas, constraints).

## Consequências

- O check do CI é obrigatório para o merge.
