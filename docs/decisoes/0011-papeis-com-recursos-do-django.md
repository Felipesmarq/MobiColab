# 0011 — Papéis de usuário com os recursos do próprio Django

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF01, RF06, RF07

## Contexto

A primeira versão da spec previa os campos `perfil` (passageiro · analista · admin) e `bloqueado`. O Django já tem `is_staff`, `is_superuser`, `is_active` e grupos — ter as duas coisas cria duas fontes de verdade.

## Decisão

Nenhum campo extra. Os papéis são representados assim:

| Papel | Representação |
| --- | --- |
| Passageiro | Qualquer usuário ativo |
| Analista | Membro do grupo `analistas` (criado por migration) |
| Administrador | `is_staff` / `is_superuser` |
| Bloqueado | `is_active = False` |

## Alternativas consideradas

- Campos `perfil` e `bloqueado` próprios — descartada: duplicam o que o Django oferece e exigem manter os dois em sincronia.
- `bloqueado` separado de `is_active` (bloqueado ainda entra, só não relata) — descartada: a consulta é pública, então o usuário bloqueado não perde nada por não conseguir entrar.

## Consequências

- Bloquear um usuário encerra também as sessões abertas dele (o Django rejeita usuários inativos).
- A tela de bloqueio é o próprio Admin (desmarcar "Ativo").
