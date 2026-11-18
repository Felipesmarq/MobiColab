# RD02 — Plano de Preparação de Dados

> **Status: rascunho para revisão da equipe de CC.** Entregável 2 da trilha de Análise e Visualização de Dados (fase 1), junto com o pipeline do RD03. Requisito e critérios de aceite: RD02 em [`docs/spec.md`](../spec.md). Perguntas e hipóteses: [RD01](01-plano-analise.md).

Este documento diz **de onde vem cada dado, como ele falta e o que fazemos com ele antes da análise**. A implementação está no pipeline ([`dados/pipeline/`](../../dados/pipeline/), [ADR 0026](../decisoes/0026-desenho-do-pipeline.md)); aqui fica o porquê de cada decisão.

## 1. Fontes

| Fonte | Conteúdo | Formato | Período coberto | Status de validação | Uso |
| --- | --- | --- | --- | --- | --- |
| **Relatos mockados** (`dados/mock/`) | Usuários, relatos (com substituições e remoções) e confirmações, no mesmo esquema do app | Gravados no banco do app por `manage.py gerar_mock`; parâmetros em `config.yaml` | 28 dias terminando na data pedida (`periodo.dias`, `--fim`) | **Validado** pelos testes do gerador (`tests/test_rd02_mock_*.py`): RN05, RN06 e padrões programados conferidos | H1–H4 no MVP ([ADR 0006](../decisoes/0006-mvp-sobre-dados-mockados.md)) |
| **Linhas e paradas de desenvolvimento** (`src/transporte/fixtures/linhas_dev.json`) | 5 linhas (ônibus, BRT, metrô) e 9 paradas, com itinerário | JSON (fixture do Django) | Retrato fixo, sem data | **Aproximado**: nomes e destinos reais, coordenadas aproximadas. Serve só para desenvolvimento e testes | Dimensão de linha até a importação real |
| **Dados abertos de PE / Grande Recife** (versão antiga) | Linhas, operadoras, paradas e itinerários | GTFS estático (`routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`), importado por `manage.py importar_gtfs` | **A preencher na #25** (data de publicação do arquivo) | **Pendente** (#25): baixar, conferir contagem de linhas, operadoras, `route_type` e coordenadas | Dimensões de linha, operadora (H2) e terminal (H1) |
| **INMET, estação Recife** | Temperatura horária | CSV em `dados/externos/temperatura/` (`data_hora`, `temperatura_c`, `fonte`) | **A preencher na #26** (mesmo período do mock) | **Pendente** (#26): conferir estação, fuso (UTC), lacunas e faixa de valores | H3 e calibração do mock; até lá, a temperatura sintética do mock |
| Frota climatizada por linha | Se a linha opera com ar | A pedir à Prefeitura | — | Não solicitado (decisão futura, spec seção 12) | H2, H3 e calibração |
| Relatos de usuários reais | Os mesmos campos do mock | PostgreSQL (app) | Depois do lançamento | Não se aplica no MVP | Repetir H1–H4 com dados reais |

