# MobiColab — Spec do MVP (Django)

@Felipe

MobiColab é uma aplicação web em Django onde passageiros do transporte público do Recife reportam, em poucos toques, a lotação, a climatização e a acessibilidade do veículo em que estão — e outros passageiros consultam esses relatos para decidir se embarcam ou esperam o próximo. Esta spec é a fonte da verdade do MVP: todo código nasce de um requisito daqui, e todo requisito tem critério de aceite testável.

## 1. Visão e problema

**Problema.** Falta informação qualitativa e em tempo real sobre as condições dos modais (lotação, ar-condicionado, acessibilidade). Sem ela, o passageiro espera às cegas: estresse, desconforto físico no calor do Recife e uma experiência que empurra as pessoas para carro e transporte por aplicativo.

**Hipótese.** Se o passageiro souber como está o próximo veículo antes de embarcar, ele toma decisões melhores e percebe o transporte público como mais previsível.

**Público-alvo.** Estudantes e trabalhadores da Região Metropolitana do Recife que usam ônibus, BRT e metrô diariamente, fazem baldeação nos Terminais Integrados (TIs) e têm smartphone com internet.

**Parceiro.** Prefeitura do Recife.

**Proposta de valor.** Devolver poder de escolha e previsibilidade: "pego este agora ou espero o próximo?" respondido com dados de quem está dentro do veículo.

## 2. Escopo

O MVP faz uma coisa bem: **reportar e consultar a condição de uma linha agora**. A seção de engenharia reversa do material original (rotas, GPS/ETA, alertas de percurso) descreve como apps de mobilidade existentes funcionam — é benchmark, não escopo inicial.

| Item | No MVP? | Observação |
| --- | --- | --- |
| Relato de lotação, climatização e acessibilidade | Sim | Núcleo do produto |
| Consulta do status agregado por linha e sentido | Sim | Núcleo do produto |
| Confirmação / contestação de relatos ("ainda está assim?") | Sim | Combate a dados velhos e trollagem |
| Cadastro e login | Sim | Necessário para limitar abuso |
| Entregáveis da trilha de dados (RD01–RD11) | Sim | Pipeline, EDA, dashboard publicado, pitch e bônus preditivo |
| Importação de linhas via GTFS | Sim, versão estática | Só a lista de linhas e paradas |
| Planejamento de rotas (A\*, RAPTOR, Pareto) | Não | Fase futura; depende de GTFS completo |
| Rastreamento GPS e ETA (GTFS-RT, map matching, ML) | Não | Fase futura; depende de feed da operadora |
| Alertas de percurso (acidente, alagamento) | Não | Reaproveita o modelo de relato numa fase futura |
| Micromobilidade (GBFS) | Não | Fora do problema definido |
| WebSockets / SSE | Não | Polling ou refresh resolvem o MVP |

## 3. Glossário

Os termos abaixo viram nomes de models, campos e funções no código — a mesma palavra no papel e no Python.

| Termo | Definição | No código |
| --- | --- | --- |
| Modal | Tipo de transporte: ônibus, BRT ou metrô (extensível — ver `docs/decisoes/`) | `Modal` (choices) |
| Linha | Rota operada com número e nome, ex.: "060 – Cidade Universitária". Uma linha cobre os dois sentidos | `Linha` |
| Operadora | Empresa que opera a linha | `Linha.operadora` |
| Sentido | Direção da viagem (ida ou volta), equivalente ao `direction_id` do GTFS | `Sentido` (choices); `Relato.sentido`, `LinhaParada.sentido` |
| Destino | Bairro ou ponto para onde o veículo está indo em cada sentido — é o que a interface mostra ("060 → Cidade Universitária") | `Linha.destino_ida`, `Linha.destino_volta` |
| Parada | Ponto de embarque e desembarque | `Parada` |
| Itinerário | Sequência de paradas de uma linha em um sentido | `LinhaParada` (sentido + ordem) |
| Veículo | Unidade física identificada pelo prefixo pintado na lataria (opcional no relato) | `Relato.prefixo_veiculo` |
| Relato | Registro de um passageiro sobre as condições de uma linha em um instante | `Relato` |
| Dimensão | Aspecto avaliado: lotação, conforto térmico, ar-condicionado, vaga PCD | campos do `Relato` |
| Confirmação | Voto de outro usuário dizendo se um relato ainda vale | `Confirmacao` |
| Status agregado | Resumo calculado de todos os relatos válidos de uma linha/sentido | `StatusLinha` (calculado) |
| Janela de validade | Tempo após o qual um relato deixa de contar | `RELATO_VALIDADE_MIN` |
| Terminal Integrado (TI) | Estação de baldeação do sistema do Recife | `Parada.eh_terminal` |

