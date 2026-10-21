# 0019 — Docker Compose de desenvolvimento

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RNF07

## Contexto

O "pronto" da fase 0 é `docker compose up` subir tudo do zero. As pessoas usam máquinas diferentes.

## Decisão

Um único `compose.yaml` com dois serviços na fase 0:

- `db`: `postgres:16`, com healthcheck e volume persistente.
- `web`: imagem do projeto (Python 3.12 + uv), código montado como volume, entrypoint que roda `migrate` antes do `runserver`.

Streamlit e Redis entram nas fases em que forem usados. O deploy público é decidido na fase 2, em ADR próprio.

## Alternativas consideradas

- Compose separado para produção desde já — descartada: ainda não há onde publicar.

## Consequências

- Alterar o código recarrega o servidor sem rebuild.
- `docker compose exec web python manage.py loaddata linhas_dev` carrega a fixture.
