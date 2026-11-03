"""Camada ouro (RD03, issue #32): agregados para o dashboard e os notebooks.

É a fonte única do painel (RF06) e da EDA (RD04). Só tem agregados — nenhum
identificador de relato ou de usuário. Reconstruída do zero a partir da prata.

- `ouro.relatos_por_hora`: contagens por dia, hora, linha e sentido, com a
  temperatura da hora. Somando linhas dela sai qualquer recorte do painel.
- `ouro.taxas_por_linha`: taxas de lotado, falha do ar, calor e vaga ocupada
  por linha e faixa horária, sempre com numerador e denominador.
- `ouro.qualidade_diaria`: volume, remoções, substituições, votos e cobertura
  de temperatura por dia.
"""

import numpy as np

from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, VagaPcd

from . import banco
from .esquemas import (
    OURO_QUALIDADE_DIARIA,
    OURO_RELATOS_POR_HORA,
    OURO_TAXAS_POR_LINHA,
    PRATA_RELATOS,
    PRATA_RELATOS_HISTORICO,
    PRATA_TEMPERATURA,
)
from .prata import NAO_INFORMADO

CHAVE_HORA = [
    "data",
    "hora",
    "dia_semana",
    "fim_de_semana",
    "faixa_horaria",
    "linha_codigo",
    "linha_nome",
    "modal",
    "operadora",
    "sentido",
    "destino",
    "passa_por_terminal",
    "origem",
]

# coluna de contagem → (coluna da prata, valor contado)
INDICADORES = {
    "n_vazio": ("lotacao", Lotacao.VAZIO),
    "n_moderado": ("lotacao", Lotacao.MODERADO),
    "n_lotado": ("lotacao", Lotacao.LOTADO),
    "n_ar_funcionando": ("ar_condicionado", ArCondicionado.FUNCIONANDO),
    "n_ar_nao_funcionando": ("ar_condicionado", ArCondicionado.NAO_FUNCIONANDO),
    "n_sem_ar": ("ar_condicionado", ArCondicionado.SEM_AR),
    "n_ar_nao_informado": ("ar_condicionado", NAO_INFORMADO),
    "n_frio": ("conforto_termico", ConfortoTermico.FRIO),
    "n_agradavel": ("conforto_termico", ConfortoTermico.AGRADAVEL),
    "n_quente": ("conforto_termico", ConfortoTermico.QUENTE),
    "n_conforto_nao_informado": ("conforto_termico", NAO_INFORMADO),
    "n_vaga_disponivel": ("vaga_pcd", VagaPcd.DISPONIVEL),
    "n_vaga_ocupada": ("vaga_pcd", VagaPcd.OCUPADA),
    "n_vaga_nao_informada": ("vaga_pcd", NAO_INFORMADO),
}


def executar():
    """Reconstrói todas as tabelas da ouro. Devolve {tabela: linhas gravadas}."""
    banco.garantir_schemas()
    relatos = banco.ler(PRATA_RELATOS)
    historico = banco.ler(PRATA_RELATOS_HISTORICO)
    temperatura = banco.ler(PRATA_TEMPERATURA)

    por_hora = montar_relatos_por_hora(relatos, temperatura)
    taxas = montar_taxas_por_linha(por_hora)
    qualidade = montar_qualidade_diaria(historico, relatos, temperatura)

    resumo = {}
    for tabela, df in (
        (OURO_RELATOS_POR_HORA, por_hora),
        (OURO_TAXAS_POR_LINHA, taxas),
        (OURO_QUALIDADE_DIARIA, qualidade),
    ):
        banco.recriar(tabela, df)
        resumo[tabela.nome] = len(df)
    return resumo


def montar_relatos_por_hora(relatos, temperatura):
    if relatos.empty:
        return banco.vazio(OURO_RELATOS_POR_HORA)

    df = relatos.copy()
    for coluna, (origem, valor) in INDICADORES.items():
        df[coluna] = (df[origem] == valor).astype(int)
    df["n_relatos"] = 1
    contagens = ["n_relatos", *INDICADORES, "n_confirmacoes", "n_contestacoes"]

    agregado = df.groupby(CHAVE_HORA, dropna=False, as_index=False)[contagens].sum()
    clima = temperatura[["data", "hora", "temperatura_c", "fonte"]].rename(
        columns={"fonte": "temperatura_fonte"}
    )
    agregado = agregado.merge(clima, on=["data", "hora"], how="left")
    agregado["temperatura_fonte"] = agregado["temperatura_fonte"].fillna("ausente")
    return banco.tipar(agregado, OURO_RELATOS_POR_HORA)


