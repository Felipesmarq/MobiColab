# Trilha de dados

Tudo o que a equipe de CC produz em código: gerador de dados mockados, pipeline e, nas próximas fases, notebooks e dashboard. Os documentos (RD01, RD02…) ficam em [`docs/dados/`](../docs/dados/).

| Pasta | O que tem | Requisito |
| --- | --- | --- |
| [`mock/`](mock/) | `config.yaml` com os parâmetros do gerador, cada um com a fonte que o justifica | RD02 |
| `externos/` | Arquivos de fontes externas (ex.: temperatura) lidos pela camada bronze. Não vão para o git | RD02, RD03 |
| [`pipeline/`](pipeline/) | Pipeline bronze → prata → ouro e o dicionário de dados (`esquemas.py`) | RD03 |
| `management/commands/` | Comandos do `manage.py` da trilha (`gerar_mock`, `pipeline`) | RD02, RD03 |

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

## Pipeline

```bash
python manage.py pipeline              # lê a origem e atualiza as camadas
python manage.py pipeline --sem-bronze # só reconstrói as camadas seguintes a partir da bronze
```

Desenho completo no [ADR 0026](../docs/decisoes/0026-desenho-do-pipeline.md). Colunas, tipos e significado de cada tabela estão em [`pipeline/esquemas.py`](pipeline/esquemas.py).

### Bronze

Cópia imutável da origem, só acrescentada: relatos, confirmações, linhas, paradas, itinerários e a temperatura dos CSVs de `externos/temperatura/`.

- Cada linha tem `_hash` (impressão digital do conteúdo) e `_extraido_em` (execução que a copiou).
- Só entra uma versão nova quando a linha é nova ou mudou na origem (ex.: o relato foi removido pela moderação depois). Rodar duas vezes seguidas não acrescenta nada.
- Linha que some da origem (ex.: `gerar_mock --limpar`) ganha uma versão com `_apagado_na_origem = verdadeiro`.
- Cada relato leva `origem` = `mock` ou `real`. Nenhum dado pessoal (e-mail, nome) chega à bronze.
- `bronze.execucoes` registra cada execução: linhas lidas e versões novas por tabela.

No PostgreSQL as camadas são schemas (`bronze.relatos`); no SQLite local viram prefixo (`bronze__relatos`).

### Prata

Dados limpos, apagados e recriados do zero a cada execução a partir da bronze — nunca da origem.

| Tabela | O que tem |
| --- | --- |
| `prata.relatos` | Relatos válidos para análise, com data, hora e faixa horária no fuso America/Recife, dados da linha, destino, passagem por Terminal Integrado e votos recebidos |
| `prata.relatos_historico` | Todo relato, inclusive removidos (RF07), substituídos (RN05) e fora dos domínios da RN01, com o motivo de cada um ficar fora |
| `prata.confirmacoes` | Votos atuais |
| `prata.linhas` | Cadastro atual de linhas, com a passagem por Terminal Integrado em cada sentido |
| `prata.temperatura` | Série horária única: INMET quando houver, mock senão; lacunas de até 2 h interpoladas, maiores deixadas vazias (`fonte = ausente`) |

Regras de limpeza:

- **Campos opcionais vazios viram `nao_informado`.** Nada é imputado: a falta de informação tem viés (MNAR, RD02) e é uma categoria da análise.
- **Faixas horárias:** madrugada (0–4h), início da manhã (5h), pico da manhã (6–8h), entre picos (9–16h), pico da tarde (17–19h), noite (20–23h).
- **Operadora vazia vira `nao_informada`.**

### Ouro

Fonte única do painel e dos notebooks (RF06, RD04). **Só agregados:** nenhuma tabela tem identificador de relato ou de usuário. Recriada do zero a partir da prata.

| Tabela | Grão | Para quê |
| --- | --- | --- |
| `ouro.relatos_por_hora` | dia × hora × linha × sentido × origem | Base de todos os gráficos e filtros (modal, linha, período, faixa horária). Contagens de cada valor de cada dimensão, votos e a temperatura da hora |
| `ouro.taxas_por_linha` | linha × faixa horária × origem | Taxas das hipóteses: lotado (H1), ar não funcionando (H2), quente (H3) e vaga ocupada (H4) |
| `ouro.qualidade_diaria` | dia × origem | Volume, remoções, substituições, votos, usuários ativos e cobertura de temperatura (página "Qualidade dos dados") |

- **Taxas sempre com numerador e denominador.** Para outro recorte, some as contagens e divida — nunca tire média de taxas.
- **Denominador da falha do ar:** só veículos climatizados com ar informado (funcionando + não funcionando); "sem ar" fica de fora.
- **Taxa sem denominador fica vazia, não zero:** "ninguém informou" é diferente de "ninguém viu".
- **Cuidado com o viés MNAR:** como quem tem o ar quebrado informa mais, a taxa de falha observada sai bem acima da real. Com o mock, a configuração usa falha de 25% e a ouro mostra perto de 50%.

```python
# Exemplo em notebook: ler a ouro direto do banco
import pandas as pd
from django.db import connection

por_hora = pd.read_sql("SELECT * FROM ouro.relatos_por_hora", connection.connection)
```

### Testes de qualidade

Rodam ao fim de toda execução do `pipeline` ([`pipeline/qualidade.py`](pipeline/qualidade.py)). Se uma regra falhar, o comando sai com erro e **nada daquela execução é gravado** — a ouro anterior continua valendo.

| Regra | O que confere |
| --- | --- |
| Contagem | Nada some nem aparece entre camadas: bronze → histórico → relatos válidos → somas da ouro; votos contados batem com os votos da prata |
| Nulo | Colunas obrigatórias de `prata.relatos` e chaves de `ouro.relatos_por_hora` preenchidas (ex.: relato sem linha correspondente) |
| Domínio | Valores da RN01, faixas horárias, hora entre 0 e 23, taxas entre 0 e 1, contagens não negativas |
| Unicidade | Chaves únicas em `prata.relatos` e nas três tabelas da ouro |
| Privacidade | Nenhuma tabela da ouro declara identificador de relato ou de usuário |

No CI, depois do pytest, um passo gera 7 dias de mock no PostgreSQL e roda o pipeline de ponta a ponta: se a qualidade falhar, o build falha.