## 4. Requisitos funcionais

Sete requisitos funcionais (RF) cobrem o produto e onze requisitos de dados (RD) cobrem os entregáveis da trilha de Análise e Visualização de Dados. Cada critério de aceite (Dado / Quando / Então) vira um teste automatizado antes da implementação.

### RF01 — Conta de usuário

*Como passageiro, quero criar conta e entrar, para que meus relatos sejam atribuídos a mim.*

- Dado um visitante, quando ele se cadastra com e-mail e senha válidos, então a conta é criada e ele fica logado.
- Dado um visitante não logado, quando ele tenta enviar um relato, então é redirecionado ao login e volta ao formulário depois.
- Dado um visitante, quando ele consulta o status de uma linha, então vê o resultado sem precisar de login.

### RF02 — Buscar linha

*Como passageiro, quero achar minha linha pelo número ou nome.*

- Dado o termo "060", quando busco, então vejo as linhas cujo número ou nome contém "060", com modal e o destino de cada sentido.
- Dado um termo sem correspondência, quando busco, então vejo "Nenhuma linha encontrada" e uma sugestão de termo.
- Dado que já relatei ou consultei linhas, quando abro a busca, então vejo minhas linhas recentes no topo.

### RF03 — Enviar relato

*Como passageiro dentro do veículo, quero informar as condições em até 3 toques.*

- Dado um usuário logado numa linha e sentido, quando ele escolhe lotação e envia, então o relato é salvo com data/hora do servidor e aparece no status em até 2 s.
- Dado o formulário, quando o usuário preenche só lotação, então o envio é aceito (climatização, ar e vaga PCD são opcionais).
- Dado um relato enviado há menos de `RELATO_INTERVALO_MIN` na mesma linha e sentido, quando o mesmo usuário tenta outro, então recebe aviso e o novo substitui o anterior (RN05).
- Dado um relato enviado, quando a resposta volta, então o usuário vê uma confirmação "Obrigado por colaborar".

### RF04 — Consultar status da linha

*Como passageiro no ponto, quero ver como está a linha agora.*

- Dada uma linha com relatos válidos, quando abro seu status, então vejo cada dimensão com o valor predominante, o número de relatos e há quanto tempo foi o último.
- Dada uma linha sem relatos dentro da janela de validade, quando abro seu status, então vejo "Sem informação recente" — nunca um valor antigo apresentado como atual.
- Dados relatos conflitantes, quando o status é calculado, então relatos mais recentes e mais confirmados pesam mais (RN02).

### RF05 — Confirmar ou contestar relato

*Como passageiro no mesmo veículo, quero dizer se a informação ainda vale.*

- Dado um relato válido de outro usuário, quando toco em "Ainda está assim", então a confirmação é registrada e renova o peso do relato.
- Dado um relato válido, quando toco em "Não está mais assim", então o peso do relato cai e posso enviar meu próprio relato.
- Dado um relato meu, quando tento confirmá-lo, então a ação não é oferecida.

### RF06 — Painel de dados

*Como membro da equipe ou da Prefeitura, quero ver padrões agregados.*

- Dado qualquer visitante, quando clica em "Painel" no menu do site, então é levado ao dashboard Streamlit (RD07).
- Dado o dashboard, então ele exibe só agregados — nenhum identificador de usuário nem relato individual.
- Dado o dashboard, quando filtro por modal e período, então todos os gráficos respeitam o filtro.

As visualizações estão especificadas nos RD05–RD07.

### RF07 — Moderação

*Como administrador, quero remover relatos abusivos e bloquear usuários.*

- Dado um relato com contestações ≥ `LIMIAR_CONTESTACAO`, quando o admin abre o Django Admin, então ele aparece numa fila de revisão.
- Dado um usuário bloqueado (`is_active = False`), quando tenta entrar ou enviar relato, então a ação é recusada; a consulta pública continua disponível.
- Dado um relato removido, quando o status é recalculado, então ele não conta mais.
- Dada uma remoção, então ficam registrados quando, por quem e o motivo (`removido_em`, `removido_por`, `motivo_remocao`).

### Requisitos da trilha de dados (RD01–RD11)

Cada entregável de CC vira um requisito com artefato no repositório e critério de aceite. O MVP roda sobre dados mockados (RD02); a coleta com usuários reais é decisão futura (seção 12).

