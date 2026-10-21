# MobiColab

Passageiros do transporte público do Recife reportam, em poucos toques, a lotação, a climatização e a acessibilidade do veículo em que estão — e outros passageiros consultam esses relatos para decidir se embarcam ou esperam o próximo.

- **Spec (fonte da verdade):** [`docs/spec.md`](docs/spec.md)
- **Decisões e seus porquês:** [`docs/decisoes/`](docs/decisoes/README.md)
- **Trilha de dados:** [`docs/dados/`](docs/dados/)

## Onde fica cada coisa

| Pasta | O que tem | Quem mexe |
| --- | --- | --- |
| [`src/`](src/) | Aplicação Django: `config`, `contas`, `transporte`, `relatos`, `templates` | Backend |
| [`tests/`](tests/) | Testes automatizados (um arquivo por RF) | Backend |
| `dados/` | Mock, pipeline, notebooks e dashboard Streamlit (a partir da fase 1) | Dados (CC) |
| [`docs/`](docs/) | Spec, documentos de dados (RD) e decisões (ADR) | Todos |
| [`docker/`](docker/) | Dockerfile e entrypoint | Backend |

Os arquivos soltos na raiz (`manage.py`, `compose.yaml`, `pyproject.toml`, `uv.lock`, `.env.example`) ficam ali porque as ferramentas os procuram na raiz. Detalhes em [ADR 0024](docs/decisoes/0024-organizacao-do-repositorio.md).

## Como rodar

Pré-requisito: [Docker](https://docs.docker.com/engine/install/) com o plugin Compose.

```bash
cp .env.example .env
docker compose up
```

O site sobe em <http://localhost:8000> e o Admin em <http://localhost:8000/admin/>. Em outro terminal:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py loaddata linhas_dev
```

### Sem Docker (opcional)

Com [uv](https://docs.astral.sh/uv/) instalado e um PostgreSQL 16 acessível (ajuste `DATABASE_URL` no `.env`):

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

## Testes e qualidade

```bash
docker compose exec web pytest
uv run ruff check . && uv run ruff format --check .
```

## Como contribuir

1. Pegue uma issue no quadro do projeto. Toda issue cita o requisito da spec (RF, RN, RNF ou RD).
2. Crie uma branch curta a partir da `main` (ex.: `rf03-envio-relato`).
3. Escreva o teste do critério de aceite antes do código.
4. Abra um PR em português. O CI precisa estar verde e um colega precisa aprovar.
5. Se o código precisar de algo que a spec não diz, atualize a spec no mesmo PR. Se tomar uma decisão relevante, registre um ADR em `docs/decisoes/`.

## Licença

[MIT](LICENSE)
