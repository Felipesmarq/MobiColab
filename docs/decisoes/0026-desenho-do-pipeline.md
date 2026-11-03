# 0026 — Desenho do pipeline bronze → prata → ouro

- **Data:** 03/11/2026
- **Fase:** 1
- **Status:** aceita
- **Requisitos ligados:** RD03, RD02, RNF05

## Contexto

O RD03 pede três camadas no PostgreSQL: bronze imutável e só acrescentada, prata reconstruível a partir da bronze e ouro como fonte única do dashboard e dos notebooks. Os relatos mudam depois de criados (são substituídos ou removidos), e o mock pode ser gerado de novo. A equipe de CC trabalha em pandas.

## Decisão

- **Transformações em pandas**, lendo e gravando pela conexão do próprio Django (`dados/pipeline/banco.py`). O pipeline roda nas mesmas transações do app e dos testes, sem SQLAlchemy.
- **Dicionário de dados único** (`dados/pipeline/esquemas.py`): cada tabela declara colunas, tipos e significado. As tabelas são criadas a partir dele e os DataFrames lidos são convertidos com ele.
- **Bronze versionada por impressão digital.** Cada linha leva um `_hash` do conteúdo e o `_extraido_em` da execução. A cada execução entra uma versão nova só quando a chave é nova ou o conteúdo mudou. Linha que some da origem ganha uma versão com `_apagado_na_origem`. Nada é editado ou apagado. A prata usa a versão mais recente de cada chave.
- **Origem rotulada:** cada relato da bronze leva `origem` = `mock` ou `real`, pelo domínio do e-mail do autor (ADR 0025). E-mail e nome nunca saem do app (RNF05).
- **Fontes externas por arquivo:** CSVs em `dados/externos/temperatura/` com `data_hora`, `temperatura_c` e `fonte` (hoje o mock; depois o INMET, issue #26).
- **SQLite só para desenvolvimento:** sem schemas, `bronze.relatos` vira `bronze__relatos`. O CI testa no PostgreSQL de verdade.

## Alternativas consideradas

- Copiar só IDs novos para a bronze — descartada: perderia substituições e remoções que acontecem depois do relato.
- Transformações em SQL puro — descartada: a equipe de CC mantém o pipeline, e pandas é a ferramenta da disciplina.
- dbt ou Airflow — descartadas: infraestrutura demais para o tamanho do MVP.

## Consequências

- A bronze cresce a cada mudança na origem; no volume do MVP (dezenas de milhares de linhas) isso é desprezível.
- Para acrescentar uma coluna, muda-se primeiro `esquemas.py`. Tabelas bronze já existentes precisam de migração manual da coluna.
