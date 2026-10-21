# 0017 — Stack e ferramentas de desenvolvimento

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** Seção 8 da spec, RNF06, RNF07

## Contexto

Dez pessoas vão trabalhar no mesmo código; o ambiente precisa ser igual para todos e as versões, estáveis até dezembro.

## Decisão

- **Python 3.12**, **Django 5.2 LTS**, Django REST Framework, **PostgreSQL 16**.
- **uv** para dependências (`pyproject.toml` + `uv.lock`).
- **ruff** para lint e formatação.
- **pytest-django** + **coverage** para testes.

## Alternativas consideradas

- pip + `requirements.txt` — descartada: sem lock confiável e mais lento.
- Poetry — descartada: o uv é mais rápido e já cuida da versão do Python.
- Django 5.1 — descartada: a 5.2 é LTS.
- black + flake8 + isort — descartada: o ruff faz os três.

## Consequências

- Quem não usa Docker instala só o `uv` e roda `uv sync`.
- O CI usa as mesmas versões.