**Como validar uma fonte (#25 e #26).** Para cada arquivo, registrar aqui: endereço de onde veio, data de download, período coberto, número de registros, colunas recebidas × esperadas, e o que estava fora do esperado. Só depois disso a coluna "Status" vira "Validado".

## 2. Variáveis e mecanismo de falta

Antes de limpar, classificamos por que cada variável pode faltar. A decisão de tratamento sai dessa classificação.

| Variável | Tipo | Domínio (RN01) | Pode faltar? | Mecanismo | Consequência |
| --- | --- | --- | --- | --- | --- |
| `lotacao` | Categórica ordinal | vazio, moderado, lotado | Não (obrigatória) | — | Valor fora do domínio = erro de dado |
| `sentido` | Categórica | ida, volta | Não | — | Idem |
| `criado_em` | Data e hora (UTC) | — | Não (hora do servidor) | — | Precisa de fuso para virar hora local |
| `conforto_termico` | Categórica | frio, agradável, quente | Sim (opcional) | **MNAR provável**: quem sente calor tende a relatar | Não imputar |
| `ar_condicionado` | Categórica | funcionando, não funcionando, sem ar | Sim (opcional) | **MNAR provável**: quem relata o ar tende a fazê-lo quando ele está quebrado | Não imputar; taxa de falha observada fica acima da real |
| `vaga_pcd` | Categórica | disponível, ocupada | Sim (opcional) | **MNAR provável**: depende de quem olha a vaga | Não imputar |
| `prefixo_veiculo` | Texto | — | Sim, quase sempre | Esperado: o passageiro raramente olha o prefixo ([ADR 0003](../decisoes/0003-relato-por-linha-e-sentido.md)) | Análise por veículo só no subconjunto preenchido |
| `operadora` (linha) | Categórica | — | Sim, se a fonte não trouxer | Falta da fonte, não do relato | H2 testada só por linha se faltar |
| Temperatura horária | Numérica (°C) | — | Sim, em falhas de estação | **MCAR provável**: falha de equipamento, sem relação com o valor | Interpolar só lacunas curtas |

## 3. Decisões de limpeza

Cada decisão cita a característica da variável que a justifica. Todas são aplicadas na **camada prata**, reconstruída do zero a partir da bronze a cada execução; a bronze nunca é editada.

| # | Decisão | Variável | Justificativa |
| --- | --- | --- | --- |
| L1 | Converter `criado_em` para o fuso **America/Recife** e derivar `data`, `hora`, `dia_semana`, `fim_de_semana` | `criado_em` | Tipo data/hora gravado em UTC: sem a conversão, um relato das 22h cai no dia seguinte e às 1h, e os picos (H1) saem deslocados 3 horas |
| L2 | Agrupar a hora em **faixas horárias**: madrugada (0–4h), início da manhã (5h), pico da manhã (6–8h), entre picos (9–16h), pico da tarde (17–19h), noite (20–23h) | `hora` | H1 e H4 comparam pico e fora de pico; 24 horas com poucos relatos em cada uma dão taxas instáveis |
| L3 | Relato com valor **fora do domínio da RN01** sai da análise e fica no histórico com `fora_do_dominio` | `lotacao`, `sentido`, opcionais | Categórica de domínio fechado: valor desconhecido não tem como ser interpretado nem corrigido com segurança. O banco do app já impede isso; a regra protege contra dado vindo de outra fonte |
| L4 | **Removidos pela moderação** saem da análise | `removido_em` | Relato removido é abuso ou erro confirmado por um moderador (RF07); mantê-lo distorce as taxas. Continua no histórico (RN07) |
| L5 | **Substituídos** saem da análise | `substituido_por` | Pela RN05, um relato novo do mesmo usuário em até 10 min corrige o anterior; contar os dois seria contar a mesma observação duas vezes |
| L6 | Opcional vazio vira a categoria **`nao_informado`**, sem imputação | `conforto_termico`, `ar_condicionado`, `vaga_pcd` | Falta MNAR: imputar pela moda ou por modelo esconderia o viés. "Não informado" vira categoria e o viés é declarado nas análises |
| L7 | Taxa de falha do ar usa como denominador **só** funcionando + não funcionando | `ar_condicionado` | "Sem ar" não é falha, e "não informado" é MNAR; misturá-los no denominador mudaria a pergunta da H2 |
| L8 | Taxa sem denominador fica **vazia, não zero** | Taxas da ouro | "Ninguém informou" é diferente de "ninguém viu o problema" |
| L9 | Análise por veículo usa só o subconjunto com **prefixo preenchido** | `prefixo_veiculo` | Falta esperada e em massa (cerca de 90%); o subconjunto é pequeno e isso é declarado |
| L10 | Operadora vazia vira **`nao_informada`** | `operadora` | Falta da fonte de linhas, não do relato; a linha continua na análise por linha |
| L11 | Temperatura: lacunas de **até 2 h** interpoladas no tempo; maiores ficam vazias (`fonte = ausente`) | Temperatura | MCAR e variação suave de hora em hora: 2 h de interpolação têm erro pequeno; acima disso, o valor inventado pesaria na H3 |
| L12 | Quando há duas fontes para a mesma hora, **INMET tem prioridade sobre o mock** | Temperatura | Dado real medido vale mais que o sintético |
| L13 | Linha ganha `passa_por_terminal` por sentido, a partir das paradas com `eh_terminal` | Itinerário | H1 compara linhas que chegam ou não aos Terminais Integrados |

**O que não fazemos, e por quê.**

- **Não removemos relatos de usuários com volume alto.** Volume alto pode ser um usuário assíduo. Quem decide é a moderação (L4), e a EDA (RD04) aponta os candidatos.
- **Não deduplicamos relatos parecidos de usuários diferentes.** Dois passageiros no mesmo ônibus são duas observações. É o que dá força ao status (RN03).
- **Não corrigimos lotação por linha ou horário.** Seria imputar o que queremos descobrir (H1).

## 4. Parâmetros do gerador de mock

Cada parâmetro está documentado em [`dados/mock/config.yaml`](../../dados/mock/config.yaml) como um par `{valor, fonte}`, e a validação em `dados/mock/config.py` recusa parâmetro sem fonte. Resumo:

| Grupo | O que controla | Fonte real | Suposição do grupo |
| --- | --- | --- | --- |
| `climatizacao.fracao_frota_com_ar` | 16,3% dos veículos com ar | **Grande Recife**: 401 de 2.462 ônibus (RD01) | — |
| `temperatura`, `conforto_termico.temperatura_referencia` | Temperatura média de 27 °C, amplitude diária | Ordem de grandeza do INMET; a conferir na #26 | Amplitude, hora do pico, ruído |
| `volume`, `lotacao` | Perfil horário, picos 6–8h e 17–19h, efeito dos terminais | — | Sim, alinhado à H1; substituir pela demanda por linha da Prefeitura |
| `climatizacao.prob_falha*` | 25% de falha média do ar, variando entre linhas | — | Sim, alinhado à H2 |
| `conforto_termico` | "Quente" cresce com a temperatura, mais sem ar | — | Sim, alinhado à H3 |
| `vaga_pcd` | Ocupação acompanha a lotação | — | Sim, alinhado à H4 |
| `preenchimento` | Quanto cada opcional é informado, incluindo o MNAR do ar | — | Sim, implementa o mecanismo da seção 2 |
| `usuarios`, `interacoes` | Atividade, trolls, substituições, votos, remoções | — | Sim, para a EDA ter anomalias a encontrar (RD04) |

**Limite do mock.** O gerador só devolve os padrões programados nele. Achados sobre mock validam o pipeline e as visualizações, não o comportamento dos passageiros. Toda análise sobre mock declara isso no título.

## 5. Onde cada decisão é conferida

| Decisão | Teste |
| --- | --- |
| L1, L2 | `tests/test_rd03_pipeline_prata.py` (hora local, madrugada vira o dia anterior, faixas) |
| L3–L6 | `tests/test_rd03_pipeline_prata.py` (removidos, substituídos, fora do domínio, `nao_informado`) |
| L7, L8 | `tests/test_rd03_pipeline_ouro.py` |
| L11, L12 | `tests/test_rd03_pipeline_prata.py` (lacunas de 2 h e de 4 h, prioridade do INMET) |
| Tudo, a cada execução | `dados/pipeline/qualidade.py`: contagens entre camadas, nulos, domínios, unicidade e privacidade; falha o CI |

## 6. Pendências

1. **#25:** validar o GTFS dos dados abertos e preencher período e status na seção 1.
2. **#26:** validar a série do INMET, preencher período e status, e recalibrar `temperatura` no `config.yaml`.
3. **EDA (RD04):** confirmar ou ajustar estas decisões. O que mudar volta para este documento e para o pipeline.
