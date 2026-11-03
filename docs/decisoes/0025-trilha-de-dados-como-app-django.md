# 0025 — Trilha de dados como app Django em `dados/`

- **Data:** 03/11/2026
- **Fase:** 1
- **Status:** aceita
- **Requisitos ligados:** RD02, RD03

## Contexto

O gerador de mock grava relatos no banco do app, e a spec pede o pipeline como `python manage.py pipeline` (RD03). Comandos do `manage.py` precisam morar numa app Django instalada. Pelo ADR 0024, o código da trilha de dados fica em `dados/`, fora de `src/`.

## Decisão

`dados/` vira uma app Django mínima (`dados/apps.py`, registrada em `INSTALLED_APPS`), sem models próprios. Os comandos ficam em `dados/management/commands/` e só chamam a lógica que mora em `dados/mock/` e `dados/pipeline/`. O `manage.py` e o pytest já enxergam a raiz do repositório, então `import dados` funciona sem configuração extra.

Os dados mockados são marcados pelo domínio do e-mail dos usuários (`@mock.mobicolab.invalid`, um domínio reservado que nunca recebe e-mail). O gerador só apaga o que tem essa marca.

## Alternativas consideradas

- Comandos dentro de `src/relatos/` — descartada: mistura o código da equipe de CC com o do backend.
- Scripts soltos (`python dados/mock/gerar.py`) com `django.setup()` manual — descartada: cada script repete a configuração e foge do padrão `manage.py` da spec.
- Campo `eh_mock` em `Relato` — descartada: mudaria o modelo do app só por causa da trilha de dados.

## Consequências

- `python manage.py gerar_mock` e, na próxima task, `python manage.py pipeline` funcionam igual no Docker, no CI e fora deles.
- A cobertura de testes também mede `dados/`.
