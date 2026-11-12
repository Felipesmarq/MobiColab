# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`docs/spec.md`**: the source of truth for requirements (RF, RN, RNF, RD).
- **`GLOSSARY.md`** at the repo root, if it exists.
- **`docs/decisoes/`**: this repo's ADRs (index in `docs/decisoes/README.md`, template at the end of it). Read the ones that touch the area you're about to work in. Where a skill says `docs/adr/`, use `docs/decisoes/`.

If `GLOSSARY.md` doesn't exist, **proceed silently**. Don't flag its absence; don't suggest creating it upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates it lazily when terms or decisions actually get resolved.

## File structure

Single-context repo:

```
/
├── GLOSSARY.md          (created lazily)
├── docs/
│   ├── spec.md
│   └── decisoes/        ← ADRs, numbered 0001, 0002, …
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids. The project's documents are written in Brazilian Portuguese; keep domain terms in Portuguese.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR 0013 (substituição de relato), but worth reopening because…_

New ADRs follow the template in `docs/decisoes/README.md` and get a line in its index.
