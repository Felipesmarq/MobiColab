# 0008 — Dashboard em Streamlit acoplado ao Django

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF06, RD05, RD06, RD07

## Contexto

O dashboard precisa de filtros e gráficos interativos. Construir isso em templates Django exige muito código de front-end, e a disciplina lista o Streamlit como ferramenta.

## Decisão

O dashboard é um app Streamlit (`dados/dashboard/`) que roda como serviço no mesmo Docker Compose, lê só o schema ouro do PostgreSQL e é acessado pelo item "Painel" do menu do site. Como mostra só agregados, é público e não compartilha o login do Django.

## Alternativas consideradas

- Gráficos Plotly em templates Django — mantida como **plano B**, caso a integração atrapalhe.
- Power BI ou Metabase — descartadas: outra linguagem e outro deploy.

## Consequências

- O serviço Streamlit entra no Compose na fase 2.
- Nenhum dado individual de usuário chega ao dashboard.
