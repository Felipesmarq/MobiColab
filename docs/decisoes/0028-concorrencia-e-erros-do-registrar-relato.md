# 0028 — Concorrência e erros do `registrar_relato`

- **Data:** 11/11/2026
- **Fase:** 1
- **Status:** aceita
- **Requisitos ligados:** RF03, RN05, RF07, ADR 0011, ADR 0013

## Contexto

A RN05 quer um relato ativo por usuário, linha e sentido dentro de `RELATO_INTERVALO_MIN`. Duas abas ou um clique duplo mandam dois envios quase juntos, e a moderação (RF07) pode bloquear a conta enquanto a sessão ainda guarda `is_active = True`. A API (#14) e o formulário (#15) precisam saber *por que* um envio foi recusado para responder 401, 403 ou 400.

## Decisão

- **Tudo numa transação que trava o usuário.** `registrar_relato` roda em `transaction.atomic()` e faz `select_for_update()` na linha do usuário, relendo `is_active` do banco. Os envios do mesmo usuário passam a ser serializados: o segundo vê o relato do primeiro e o substitui, em vez de deixar dois ativos na janela. O bloqueio feito pela moderação depois do carregamento da sessão é respeitado.
- **Três exceções, uma por motivo**, definidas em `src/relatos/regras.py`:
  - `UsuarioNaoAutenticado`: visitante, `None` ou conta que já não existe (a API responde 401);
  - `UsuarioBloqueado`: conta inativa no banco (403);
  - `RelatoInvalido`: valor fora do domínio da RN01; `args[0]` é um dicionário `{campo: [mensagens]}` (400).
- **Retorno `Relato`, sem objeto de resultado.** Quem chama descobre que houve substituição por `relato.substituiu.exists()`, o relacionamento reverso de `substituido_por`, e então avisa o usuário.

## Alternativas consideradas

- Restrição única parcial no banco — descartada: a janela de tempo depende do relógio e não cabe numa restrição.
- *Advisory lock* do PostgreSQL — descartada: prende o código a uma função específica sem ganho sobre travar a linha do usuário, que já existe.
- Não travar e aceitar a corrida — descartada: dois relatos ativos na janela distorcem o status agregado (RN03).
- Devolver um objeto `RelatoRegistrado(relato, substituiu)` — descartada: quebra todos os chamadores e testes por um dado que o modelo já expõe.
- `PermissionDenied` e `ValidationError` do Django — descartadas: misturam a regra de negócio com a camada HTTP, e as três situações ficariam indistinguíveis.

## Consequências

- A garantia só vale em **PostgreSQL com isolamento `READ COMMITTED`** (o padrão). Em `REPEATABLE READ` a trava não basta, e no SQLite de desenvolvimento o `select_for_update` não faz nada.
- A serialização não tem teste automatizado, porque o SQLite não a prova de forma confiável. Os testes cobrem a lógica (janela, relatos ativos, releitura de `is_active`).
- A trava é por usuário, então só atrapalha quem envia relatos ao mesmo tempo; a contenção entre usuários diferentes é nula.
- Quem mudar o nível de isolamento ou trocar de banco precisa rever esta decisão.
