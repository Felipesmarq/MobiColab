# 0021 — Fluxo de trabalho com GitHub Issues e Projects

- **Data:** 21/10/2026
- **Fase:** 0
- **Status:** aceita
- **Requisitos ligados:** Seção 11 da spec

## Contexto

O grupo tem muitas pessoas e um Trello pouco organizado. As tarefas precisam ser pequenas, independentes e ligadas à spec.

## Decisão

- **Trunk-based:** `main` protegida; branches curtas (`rf03-envio-relato`); merge por PR com CI verde e uma revisão.
- **Tarefas:** issues no GitHub, num quadro GitHub Projects (Backlog → Fazendo → Revisão → Feito). Cada issue cita o requisito no título (ex.: "[RF03] validar lotação obrigatória"), tem labels de frente (`backend`, `dados`) e de requisito, e cabe em 1–2 dias.
- **Templates** de issue e de PR com checklist: requisito ligado, testes, spec atualizada, ADR (se houver decisão).
- Tudo em português: issues, commits, PRs e documentação.

Este formato é um teste; se funcionar, pode ser espelhado no Trello depois.

## Alternativas consideradas

- Continuar no Trello — descartada por ora: não liga tarefa a código e PR.
- Git flow com `develop` — descartada: mais cerimônia do que o prazo permite.

## Consequências

- O administrador do repositório pode fazer merge sem aprovação (a proteção não se aplica a administradores), para destravar a fundação; da fase 1 em diante, a revisão de um colega vale para todos.
