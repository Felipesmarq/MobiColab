# 0010 — Login por e-mail, sem username

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** RF01

## Contexto

O RF01 pede cadastro e login com e-mail e senha. O `AbstractUser` do Django faz login por `username`. Trocar o model de usuário depois da primeira migration é muito trabalhoso.

## Decisão

`contas.Usuario` herda de `AbstractUser`, remove o campo `username` e usa `USERNAME_FIELD = "email"`, com e-mail único. Um manager próprio (`UsuarioManager`) cria usuários e superusuários a partir do e-mail. O model existe desde a migration `0001` e `AUTH_USER_MODEL = "contas.Usuario"`.

## Alternativas consideradas

- Manter `username` e exigir e-mail — descartada: dois identificadores para o mesmo usuário e um campo a mais no cadastro.

## Consequências

- `createsuperuser` pede e-mail em vez de username.
- O Admin usa um `UserAdmin` adaptado ao e-mail.