| Nº | Entregável | Requisito | Artefato no repositório | Fase |
| --- | --- | --- | --- | --- |
| 1 | Plano de Análise de Dados | RD01 | `docs/dados/01-plano-analise.md` | 0 |
| 2 | Plano de Preparação de Dados | RD02, RD03 | `docs/dados/02-plano-preparacao.md` + `dados/pipeline/` | 1 |
| 3 | Análise Exploratória (EDA) | RD04 | `dados/notebooks/03-eda.ipynb` | 1 |
| 4 | Dashboard — versão inicial | RD05 | `dados/dashboard/` (v0.1) | 2 |
| 5 | Proposta de Integração e Publicação | RD06 | `docs/dados/05-proposta-publicacao.md` | 2 |
| 6 | Dashboard Consolidado | RD07 | `dados/dashboard/` (v1.0) + `docs/dados/06-decisoes-visuais.md` | 2 |
| 7 | Versão Quase Final (validação) | RD08 | `docs/dados/07-validacao.md` | 3 |
| 8 | Storytelling e Pitch | RD09 | `docs/dados/08-storytelling/` | 3 |
| 9 | Documentação Final | RD10 | `docs/dados/09-documentacao-final.md` + `docs/decisoes/` | 3 |
| Bônus | Modelagem Preditiva | RD11 | `dados/notebooks/10-modelagem.ipynb` | 3 |

### RD01 — Plano de Análise de Dados

*Define a pergunta, as hipóteses e as fontes candidatas antes de tocar nos dados.*

