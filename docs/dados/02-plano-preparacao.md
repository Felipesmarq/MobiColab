# RD02 — Plano de Preparação de Dados

> **Status: rascunho para revisão da equipe de CC.** Entregável 2 da trilha de Análise e Visualização de Dados (fase 1), junto com o pipeline do RD03. Requisito e critérios de aceite: RD02 em [`docs/spec.md`](../spec.md). Perguntas e hipóteses: [RD01](01-plano-analise.md).

Este documento diz **de onde vem cada dado, como ele falta e o que fazemos com ele antes da análise**. A implementação está no pipeline ([`dados/pipeline/`](../../dados/pipeline/), [ADR 0026](../decisoes/0026-desenho-do-pipeline.md)); aqui fica o porquê de cada decisão.

## 1. Fontes

| Fonte | Conteúdo | Formato | Período coberto | Status de validação | Uso |
| --- | --- | --- | --- | --- | --- |
| **Relatos mockados** (`dados/mock/`) | Usuários, relatos (com substituições e remoções) e confirmações, no mesmo esquema do app | Gravados no banco do app por `manage.py gerar_mock`; parâmetros em `config.yaml` | 28 dias terminando na data pedida (`periodo.dias`, `--fim`) | **Validado** pelos testes do gerador (`tests/test_rd02_mock_*.py`): RN05, RN06 e padrões programados conferidos | H1–H4 no MVP ([ADR 0006](../decisoes/0006-mvp-sobre-dados-mockados.md)) |
| **Linhas e paradas de desenvolvimento** (`src/transporte/fixtures/linhas_dev.json`) | 5 linhas (ônibus, BRT, metrô) e 9 paradas, com itinerário | JSON (fixture do Django) | Retrato fixo, sem data | **Aproximado**: nomes e destinos reais, coordenadas aproximadas. Serve só para desenvolvimento e testes | Dimensão de linha até a importação real |
| **GTFS oficial do Grande Recife** ([ADR 0029](../decisoes/0029-gtfs-oficial-do-grande-recife.md)) | 400 linhas, 11 operadoras, 7.237 paradas e itinerários de ônibus, metrô e VLT | GTFS estático (ZIP com 12 arquivos), importado por `manage.py importar_gtfs` | Versão `v2026.11.16`; calendário de 01/05/2020 a 16/11/2027 | **Validado** em 18/11/2026 (#25), com as ressalvas da seção 1.1 | Dimensões de linha, operadora (H2) e terminal (H1) |
| **INMET, estação A301 (Recife)** | Temperatura horária (bulbo seco) | CSV do INMET (latin-1, `;`, vírgula decimal, hora UTC), convertido por `manage.py importar_inmet` para `dados/externos/temperatura/inmet_A301.csv` | Arquivo de 01/01 a 31/10/2026; **medições de 21/05 a 31/10/2026** (3.917 horas) | **Validado** em 18/11/2026 (#26), seção 1.2 | H3 e calibração do mock; o gerador usa a temperatura medida quando existe |
| Frota climatizada por linha | Se a linha opera com ar | A pedir à Prefeitura | — | Não solicitado (decisão futura, spec seção 12) | H2, H3 e calibração |
| Relatos de usuários reais | Os mesmos campos do mock | PostgreSQL (app) | Depois do lançamento | Não se aplica no MVP | Repetir H1–H4 com dados reais |

**Como validar uma fonte (#25 e #26).** Para cada arquivo, registrar aqui: endereço de onde veio, data de download, período coberto, número de registros, colunas recebidas × esperadas, e o que estava fora do esperado. Só depois disso a coluna "Status" vira "Validado".

### 1.1 Validação do GTFS do Grande Recife (#25)

| Item | Resultado |
| --- | --- |
| Origem | `https://www.granderecife.pe.gov.br/gtfs/gtfs.zip`, publicado pelo Grande Recife Consórcio de Transporte (catalogado no [Transitland](https://www.transit.land/data/feeds/f-7nx-granderecife) como `f-7nx-granderecife`). Os portais de dados abertos de PE e do Recife não têm mais a versão antiga prevista no ADR 0005 |
| Download | 18/11/2026; 38,1 MB; SHA-256 `932e8c9578345685c66f89ec018f28821638850e60839e7b8f3b6b66d2de4bb7`; arquivo modificado no servidor em 16/11/2026 |
| Versão e período | `feed_version = v2026.11.16`; `feed_start_date` 01/05/2020, `feed_end_date` 16/11/2027 |
| Arquivos | `agency`, `calendar`, `calendar_dates`, `fare_attributes`, `fare_rules`, `feed_info`, `routes`, `shapes`, `stops`, `stop_times` (208 MB), `transfers`, `trips`. Todos os que o importador exige estão presentes |
| Operadoras | 11 (10 de ônibus + CBTU/Metrorec). Todas as rotas têm `agency_id` |
| Linhas | 400: 395 ônibus (`route_type 3`), 3 metrô (`1`), 2 VLT (`0`). Nenhum `route_short_name` vazio ou repetido; nenhum código acima do limite do modelo |
| Paradas | 7.237, todas com coordenadas dentro da RMR (lat −8,56 a −7,73; lon −35,20 a −34,82); 30 estações (`location_type 1`); nenhum `stop_id` repetido |
| Viagens | 87.182, com `direction_id` 0 e 1 equilibrados; 8 linhas sem nenhuma viagem |
| Importação | 398 linhas (o VLT fica de fora), 7.237 paradas e 31.786 trechos de itinerário em cerca de 13 s; rodar de novo não duplica nada |

**O que estava fora do esperado, e o que fizemos:**

| Achado | Tamanho | Tratamento |
| --- | --- | --- |
| Nome de parada é só o código ("130220") | 6.730 de 7.237 paradas (93%) | Mantido como está (é o que a fonte tem). Para o **destino**, o importador usa a última parada do percurso que tem nome, e o nome da linha se nenhuma tiver (22 linhas). Antes da correção, 228 linhas mostravam um código como destino |
| Nomes de parada terminam com o código ("Terminal De Piedade - 010307") | Todas as paradas nomeadas | O importador tira o sufixo; o código continua em `gtfs_stop_id` |
| `trip_headsign` é "Principal" nos ônibus | Quase todas as viagens de ônibus | Não serve de destino; ignorado |
| BRT não é identificável | 0 linhas com "BRT" | Todas entram como ônibus. Marcar BRT exige uma lista do Grande Recife (pendência na spec, seção 12) |
| VLT (`route_type 0`) | 2 linhas | Fora do MVP, como novo modal futuro (RNF08) |
| Linhas sem viagem | 8 | Importadas sem itinerário; não aparecem como passando por terminal |
| Paradas sem nenhuma linha | 234 | Importadas; não afetam a análise |
| Memória da importação | cerca de 2 GB | Funciona; otimizar lendo o `stop_times.txt` em fluxo |

**Status: validado.** A fonte serve para o MVP. Os limites (BRT, nomes de parada) são declarados nas análises.

### 1.2 Validação da temperatura do INMET (#26)

| Item | Resultado |
| --- | --- |
| Origem | Dados históricos do INMET, arquivo anual `2026.zip` (`portal.inmet.gov.br/uploads/dadoshistoricos/2026.zip`, 81,8 MB, 634 estações, "até 31/10/2026"); estação automática **A301 – Recife** (lat −8,019; lon −34,944; altitude 10 m) |
| Download | 18/11/2026 pelo navegador (o portal recusa clientes automáticos); SHA-256 do ZIP `e50640dee9556273fcdf02874fc88518c5a82a377e3780eb0fcdf202cb9006fd` |
| Formato | CSV `INMET_NE_PE_A301_RECIFE_01-01-2026_A_31-10-2026.CSV`: latin-1, `;`, vírgula decimal, 8 linhas de metadados, `Data` `AAAA/MM/DD`, `Hora UTC` `HHMM UTC`, hora sem medição vazia. Usamos a coluna `TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)` |
| Fuso | UTC no arquivo; convertido para America/Recife só na prata (L1) |
| Faixa de valores | 19,0 a 32,6 °C; média de 25,9 °C. Nenhum valor fora do plausível para Recife |
| Conversão | `python manage.py importar_inmet ~/Downloads/2026.zip` (aceita o ZIP anual ou o CSV) grava `dados/externos/temperatura/inmet_A301.csv` no formato da bronze e imprime as lacunas |

**Lacunas medidas** (período do arquivo: 7.296 horas):

| Lacuna | Horas | Tratamento (L11) |
| --- | --- | --- |
| Estação sem medir de 01/01 a 21/05/2026 | 3.377 | Fica ausente (`fonte = ausente`). Não afeta o MVP: o mock e a EDA usam outubro e novembro |
| 2 lacunas de 1 h entre 21/05 e 31/10 | 2 | Interpoladas na prata |
| Depois de 31/10/2026 | — | O arquivo anual só vai até 31/10. Horas posteriores usam a temperatura sintética do mock, calibrada com outubro |

**Regra de interpolação: confirmada em até 2 h.** No período com medição, todas as lacunas têm 1 h, e a temperatura varia em média menos de 1 °C de uma hora para a outra (ruído de 0,84 °C em outubro). A falha longa do início do ano é de equipamento, sem relação com a temperatura (MCAR), e não deve ser interpolada.

**Calibração do mock** (outubro/2026): média de 27,3 °C (antes 27,0), semi-amplitude de 3,49 °C (antes 3,5), hora mais quente 12h (antes 13h), desvio entre dias de 0,59 °C (antes 1,0) e ruído horário de 0,84 °C (antes 0,5).

Além disso, **o gerador passa a usar a temperatura medida** quando há arquivo real em `dados/externos/temperatura/`. O conforto térmico do mock segue então a mesma temperatura que a prata mostra: com outubro do INMET, 645 das 672 horas do mock são reais, e a associação temperatura × "quente" (H3) segue forte (Spearman ρ = 0,76).

**Status: validado.**

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
| `operadora` (linha) | Categórica | 11 operadoras no GTFS | Não no GTFS oficial (100% preenchida); sim na fixture de desenvolvimento | Falta da fonte, não do relato | H2 testável por operadora com o GTFS |
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
| L10 | Operadora vazia vira **`nao_informada`** | `operadora` | Falta da fonte de linhas, não do relato; a linha continua na análise por linha. Com o GTFS oficial não acontece; segue valendo para a fixture e para linhas cadastradas à mão |
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
| `temperatura`, `conforto_termico.temperatura_referencia` | Média de 27,3 °C, semi-amplitude de 3,5 °C, pico às 12h, variação entre dias e ruído | **INMET A301, outubro/2026** (#26). Só vale nas horas sem medição: com o INMET presente, o gerador usa a temperatura real | — |
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

1. ~~**#25:** validar o GTFS~~ (feito, seção 1.1). Falta a lista de linhas BRT.
2. ~~**#26:** validar a série do INMET~~ (feito, seção 1.2). O arquivo anual só vai até 31/10: baixar de novo quando o INMET publicar novembro.
3. **EDA (RD04):** confirmar ou ajustar estas decisões. O que mudar volta para este documento e para o pipeline.
