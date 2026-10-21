# Registros de decisão (ADR)

Cada arquivo registra uma decisão: contexto, decisão, alternativas e consequências. A spec ([../spec.md](../spec.md)) diz *o quê*; estes registros dizem *por quê*. Para mudar uma decisão, crie um novo ADR que substitua o anterior.

| Nº | Decisão | Status |
| --- | --- | --- |
| 0001 | [Registrar decisões em ADRs](0001-usar-adrs.md) | aceita |
| 0002 | [Lotação em três níveis](0002-lotacao-tres-niveis.md) | aceita |
| 0003 | [Relato por linha e sentido, com prefixo do veículo opcional](0003-relato-por-linha-e-sentido.md) | aceita |
| 0004 | [Somente versão web responsiva no MVP](0004-somente-web-responsiva.md) | aceita |
| 0005 | [Linhas e paradas a partir dos dados abertos antigos de PE](0005-linhas-de-dados-abertos-antigos.md) | aceita |
| 0006 | [MVP sobre dados mockados calibrados com dados reais](0006-mvp-sobre-dados-mockados.md) | aceita |
| 0007 | [EDA organizada em quatro princípios](0007-eda-quatro-principios.md) | aceita |
| 0008 | [Dashboard em Streamlit acoplado ao Django](0008-dashboard-streamlit-acoplado.md) | aceita |
| 0009 | [Cronograma de fases definido pelo grupo](0009-cronograma-do-grupo.md) | aceita |
| 0010 | [Login por e-mail, sem username](0010-login-por-email.md) | aceita |
| 0011 | [Papéis de usuário com os recursos do próprio Django](0011-papeis-com-recursos-do-django.md) | aceita |
| 0012 | [Linha única por código, com sentido no relato e itinerário por parada](0012-linha-unica-com-itinerarios.md) | aceita |
| 0013 | [Substituição de relato gera um relato novo](0013-substituicao-de-relato.md) | aceita |
| 0014 | [Remoção de relato por soft delete auditável](0014-soft-delete-auditavel.md) | aceita |
| 0015 | [Operadora como atributo da linha](0015-operadora-na-linha.md) | aceita |
| 0016 | [Modais como TextChoices, fáceis de estender](0016-modais-extensiveis.md) | aceita |
| 0017 | [Stack e ferramentas de desenvolvimento](0017-stack-e-ferramentas.md) | aceita |
| 0018 | [Configuração por variáveis de ambiente](0018-configuracao-por-ambiente.md) | aceita |
| 0019 | [Docker Compose de desenvolvimento](0019-compose-de-desenvolvimento.md) | aceita |
| 0020 | [Integração contínua no GitHub Actions](0020-integracao-continua.md) | aceita |
| 0021 | [Fluxo de trabalho com GitHub Issues e Projects](0021-fluxo-de-trabalho.md) | aceita |
| 0022 | [Repositório público com licença MIT](0022-repositorio-publico-mit.md) | aceita |
| 0023 | [Fixture de linhas reais para desenvolvimento](0023-fixture-de-desenvolvimento.md) | aceita |
| 0024 | [Organização do repositório por frente de trabalho](0024-organizacao-do-repositorio.md) | aceita |

## Modelo

```markdown
# NNNN — Título curto

- **Data:** dd/mm/aaaa
- **Fase:** N
- **Status:** proposta | aceita | substituída por NNNN
- **Requisitos ligados:** RFxx, RNxx, RDxx

## Contexto
## Decisão
## Alternativas consideradas
## Consequências
```