def montar_taxas_por_linha(por_hora):
    if por_hora.empty:
        return banco.vazio(OURO_TAXAS_POR_LINHA)

    chave = ["linha_codigo", "linha_nome", "modal", "operadora", "faixa_horaria", "origem"]
    somas = por_hora.groupby(chave, dropna=False, as_index=False)[
        [
            "n_relatos",
            "n_lotado",
            "n_ar_funcionando",
            "n_ar_nao_funcionando",
            "n_frio",
            "n_agradavel",
            "n_quente",
            "n_vaga_disponivel",
            "n_vaga_ocupada",
        ]
    ].sum()
    somas["n_ar_climatizado_informado"] = somas["n_ar_funcionando"] + somas["n_ar_nao_funcionando"]
    somas["n_conforto_informado"] = somas["n_frio"] + somas["n_agradavel"] + somas["n_quente"]
    somas["n_vaga_informada"] = somas["n_vaga_disponivel"] + somas["n_vaga_ocupada"]

    somas["taxa_lotado"] = taxa(somas["n_lotado"], somas["n_relatos"])
    somas["taxa_ar_nao_funcionando"] = taxa(
        somas["n_ar_nao_funcionando"], somas["n_ar_climatizado_informado"]
    )
    somas["taxa_quente"] = taxa(somas["n_quente"], somas["n_conforto_informado"])
    somas["taxa_vaga_ocupada"] = taxa(somas["n_vaga_ocupada"], somas["n_vaga_informada"])
    return banco.tipar(somas, OURO_TAXAS_POR_LINHA)


def taxa(numerador, denominador):
    """Proporção; vazia (não zero) quando o denominador é zero."""
    numerador = numerador.astype(float)
    denominador = denominador.astype(float)
    return (numerador / denominador.replace(0, np.nan)).astype(float)


def montar_qualidade_diaria(historico, relatos, temperatura):
    if historico.empty:
        return banco.vazio(OURO_QUALIDADE_DIARIA)

    flags = historico.assign(
        n_relatos_total=1,
        n_validos=historico["valido"].astype(int),
        n_removidos=historico["removido"].astype(int),
        n_substituidos=historico["substituido"].astype(int),
        n_fora_do_dominio=historico["fora_do_dominio"].astype(int),
    )
    por_dia = flags.groupby(["data", "origem"], as_index=False).agg(
        n_relatos_total=("n_relatos_total", "sum"),
        n_validos=("n_validos", "sum"),
        n_removidos=("n_removidos", "sum"),
        n_substituidos=("n_substituidos", "sum"),
        n_fora_do_dominio=("n_fora_do_dominio", "sum"),
        n_usuarios_ativos=("usuario_id", "nunique"),
    )

    votos = relatos.groupby(["data", "origem"], as_index=False).agg(
        n_confirmacoes=("n_confirmacoes", "sum"),
        n_contestacoes=("n_contestacoes", "sum"),
        n_linhas_com_relato=("linha_id", "nunique"),
    )
    por_dia = por_dia.merge(votos, on=["data", "origem"], how="left")

    if temperatura.empty:
        por_dia["horas_com_temperatura"] = 0
        por_dia["horas_temperatura_interpolada"] = 0
    else:
        clima = (
            temperatura.assign(
                com_valor=temperatura["temperatura_c"].notna().astype(int),
                interpolada_int=temperatura["interpolada"].astype(bool).astype(int),
            )
            .groupby("data", as_index=False)
            .agg(
                horas_com_temperatura=("com_valor", "sum"),
                horas_temperatura_interpolada=("interpolada_int", "sum"),
            )
        )
        por_dia = por_dia.merge(clima, on="data", how="left")

    for coluna in (
        "n_confirmacoes",
        "n_contestacoes",
        "n_linhas_com_relato",
        "horas_com_temperatura",
        "horas_temperatura_interpolada",
    ):
        por_dia[coluna] = por_dia[coluna].fillna(0)
    return banco.tipar(por_dia, OURO_QUALIDADE_DIARIA)
