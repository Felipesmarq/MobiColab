# 0013 — Substituição de relato gera um relato novo

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RN05, RN07, RD03

## Contexto

A RN05 diz que um relato novo do mesmo usuário, na mesma linha e sentido, dentro de 10 min, substitui o anterior. A camada bronze do pipeline é imutável e a prata "resolve as substituições" — logo, o relato anterior precisa continuar existindo.

## Decisão

A substituição grava um **relato novo** e marca o anterior com `substituido_por` (FK nullable para `Relato`). O anterior sai do status agregado, mas continua no histórico. As confirmações do anterior **não** passam para o novo.

## Alternativas consideradas

- Atualizar o relato anterior no lugar — descartada: perde o histórico e quebra a imutabilidade da bronze.
- Apagar o anterior — descartada: viola a RN07.

## Consequências

- O cálculo do status ignora relatos com `substituido_por` preenchido.
- A EDA pode medir a frequência de reenvio (calibração do `RELATO_INTERVALO_MIN`).
