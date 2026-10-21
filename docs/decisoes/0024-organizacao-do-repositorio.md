# 0024 — Organização do repositório por frente de trabalho

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** Seção 8 da spec

## Contexto

Com as apps Django soltas na raiz (`config/`, `contas/`, `transporte/`, `relatos/`, `painel/`, `api/`, `templates/`) e, a partir da fase 1, as pastas da trilha de dados (`analytics/`, `notebooks/`, `dados/`), a raiz ficaria com mais de dez pastas misturadas com arquivos de configuração. É difícil saber onde cada frente trabalha. Além disso, `painel/` e `api/` eram apps vazias.

## Decisão

- **`src/`** guarda todo o código Django: `config/`, as apps de domínio e `templates/`.
- **`dados/`** guarda toda a trilha de CC: `mock/`, `pipeline/`, `notebooks/` e `dashboard/` (o app Streamlit).
- **`docs/`** guarda a spec, os documentos de dados e os ADRs.
- **`docker/`** guarda o `Dockerfile` e o entrypoint.
- **Ficam na raiz** só os arquivos que as ferramentas procuram lá: `manage.py`, `compose.yaml`, `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`, `.env.example`, além de `tests/`.
- **Apps a menos:** a API de cada domínio fica no `api.py` da própria app, e as rotas são reunidas em `src/config/urls.py`. O "Painel" (RF06) é um item de menu, sem app própria. O MVP passa de cinco para três apps (`contas`, `transporte`, `relatos`).

O `manage.py` continua na raiz e coloca `src/` no caminho de importação, então os comandos não mudam (`python manage.py ...`). O pytest faz o mesmo via `pythonpath = ["src"]`.

## Alternativas consideradas

- `manage.py` dentro de `src/` — descartada: todos os comandos passariam a ser `python src/manage.py ...`.
- Manter `api/` como app separada — descartada: separa o serializer do model que ele serializa e cria uma app que depende de todas as outras.

## Consequências

- Quem trabalha no backend mexe em `src/` e `tests/`; quem trabalha em dados mexe em `dados/` e `docs/dados/`.
- Se a API crescer muito, uma app `api` pode voltar num ADR novo.
