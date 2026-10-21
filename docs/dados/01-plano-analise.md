# RD01 — Plano de Análise de Dados

> **Status: rascunho para revisão da equipe de CC.** Entregável 1 da trilha de Análise e Visualização de Dados (fase 0). Requisito e critérios de aceite: RD01 em [`docs/spec.md`](../spec.md).

## 1. Problema

Quem usa ônibus, BRT e metrô na Região Metropolitana do Recife não tem informação sobre as condições do próximo veículo — se está lotado, se o ar-condicionado funciona, se a vaga PCD está livre. A espera é às cegas, e o desconforto no calor do Recife empurra as pessoas para o carro e para o transporte por aplicativo.

O desconforto é estrutural: segundo o Grande Recife, dos 2.462 ônibus em circulação no início de 2026, só 401 (cerca de 16%) tinham ar-condicionado ([Diário de Pernambuco](https://www.diariodepernambuco.com.br/amp/vida-urbana/2026/01/11705131-aumento-da-passagem-passageiros-devem-pagar-mais-caro-para-usar-onibus-velhos-e-sem-ar-condicionado.html)).

**Objetivo da análise:** mostrar **onde e quando** o desconforto pesa mais — lotação, calor, ar quebrado e vaga PCD ocupada — para que a Prefeitura do Recife tenha evidência para priorizar linhas e horários.

## 2. Perguntas e hipóteses

Cada hipótese é testável e aponta a variável e a fonte que a testam. As visualizações são **provisórias até a EDA** (RD04).

| Pergunta | Hipótese | Variáveis | Fonte | Visualização provável (provisória) |
| --- | --- | --- | --- | --- |
| **Q1.** Em que linhas e horários a lotação é pior? | **H1.** A lotação se concentra nos picos da manhã e da tarde, nas linhas que chegam aos Terminais Integrados (TIs). | `Relato.lotacao`, `Relato.criado_em` (faixa horária, dia da semana), `Relato.linha`, `Parada.eh_terminal` via `LinhaParada` | Relatos (mock no MVP) + linhas e paradas dos dados abertos de PE | Mapa de calor linha × hora |
| **Q2.** Com que frequência o ar falha em veículos climatizados? | **H2.** A taxa de "não funcionando" varia entre linhas e operadoras. | `Relato.ar_condicionado`, `Relato.linha`, `Linha.operadora` | Relatos (mock) + dados abertos de PE (operadora) | Barras ranqueadas por linha e por operadora |
| **Q3.** O desconforto térmico acompanha a temperatura externa? | **H3.** Os relatos "quente" crescem com a temperatura, com efeito mais forte em veículos sem ar. | `Relato.conforto_termico`, `Relato.ar_condicionado`, `Relato.criado_em`; temperatura horária | Relatos (mock) + INMET, estação Recife | Dispersão com linha de tendência, separada por "com ar" e "sem ar" |
| **Q4.** Quando a vaga PCD está ocupada? | **H4.** A ocupação da vaga PCD acompanha a lotação. | `Relato.vaga_pcd`, `Relato.lotacao`, faixa horária | Relatos (mock) | Barras empilhadas por faixa horária |

**Como cada hipótese será testada (a confirmar na EDA):**

- **H1:** comparar a proporção de relatos "lotado" entre faixas horárias (pico × fora de pico) e entre linhas que passam ou não por TI; associação medida por V de Cramér.
- **H2:** taxa de "não funcionando" sobre relatos com ar informado, por linha e por operadora, com intervalo de confiança; linhas com poucos relatos ficam fora do ranking.
- **H3:** correlação de Spearman entre temperatura e proporção de "quente" por hora, separada por "com ar" e "sem ar".
- **H4:** proporção de "vaga ocupada" por nível de lotação e por faixa horária; V de Cramér entre `vaga_pcd` e `lotacao`.

## 3. Fontes candidatas

Detalhamento, validação e plano de preparação ficam no RD02.

| Fonte | Conteúdo | Formato | Uso | Situação |
| --- | --- | --- | --- | --- |
| Dados mockados (`dados/mock/`) | Relatos com o mesmo esquema do app | Script + `config.yaml` | H1–H4 no MVP | A construir na fase 1 |
| Dados abertos de PE / Grande Recife (versão antiga) | Linhas, operadoras e paradas | CSV | Dimensões de linha, operadora e terminal | Em uso; a validar |
| INMET, estação Recife | Temperatura horária | CSV | H3 e calibração do mock | A validar |
| Frota climatizada por linha | Se a linha opera com ar | A pedir à Prefeitura | H2, H3 e calibração do mock | Não solicitado |
| Relatos de usuários reais | Lotação, clima, ar e vaga PCD por linha e hora | PostgreSQL | Repetir H1–H4 com dados reais | Depois do lançamento |

## 4. Limitações conhecidas

- **Dados mockados.** No MVP, os relatos são gerados por script. O gerador só devolve os padrões programados nele: achados sobre mock **validam o pipeline e as visualizações, não o comportamento dos passageiros**. Toda análise sobre mock declara isso no título.
- **Campos opcionais com viés.** Ar, conforto e vaga PCD são opcionais; quem relata o ar tende a fazê-lo quando ele está quebrado (provável MNAR). A taxa de falha da H2 tende a ser superestimada.
- **Dados de linhas desatualizados.** A base de linhas e paradas é uma versão antiga; itinerários e operadoras podem ter mudado.
- **Operadora pode faltar.** Se a fonte não trouxer a operadora, a H2 é testada só por linha.

## 5. Próximos passos

1. Revisão deste plano pela equipe de CC.
2. RD02 — validar as fontes e escrever o plano de preparação.
3. RD03 — pipeline bronze → prata → ouro.
4. RD04 — EDA, que confirma ou ajusta as visualizações provisórias acima.
