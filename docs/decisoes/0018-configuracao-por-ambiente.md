# 0018 — Configuração por variáveis de ambiente

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RNF07

## Contexto

O mesmo código roda na máquina de cada pessoa, no CI e, na fase 2, num servidor público. Segredos não podem ir para um repositório público.

## Decisão

Um único `config/settings.py` lê variáveis de ambiente com `django-environ`. O repositório tem um `.env.example` com todas as variáveis; o `.env` fica no `.gitignore`. Padrões: `LANGUAGE_CODE = "pt-br"`, `TIME_ZONE = "America/Recife"`, `USE_TZ = True`. Os parâmetros das regras de negócio (`RELATO_VALIDADE_MIN` etc.) ficam nos settings com os valores iniciais da spec.

## Alternativas consideradas

- Settings divididos em `base/dev/prod` — descartada: mais arquivos para o mesmo efeito.

## Consequências

- Calibrar um parâmetro é mudar uma variável de ambiente, sem mexer no código.
