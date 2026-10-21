# 0003 — Relato por linha e sentido, com prefixo do veículo opcional

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF03, RF04, RN05

## Contexto

O passageiro sabe em que linha está e para onde vai, mas raramente presta atenção no prefixo pintado na lataria. Exigir o veículo tornaria o relato lento e com muitos erros.

## Decisão

O relato é feito para uma **linha e um sentido**. O prefixo do veículo (`prefixo_veiculo`) é opcional. O status é calculado por linha e sentido.

## Alternativas consideradas

- Relato por veículo — descartada: depende de informação que o passageiro não tem; fica para quando houver GPS da frota.
- Relato só por linha, sem sentido — descartada: ida e volta têm lotações muito diferentes no mesmo horário.

## Consequências

- Análises por veículo usam só o subconjunto com prefixo preenchido (RD02).
- O modelo detalhado de linha e sentido está no ADR 0012.