**Contexto.** Segundo o Grande Recife, dos 2.462 ônibus em circulação no início de 2026, só 401 tinham ar-condicionado ([Diário de Pernambuco](https://www.diariodepernambuco.com.br/amp/vida-urbana/2026/01/11705131-aumento-da-passagem-passageiros-devem-pagar-mais-caro-para-usar-onibus-velhos-e-sem-ar-condicionado.html)). O desconforto é estrutural; a análise mostra onde e quando ele pesa mais.

| Pergunta | Hipótese inicial | Visualização provável |
| --- | --- | --- |
| Q1. Em que linhas e horários a lotação é pior? | H1. Lotação concentra-se nos picos da manhã e da tarde, nas linhas que chegam aos TIs | Mapa de calor linha × hora |
| Q2. Com que frequência o ar falha em veículos climatizados? | H2. A taxa de "não funcionando" varia entre linhas e operadoras (`Linha.operadora`) | Barras ranqueadas |
| Q3. O desconforto térmico acompanha a temperatura externa? | H3. Relatos "quente" crescem com a temperatura, mais forte em veículos sem ar | Dispersão com tendência |
| Q4. Quando a vaga PCD está ocupada? | H4. Ocupação da vaga PCD acompanha a lotação | Barras empilhadas por faixa horária |

- Dado o documento, então ele traz o problema, ao menos 3 hipóteses testáveis, as fontes candidatas (RD02) e as visualizações marcadas como provisórias até a EDA.
- Dada cada hipótese, então ela aponta qual variável e qual fonte a testam.

### RD02 — Fontes de dados e plano de preparação

*Seleciona e valida as fontes, avalia o mecanismo de falta de dados e justifica cada tratamento.*

| Fonte | Conteúdo | Formato | Situação |
| --- | --- | --- | --- |
| Dados mockados | mesmo esquema dos relatos | Script em `dados/mock/` | **Fonte do MVP** — ver regras abaixo |
| Dados abertos de PE / Grande Recife (versão antiga) | linhas, operadoras e paradas | CSV | Em uso no MVP; atualizar é decisão futura |
| INMET, estação Recife | temperatura horária | CSV | Validar — dado real para cruzar com o mock |
| Frota climatizada por linha | se a linha opera com ar | A pedir à Prefeitura | Decisão futura (seção 12) |
| Relatos de usuários reais | lotação, clima, ar, vaga PCD por linha e hora | PostgreSQL | Após o lançamento; coleta piloto é decisão futura |

**Regras para os dados mockados.** O gerador é calibrado com fatos reais — horários de pico, cerca de 16% da frota com ar (401 de 2.462 ônibus, RD01) e temperatura real do INMET — e seus parâmetros ficam versionados em `dados/mock/config.yaml`. Toda análise sobre mock declara isso no título. Achados sobre mock validam o pipeline e as visualizações, não o comportamento dos passageiros: o gerador só devolve os padrões programados nele.

**Mecanismo de falta.** Antes de limpar, classificar cada variável com ausência:

- Campos opcionais do relato (ar, conforto, vaga PCD): provável MNAR — quem relata o ar tende a fazê-lo quando ele está quebrado. Não imputar; tratar "não informado" como categoria e registrar o viés.
- Temperatura do INMET com falha de estação: provável MCAR. Interpolação temporal só em lacunas curtas (até 2 h); acima disso, deixar ausente.
- `prefixo_veiculo` vazio: esperado (campo opcional); análises por veículo usam só o subconjunto preenchido.

**Critérios de aceite.**

- Dado o documento, então cada fonte aparece com formato, período coberto e status de validação.
- Dada cada decisão de limpeza, então ela cita a característica da variável que a justifica (tipo, domínio da RN01, mecanismo de falta).
- Dado o gerador de mock, então cada parâmetro está documentado com a fonte real que o calibrou.

### RD03 — Pipeline de dados (bronze → prata → ouro)

*Separa dado bruto de dado tratado, em arquitetura medallion.*

| Camada | Conteúdo | Regras |
| --- | --- | --- |
| Bronze | Cópia imutável dos relatos e dos arquivos externos, com data de extração | Nunca editada; só acrescentada |
| Prata | Dados limpos: tipos, fuso America/Recife, domínios da RN01, relatos removidos fora (`removido_em` preenchido), substituições da RN05 resolvidas (`substituido_por`), join com `Linha` | Reconstruível a partir da bronze |
| Ouro | Agregados para análise: relatos por linha × hora, taxas por dimensão, join com temperatura | Fonte única do dashboard e dos notebooks |

- Dado o comando `python manage.py pipeline`, quando executado do zero, então prata e ouro são reconstruídas a partir da bronze.
- Dada cada execução, então testes de qualidade conferem contagens entre camadas, nulos e domínios — e falham o CI se quebrarem.
- Dado o dashboard ou um notebook, então eles leem só da camada ouro (schema `ouro` no PostgreSQL).

### RD04 — Análise Exploratória (EDA)

*Notebook que encontra padrões e decide se a preparação precisa de ajuste.*

1. **Estrutural:** tipos, domínios da RN01, granularidade (um relato por linha, sentido e instante), chaves, contagens entre camadas e nulos, ligados ao mecanismo de falta do RD02.
2. **Distribucional:** distribuição de cada dimensão e volume de relatos por linha, faixa horária e dia da semana.
3. **Relacional:** lotação × faixa horária, conforto térmico × temperatura, ar × linha; V de Cramér entre categóricas e Spearman com temperatura; agrupamento de linhas pelo perfil de lotação ao longo do dia (k-means ou hierárquico).
4. **Outliers e anomalias:** univariados — volume por linha/hora fora de 1,5 × IIQ; bivariados — combinações improváveis ("vazio" em pico numa linha sempre lotada); usuários com volume ou padrão anômalo, candidatos à moderação (RF07).
5. **Conclusão:** o que muda na preparação (volta ao RD02/RD03) e quais achados seguem para o dashboard.

- Dado o notebook, então ele tem uma seção para cada um dos quatro princípios (estrutural, distribucional, relacional, outliers e anomalias) e cada gráfico tem logo abaixo um texto de interpretação.
- Dado cada outlier encontrado, então o notebook decide e justifica: manter, tratar ou excluir.
- Dado o notebook executado do zero, então ele roda só a partir da camada ouro, sem erro.

### RD05 — Dashboard interativo, versão inicial

*Primeira versão funcional, já na ferramenta definida no RD06.*

- Dado o dashboard, então ele tem ao menos 3 visualizações integradas e filtros por modal, linha, período e faixa horária que afetam todas elas.
- Dada cada página, então o título é a pergunta e o gráfico principal a responde (narrativa visual).
- Dada a revisão de design, então um checklist de clareza, contraste, hierarquia visual e usabilidade está preenchido.

### RD06 — Proposta de Integração e Publicação

*Planeja a versão final: estrutura, páginas e ferramenta.*

**Ferramenta: Streamlit acoplado ao Django.** O Streamlit roda como serviço no mesmo Docker Compose, lê só o schema ouro, e o item "Painel" do menu do site leva a ele. Motivos: filtros e gráficos interativos saem com bem menos código do que em templates Django, a linguagem é a mesma e a disciplina lista o Streamlit. Como o dashboard mostra só agregados, sem dado de usuário, ele pode ser público e não precisa compartilhar o login do Django. Plano B, se a integração atrapalhar: os mesmos gráficos em Plotly dentro de templates Django.

| Página | Pergunta que responde | Visualização principal |
| --- | --- | --- |
| Visão geral | Como está o sistema hoje? | Indicadores: relatos, cobertura, linhas ativas |
| Lotação | Onde e quando lota? | Mapa de calor linha × hora |
| Climatização | Onde o ar falha e quando o calor pesa? | Ranking de falhas + dispersão com temperatura |
| Acessibilidade | Quando a vaga PCD está ocupada? | Barras por faixa horária |
| Qualidade dos dados | Dá para confiar nos números? | Cobertura, confirmações e contestações |

- Dado o documento, então ele traz a estrutura de páginas, um wireframe feito com a equipe de Design e a ferramenta escolhida com justificativa.

### RD07 — Dashboard consolidado

*Versão integrada e publicada, funcionando de ponta a ponta.*

- Dado o link público, quando aberto, então os dados da camada ouro (mock no MVP) carregam e todos os filtros funcionam.
- Dado o pipeline (RD03) executado, então o dashboard reflete os novos dados sem mudança de código.
- Dado o documento de decisões visuais, então cada gráfico tem: pergunta, tipo escolhido, motivo, uso de cor — e os insights obtidos até aqui.

### RD08 — Versão quase final (validação funcional)

*Prova que o dashboard foi testado com gente real e ajustado.*

- Dado um roteiro de tarefas (ex.: "qual linha está mais lotada às 18h?"), quando aplicado a pessoas do público-alvo (quantidade a definir; sugestão: 5), então registram-se sucesso, tempo e comentários de cada tarefa.
- Dados os resultados, então cada ajuste feito aponta para o achado do teste que o motivou.
- Dado o documento, então ele tem duas listas explícitas: o que foi validado e o que ainda será refinado antes do pitch.

### RD09 — Storytelling e preparação do pitch

*Transforma os achados em narrativa para a apresentação final.*

**Linha narrativa proposta:** contexto (frota majoritariamente sem ar e espera às cegas) → o que os passageiros relataram → os 2–3 achados mais fortes → recomendação concreta para a Prefeitura.

- Dada a curadoria, então entram de 3 a 5 gráficos, escolhidos pelo achado que sustentam.
- Dada cada peça narrativa, então ela usa um elemento pré-atentivo para o achado (uma única cor de destaque, o resto em cinza) e princípios da Gestalt (proximidade e similaridade) para agrupar.
- Dado o roteiro do pitch, então cada slide tem um título que afirma o achado, não o tema.

### RD10 — Documentação final

*Registra o processo inteiro e os resultados.*

- Dado o repositório, então `docs/decisoes/` tem um registro de decisão (ADR) por escolha relevante, criado no momento da decisão, desde a fase 0.
- Dado o documento final, então ele traz capturas ou links de todas as visualizações, a síntese dos principais insights com os números que os sustentam e o histórico de decisões.
- Dadas as hipóteses do RD01, então cada uma aparece como confirmada, refutada ou inconclusiva, com a evidência.

### RD11 — Bônus: modelagem preditiva

*Exploração inicial; não substitui nenhum entregável obrigatório.*

**Caminho recomendado: classificação.** Prever se um relato será "lotado" a partir de linha, faixa horária, dia da semana e temperatura. Alternativa de regressão: proporção de relatos "quente" em função da temperatura.

- Dado o notebook, então há um baseline (classe mais frequente) e um classificador simples (regressão logística ou árvore de decisão), com divisão treino/teste temporal.
- Dado o modelo, então o notebook mostra matriz de confusão, acurácia, precisão, recall, F1 e as curvas ROC e precision-recall.
- Dados os resultados, então um texto interpreta o desempenho e o que ele permite na prática (ex.: prever lotação quando não há relato recente).

## 5. Regras de negócio

As regras ficam num único módulo (`src/relatos/regras.py`) e os números em `settings` — são parâmetros iniciais, a calibrar com dados reais.

**RN01 — Valores de cada dimensão.**

| Dimensão | Valores | Obrigatória? |
| --- | --- | --- |
| Lotação | vazio · moderado · lotado | Sim |
| Conforto térmico | frio · agradável · quente | Não |
| Ar-condicionado | funcionando · não funcionando · sem ar | Não |
| Vaga PCD | disponível · ocupada | Não |

**RN02 — Peso por idade (decaimento exponencial).** Cada relato tem peso que cai com o tempo; confirmações somam e contestações subtraem:

```latex
w = e^{-\lambda t} \cdot (1 + 0{,}5\,c - 0{,}5\,x)
```

onde t = minutos desde o relato (ou desde a última confirmação), c = confirmações, x = contestações. λ inicial = ln 2 / 15 (meia-vida de 15 min). Peso ≤ 0 não conta.

**RN03 — Status agregado.** Para cada dimensão, o valor exibido é o de maior soma de pesos entre os relatos válidos. Se a soma total for menor que `PESO_MINIMO`, a dimensão mostra "Sem informação recente".

**RN04 — Janela de validade.** Relatos com mais de `RELATO_VALIDADE_MIN` = 45 min não entram no cálculo, mesmo com peso residual.

**RN05 — Limite por usuário.** Um relato ativo por usuário por linha e sentido; um novo dentro de `RELATO_INTERVALO_MIN` = 10 min substitui o anterior. A substituição grava um relato novo e marca o anterior com `substituido_por`: o anterior sai do status agregado, continua no histórico (RN07) e suas confirmações não passam para o novo.

**RN06 — Confirmação única.** Cada usuário confirma ou contesta um mesmo relato uma vez, e nunca o próprio.

**RN07 — Histórico preservado.** Relatos expirados ou substituídos não são apagados: alimentam o painel (RF06). Só a moderação remove, e por soft delete: `removido_em`, `removido_por` e `motivo_remocao`.

## 6. Requisitos não funcionais

| ID | Requisito | Como verificar |
| --- | --- | --- |
| RNF01 | Mobile-first: usável com uma mão em tela de 360 px | Revisão de design + teste manual em celular |
| RNF02 | Envio de relato responde em < 1 s (p95) com rede 4G | Teste de carga com Locust |
| RNF03 | Com conexão instável, o envio falha com mensagem clara e o formulário mantém o que foi preenchido | Teste com rede lenta e offline no DevTools |
| RNF04 | Acessibilidade WCAG 2.1 AA — o público inclui PCDs | Lighthouse + leitor de tela |
| RNF05 | LGPD: nenhuma localização contínua é guardada; relato guarda só linha, sentido e hora | Revisão do modelo de dados |
| RNF08 | Novos modais entram sem mudar o modelo de dados: um valor em `Modal` e um mapeamento GTFS | Procedimento descrito em `docs/decisoes/` |
| RNF06 | Cobertura de testes ≥ 80% em `src/relatos/regras.py` | `coverage` no CI |
| RNF07 | Deploy reproduzível com Docker Compose | `docker compose up` sobe tudo do zero |

## 7. Modelo de dados

Seis models bastam para o MVP; o status agregado é calculado, não armazenado (com cache curto na fase 2).

| Model | App | Campos principais | Regras ligadas |
| --- | --- | --- | --- |
| `Usuario` | contas | herda `AbstractUser`; login por `email` (único), sem `username` | RF01, RF07 |
| `Linha` | transporte | `codigo` (único), `nome`, `modal`, `operadora`, `destino_ida`, `destino_volta` (vazio se circular), `ativa`, `gtfs_route_id` | RF02 |
| `Parada` | transporte | `nome`, `lat`, `lon`, `eh_terminal`, `gtfs_stop_id`; `linhas` (muitos-para-muitos via `LinhaParada`) | RF02, fase 2 |
| `LinhaParada` | transporte | FK `linha`, FK `parada`, `sentido`, `ordem`; único por (linha, sentido, ordem) e por (linha, parada, sentido) | Itinerário |
| `Relato` | relatos | FK `usuario`, FK `linha`, `sentido`, `lotacao`, `conforto_termico`, `ar_condicionado`, `vaga_pcd`, `prefixo_veiculo` (opcional), `criado_em`, `substituido_por` (FK para `Relato`), `removido_em`, `removido_por`, `motivo_remocao` | RF03, RN01–RN05, RN07 |
| `Confirmacao` | relatos | FK `relato`, FK `usuario`, `ainda_vale` (bool), `criado_em`; único por (relato, usuario) | RF05, RN06 |

**Papéis de usuário.** Usam os recursos do próprio Django, sem campos extras:

| Papel | Como é representado |
| --- | --- |
| Passageiro | Qualquer usuário ativo |
| Analista | Membro do grupo `analistas` |
| Administrador | `is_staff` (acessa o Admin) / `is_superuser` |
| Bloqueado | `is_active = False` — não entra nem relata; a consulta é pública |

Índices: `Relato(linha, sentido, criado_em)` para o cálculo do status e `Relato(criado_em)` para o painel. Use `models.TextChoices` para os valores da RN01, para `Modal` e para `Sentido` — o enum no código é o mesmo da spec. `lat`/`lon` são `DecimalField(9, 6)` até a entrada do PostGIS.

## 8. Arquitetura Django

Um monólito Django com três apps de domínio, cada uma com sua parte da API REST; a interface é server-rendered com HTMX, o que evita um front separado no MVP.

```
 navegador ── HTMX ──┐                 ┌── Streamlit (dados/dashboard/) ── lê só o schema ouro
                     ▼                 │
           Django (src/config/)        │
     contas · transporte · relatos     │
       (views + api.py com DRF)        │
                     │                 │
                     ▼                 │
              PostgreSQL 16 ◄──────────┘
       schema public (app) · bronze/prata/ouro (dados/pipeline)
```

Views e API são portas finas: toda decisão sobre relatos passa por `src/relatos/regras.py`, que é onde os testes de aceite se concentram.

**Stack.** Python 3.12 · Django 5.2 LTS · Django REST Framework · PostgreSQL 16 · HTMX + Tailwind · pytest-django · ruff · uv · Docker Compose · GitHub Actions. Configuração por variáveis de ambiente (`django-environ`, `.env.example` no repositório). Trilha de dados: pandas, Jupyter, scikit-learn e Streamlit. Redis e PostGIS entram só na fase 2. O dashboard Streamlit roda como serviço à parte e lê só o schema ouro do mesmo PostgreSQL.

**Estrutura de pastas.**

A raiz tem só quatro pastas de conteúdo — uma por frente de trabalho — e os arquivos de configuração que as ferramentas exigem na raiz.

```
MobiColab/
├── src/                  # aplicação Django (frente backend)
│   ├── config/           # settings, urls, wsgi
│   ├── contas/           # Usuario, login, papéis
│   ├── transporte/       # Linha, Parada, LinhaParada, modais, importar_gtfs, fixtures
│   ├── relatos/          # Relato, Confirmacao, regras.py, status
│   └── templates/        # base.html e telas (inclui o link "Painel" do RF06)
├── dados/                # trilha de dados (frente de CC) — a partir da fase 1
│   ├── mock/             # gerador de dados mockados + config.yaml (RD02)
│   ├── pipeline/         # bronze → prata → ouro + testes de qualidade (RD03)
│   ├── notebooks/        # 03-eda.ipynb, 10-modelagem.ipynb (RD04, RD11)
│   └── dashboard/        # app Streamlit (RD05, RD07)
├── docs/
│   ├── spec.md           # esta spec
│   ├── dados/            # planos, proposta, validação, storytelling (RD01–RD10)
│   └── decisoes/         # registros de decisão (ADR)
├── tests/                # um arquivo por RF
├── docker/               # Dockerfile e entrypoint
├── manage.py
├── compose.yaml · pyproject.toml · uv.lock
└── README.md · LICENSE · .env.example
```

Cada app guarda a sua parte da API em `api.py` (serializers e viewsets DRF); as rotas são reunidas em `src/config/urls.py`. O "Painel" é só um item de menu que leva ao Streamlit — não precisa de app própria.

**Endpoints.**

| Método | Rota | Auth | Requisito |
| --- | --- | --- | --- |
| GET | `/api/linhas/?q=` | Pública | RF02 |
| GET | `/api/linhas/{id}/status/?sentido=ida` | Pública | RF04 |
| POST | `/api/relatos/` | Logado | RF03 |
| POST | `/api/relatos/{id}/confirmacoes/` | Logado | RF05 |
| GET | `/painel/` → dashboard Streamlit | Pública | RF06 |
| — | `/admin/` | Admin | RF07 |

## 9. Trilha de dados e métricas de sucesso

Os entregáveis da trilha estão nos RD01–RD11 (seção 4); o dashboard transforma relatos individuais em padrões que a Prefeitura pode usar. Design de Interface cuida do fluxo de relato e consulta.

**Visualizações do painel.**

1. Mapa de calor: linha × faixa horária, cor = lotação predominante.
2. Ranking de linhas com mais relatos de ar-condicionado não funcionando.
3. Volume de relatos por dia e por modal (série temporal).
4. Cobertura: % das consultas que encontraram status com relato válido.

**Métricas de sucesso do MVP.** As metas são decisão futura — ver seção 12.

| Métrica | O que mede | Fonte |
| --- | --- | --- |
| Relatos por dia | Engajamento | `Relato.criado_em` |
| Cobertura de consultas | Utilidade: o usuário achou informação? | Log de `/status/` |
| Taxa de confirmação | Confiabilidade percebida | `Confirmacao` |
| Taxa de contestação | Ruído / trollagem | `Confirmacao.ainda_vale = false` |
| Usuários que relatam em 2+ semanas | Retenção | `Relato.usuario` |

## 10. Riscos e mitigação

| Risco | Impacto | Mitigação na spec |
| --- | --- | --- |
| Poucos relatos nos primeiros meses (mapa vazio) | Usuário novo não acha informação e desiste | Piloto concentrado em poucas linhas que passam pela CESAR; RF04 mostra "Sem informação recente" com convite a relatar |
| Dados falsos ou trollagem | Plataforma perde confiança | Login obrigatório para relatar (RF01), limite por usuário (RN05), contestação (RF05), fila de moderação (RF07) |
| Dados desatualizados | Usuário embarca num ônibus que já mudou | Decaimento exponencial (RN02) e janela de validade (RN04) |
| GPS e sinal fracos (metrô subterrâneo) | Relato não chega | MVP não depende de GPS: usuário escolhe a linha; mensagem clara se o envio falhar (RNF03) |
| Dados GTFS do Recife indisponíveis ou desatualizados | Lista de linhas incompleta | Cadastro manual de linhas pelo Admin como fallback |

**Risco da trilha de dados.** Com o MVP sobre dados mockados, a EDA e o dashboard podem mostrar só os padrões que o gerador recebeu. Mitigação: calibrar o mock com dados reais (frota, temperatura, horários de pico), rotular toda análise sobre mock e tratar a coleta real como próximo passo.

## 11. Roadmap

O ciclo spec-driven é sempre o mesmo: **spec → plano técnico → tarefas → testes → código**. Nenhuma tarefa começa sem apontar para um RF, RN, RNF ou RD desta spec; se o código precisar de algo que a spec não diz, a spec muda primeiro.

**Fluxo de trabalho.** As tarefas vivem como issues no GitHub, num quadro kanban (Backlog → Fazendo → Revisão → Feito). Cada issue cita o requisito no título (ex.: "[RF03] validar lotação obrigatória") e cabe em 1–2 dias. A `main` é protegida: todo merge passa por PR com o CI verde e uma revisão.

**Fases.**

A disciplina define só a entrega final, em 11/12/2026; os prazos intermediários são do grupo.

| Fase | Período | Escopo | Entregas de dados | Pronto quando |
| --- | --- | --- | --- | --- |
| 0 — Fundação | 14/10 a 21/10 | Repositório, Docker Compose, CI com pytest, models e migrations da seção 7, Django Admin, fixture de desenvolvimento, `docs/decisoes/` | RD01 | `docker compose up` sobe e o CI passa |
| 1 — Núcleo e dados mockados | 22/10 a 10/11 | RF01 a RF05 com testes de aceite; importação das linhas; gerador de mock calibrado; pipeline | RD02, RD03, RD04 | Testes de aceite dos RF01–RF05 passam; `manage.py pipeline` reconstrói prata e ouro |
| 2 — Painel e confiança | 11/11 a 24/11 | RF06, RF07, dashboard Streamlit acoplado, cache do status em Redis, publicação | RD05, RD06, RD07 | Dashboard publicado com link no menu |
| 3 — Validação e entrega | 25/11 a 08/12 | Testes de uso, storytelling, documentação | RD08, RD09, RD10, RD11 | Pitch e documentação final prontos |
| Folga e entrega final | 09/12 a 11/12 | — | — | Entregue |

**Depois da disciplina — Expansão (benchmark):** coleta real, GTFS atualizado, novos modais (ex.: VLT), alertas de percurso, PostGIS, GPS/ETA e rotas.

## 12. Pendências

Tudo o que espera calibração, dados externos ou decisão futura, num lugar só. As decisões já tomadas, com seus motivos e alternativas, estão em [`docs/decisoes/`](decisoes/README.md). Entrega final do projeto: 11/12/2026.

### Parâmetros a calibrar

Valores iniciais, escolhidos sem dados. Revisar todos quando houver relatos reais; até lá, nenhum é verdade.

| Parâmetro | Valor inicial | Onde | Como calibrar |
| --- | --- | --- | --- |
| Meia-vida do relato | 15 min | RN02 | Em quanto tempo relatos consecutivos da mesma linha mudam de valor |
| `RELATO_VALIDADE_MIN` | 45 min | RN04 | Mesma análise + taxa de "Sem informação recente" |
| Peso de confirmação e contestação | 0,5 cada | RN02 | Comparar status calculado com relatos posteriores |
| `RELATO_INTERVALO_MIN` | 10 min | RN05 | Frequência de reenvio pelo mesmo usuário |
| `PESO_MINIMO` | a definir | RN03 | Equilíbrio entre cobertura e erro percebido no teste de uso |
| `LIMIAR_CONTESTACAO` | a definir | RF07 | Taxa de contestação observada |
| Parâmetros do gerador de mock | `config.yaml` | RD02 | Fontes reais citadas em cada parâmetro |

### Pedidos à Prefeitura

| Pedido | Para quê | Status |
| --- | --- | --- |
| Lista de linhas com frota climatizada | Testar H2 e H3; calibrar o mock | Não solicitado |
| GTFS atualizado do Grande Recife | Substituir os dados antigos | Não solicitado |
| Demanda de passageiros por linha | Escolher as linhas do piloto | Não solicitado |
| Operadora de cada linha | Testar H2 | Não solicitado (tentar antes nos dados abertos) |

### Decisões futuras

- [ ] Coleta com usuários reais: quando, quantas pessoas e termo de consentimento (LGPD)
- [ ] Metas numéricas das métricas da seção 9
- [ ] Trocar os dados antigos pelo GTFS atualizado, quando chegar
- [ ] Incorporar a lista de frota climatizada, quando chegar
- [ ] Revisar os parâmetros a calibrar com dados reais
- [ ] Onde publicar o site e o dashboard (fase 2)

### Próximas ações

- [ ] Escolher as linhas do MVP: levantar juntos, nos dados disponíveis, as linhas mais usadas (a fixture da fase 0 é só para desenvolvimento)
