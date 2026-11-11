# 0027 — Tailwind CLI standalone e HTMX locais

- **Data:** 11/11/2026
- **Fase:** 1
- **Status:** aceita
- **Requisitos ligados:** RNF01, RNF04

## Contexto

O layout base (issue #2) precisa de CSS utilitário e de HTMX. A issue deixou em aberto como carregar o Tailwind: CLI standalone ou CDN. O projeto roda em Django com Docker e não tem Node.

## Decisão

- **Tailwind CLI standalone** (v4.1.11): `python scripts/tailwind.py` baixa o binário para `.tools/` (ignorado pelo git) e gera `src/static/css/tailwind.css`. A entrada fica em `tailwind/entrada.css`. Use `--watch` durante o desenvolvimento.
- **O CSS gerado é versionado.** Rodar o app, os testes e o CI não exige o binário; só quem muda classes nos templates precisa regenerar.
- **HTMX 2.0.4 copiado para `src/static/js/htmx.min.js`**, sem CDN. O app funciona sem depender de serviço externo.
- **Menu na base da tela**, para ser alcançado com o polegar (RNF01).

## Alternativas consideradas

- Tailwind via CDN — descartada: a própria documentação do Tailwind não recomenda para produção, o CSS não é otimizado e o app dependeria de rede externa.
- Node + npm — descartada: adicionaria uma toolchain inteira só para gerar um CSS.
- Gerar o CSS no build do Docker — descartada por ora: complica o Dockerfile e o CI sem ganho no tamanho do MVP.

## Consequências

- Quem altera classes nos templates deve rodar `python scripts/tailwind.py` e commitar o CSS atualizado; esquecer deixa a página sem o estilo novo.
- Atualizar o Tailwind ou o HTMX é trocar a versão no script ou o arquivo em `static/js`.
