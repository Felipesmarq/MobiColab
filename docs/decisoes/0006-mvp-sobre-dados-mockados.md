# 0006 — MVP sobre dados mockados calibrados com dados reais

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RD02, RD03, RD04

## Contexto

Os entregáveis de dados (EDA, dashboard, pitch) acontecem antes que o app tenha usuários reais. A coleta com pessoas exige termo de consentimento (LGPD) e tempo.

## Decisão

O MVP roda sobre dados mockados com o mesmo esquema dos relatos, gerados por script em `dados/mock/`. O gerador é calibrado com fatos reais (horários de pico, cerca de 16% da frota com ar, temperatura do INMET) e seus parâmetros ficam em `dados/mock/config.yaml`, cada um com a fonte que o justifica.

## Alternativas consideradas

- Coletar relatos reais antes da EDA — descartada: não cabe no prazo; fica como decisão futura.
- Usar só dados externos (sem relatos) — descartada: não exercita o pipeline nem o produto.

## Consequências

- Toda análise sobre mock declara isso no título.
- Achados sobre mock validam o pipeline e as visualizações, não o comportamento dos passageiros.
