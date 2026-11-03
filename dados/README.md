# Trilha de dados

Tudo o que a equipe de CC produz em código: gerador de dados mockados, pipeline e, nas próximas fases, notebooks e dashboard. Os documentos (RD01, RD02…) ficam em [`docs/dados/`](../docs/dados/).

| Pasta | O que tem | Requisito |
| --- | --- | --- |
| [`mock/`](mock/) | `config.yaml` com os parâmetros do gerador, cada um com a fonte que o justifica | RD02 |
| `externos/` | Arquivos de fontes externas (ex.: temperatura) lidos pela camada bronze. Não vão para o git | RD02, RD03 |
| `management/commands/` | Comandos do `manage.py` da trilha (`gerar_mock`) | RD02 |

## Dados mockados

O MVP roda sobre dados mockados com o mesmo esquema dos relatos do app ([ADR 0006](../docs/decisoes/0006-mvp-sobre-dados-mockados.md)).

- **Parâmetros:** [`mock/config.yaml`](mock/config.yaml). Todo parâmetro é um par `{valor, fonte}`; a validação em `mock/config.py` recusa parâmetro sem fonte e valores impossíveis.
- **Fontes honestas:** quando não há dado real, a fonte diz "Suposição". Hoje só a fração da frota com ar vem de dado real; temperatura e horários são ordens de grandeza a conferir (issues #26 e pedidos à Prefeitura).
- **O mock só devolve o que foi programado nele.** As hipóteses H1–H4 do [RD01](../docs/dados/01-plano-analise.md) estão embutidas nos parâmetros. Toda análise sobre mock declara isso no título.

Para mudar um parâmetro, edite o `config.yaml` mantendo a fonte atualizada e rode os testes:

```bash
uv run pytest tests/test_rd02_mock_config.py
```

### Gerar os dados

Com as linhas carregadas (`python manage.py loaddata linhas_dev`):

```bash
python manage.py gerar_mock              # 28 dias terminando hoje
python manage.py gerar_mock --limpar     # apaga o mock anterior e gera de novo
python manage.py gerar_mock --dias 7 --fim 2026-11-01 --semente 1
```

O comando grava usuários, relatos (com substituições e remoções) e confirmações no banco do app, com o mesmo esquema dos dados reais, e escreve a temperatura horária sintética em `externos/temperatura/temperatura_mock.csv`. Com a configuração do repositório, são cerca de 25 mil relatos.

- **Marca de mock:** todo usuário gerado tem e-mail `@mock.mobicolab.invalid`. O `--limpar` só apaga o que tem essa marca; dados reais nunca são tocados.
- **Reprodutível:** a mesma configuração e a mesma data final geram sempre os mesmos dados.
- **Trolls:** uma pequena fração dos usuários relata ao acaso e com volume alto. A moderação remove parte desses relatos — é o que a EDA deve encontrar como anomalia (RD04).
