# Trilha de dados

Tudo o que a equipe de CC produz em código: gerador de dados mockados, pipeline e, nas próximas fases, notebooks e dashboard. Os documentos (RD01, RD02…) ficam em [`docs/dados/`](../docs/dados/).

| Pasta | O que tem | Requisito |
| --- | --- | --- |
| [`mock/`](mock/) | `config.yaml` com os parâmetros do gerador, cada um com a fonte que o justifica | RD02 |
| `externos/` | Arquivos de fontes externas (ex.: temperatura) lidos pela camada bronze. Não vão para o git | RD02, RD03 |

## Dados mockados

O MVP roda sobre dados mockados com o mesmo esquema dos relatos do app ([ADR 0006](../docs/decisoes/0006-mvp-sobre-dados-mockados.md)).

- **Parâmetros:** [`mock/config.yaml`](mock/config.yaml). Todo parâmetro é um par `{valor, fonte}`; a validação em `mock/config.py` recusa parâmetro sem fonte e valores impossíveis.
- **Fontes honestas:** quando não há dado real, a fonte diz "Suposição". Hoje só a fração da frota com ar vem de dado real; temperatura e horários são ordens de grandeza a conferir (issues #26 e pedidos à Prefeitura).
- **O mock só devolve o que foi programado nele.** As hipóteses H1–H4 do [RD01](../docs/dados/01-plano-analise.md) estão embutidas nos parâmetros. Toda análise sobre mock declara isso no título.

Para mudar um parâmetro, edite o `config.yaml` mantendo a fonte atualizada e rode os testes:

```bash
uv run pytest tests/test_rd02_mock_config.py
```
