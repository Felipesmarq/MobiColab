"""Dicionário de dados do pipeline (RD03): colunas, tipos e significado de cada tabela.

É a fonte única dos tipos: o pipeline cria as tabelas a partir daqui e
converte os DataFrames lidos do banco com estes tipos. Para acrescentar uma
coluna, declare-a aqui primeiro.

Tipos: inteiro, real, texto, booleano, data_hora (com fuso), data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str
    descricao: str


@dataclass(frozen=True)
class Tabela:
    schema: str
    nome: str
    descricao: str
    colunas: tuple
    chave: tuple = ()

    @property
    def nomes(self):
        return [c.nome for c in self.colunas]


def _c(nome, tipo, descricao):
    return Coluna(nome, tipo, descricao)


# Metadados que toda tabela bronze acrescenta às colunas da origem.
META_BRONZE = (
    _c("_hash", "texto", "Impressão digital do conteúdo da linha; muda quando a origem muda"),
    _c("_extraido_em", "data_hora", "Momento da execução do pipeline que copiou esta versão"),
    _c(
        "_apagado_na_origem",
        "booleano",
        "Verdadeiro quando a linha sumiu da origem (ex.: mock gerado de novo); a prata a ignora",
    ),
)

# ---------------------------------------------------------------- bronze

BRONZE_RELATOS = Tabela(
    "bronze",
    "relatos",
    "Cópia imutável dos relatos do app. Cada mudança na origem vira uma nova versão.",
    (
        _c("id", "inteiro", "Identificador do relato no app"),
        _c("usuario_id", "inteiro", "Autor (só o número; nenhum dado pessoal)"),
        _c("linha_id", "inteiro", "Linha relatada"),
        _c("sentido", "texto", "ida ou volta"),
        _c("lotacao", "texto", "vazio, moderado ou lotado (RN01)"),
        _c("conforto_termico", "texto", "frio, agradavel, quente ou vazio se não informado"),
        _c("ar_condicionado", "texto", "funcionando, nao_funcionando, sem_ar ou vazio"),
        _c("vaga_pcd", "texto", "disponivel, ocupada ou vazio"),
        _c("prefixo_veiculo", "texto", "Prefixo do veículo, se informado"),
        _c("criado_em", "data_hora", "Momento do relato (hora do servidor)"),
        _c("substituido_por_id", "inteiro", "Relato que substituiu este (RN05), se houver"),
        _c("removido_em", "data_hora", "Momento da remoção pela moderação, se houver"),
        _c("motivo_remocao", "texto", "Motivo da remoção"),
        _c("origem", "texto", "mock ou real (usuário com e-mail @mock.mobicolab.invalid)"),
    )
    + META_BRONZE,
    chave=("id",),
)

BRONZE_CONFIRMACOES = Tabela(
    "bronze",
    "confirmacoes",
    "Cópia imutável dos votos 'ainda está assim' / 'não está mais assim' (RF05).",
    (
        _c("id", "inteiro", "Identificador do voto no app"),
        _c("relato_id", "inteiro", "Relato votado"),
        _c("usuario_id", "inteiro", "Quem votou (só o número)"),
        _c("ainda_vale", "booleano", "Verdadeiro = confirmação; falso = contestação"),
        _c("criado_em", "data_hora", "Momento do voto"),
    )
    + META_BRONZE,
    chave=("id",),
)

BRONZE_LINHAS = Tabela(
    "bronze",
    "linhas",
    "Cópia imutável do cadastro de linhas.",
    (
        _c("id", "inteiro", "Identificador da linha no app"),
        _c("codigo", "texto", "Código público da linha (ex.: 060)"),
        _c("nome", "texto", "Nome da linha"),
        _c("modal", "texto", "onibus, brt ou metro"),
        _c("operadora", "texto", "Empresa operadora, se conhecida"),
        _c("destino_ida", "texto", "Para onde vai no sentido ida"),
        _c("destino_volta", "texto", "Para onde vai no sentido volta (vazio se circular)"),
        _c("ativa", "booleano", "Linha em operação"),
        _c("gtfs_route_id", "texto", "route_id do GTFS, se importada"),
    )
    + META_BRONZE,
    chave=("id",),
)

BRONZE_PARADAS = Tabela(
    "bronze",
    "paradas",
    "Cópia imutável do cadastro de paradas.",
    (
        _c("id", "inteiro", "Identificador da parada no app"),
        _c("nome", "texto", "Nome da parada"),
        _c("lat", "real", "Latitude"),
        _c("lon", "real", "Longitude"),
        _c("eh_terminal", "booleano", "É Terminal Integrado"),
        _c("gtfs_stop_id", "texto", "stop_id do GTFS, se importada"),
    )
    + META_BRONZE,
    chave=("id",),
)

BRONZE_LINHAS_PARADAS = Tabela(
    "bronze",
    "linhas_paradas",
    "Cópia imutável dos itinerários (parada, sentido e ordem de cada linha).",
    (
        _c("id", "inteiro", "Identificador no app"),
        _c("linha_id", "inteiro", "Linha"),
        _c("parada_id", "inteiro", "Parada"),
        _c("sentido", "texto", "ida ou volta"),
        _c("ordem", "inteiro", "Posição da parada no itinerário"),
    )
    + META_BRONZE,
    chave=("id",),
)

BRONZE_TEMPERATURA = Tabela(
    "bronze",
    "temperatura",
    "Cópia imutável dos arquivos de temperatura horária de dados/externos/temperatura/.",
    (
        _c("data_hora", "data_hora", "Hora da medição"),
        _c("temperatura_c", "real", "Temperatura em °C"),
        _c("fonte", "texto", "inmet ou mock"),
        _c("arquivo", "texto", "Nome do arquivo de origem"),
    )
    + META_BRONZE,
    chave=("fonte", "data_hora"),
)

BRONZE_EXECUCOES = Tabela(
    "bronze",
    "execucoes",
    "Registro de cada execução da bronze: quantas linhas foram lidas e quantas eram novas.",
    (
        _c("extraido_em", "data_hora", "Momento da execução"),
        _c("tabela", "texto", "Tabela bronze"),
        _c("linhas_lidas", "inteiro", "Linhas lidas da origem"),
        _c("linhas_novas", "inteiro", "Versões novas acrescentadas"),
    ),
)

TABELAS_BRONZE = (
    BRONZE_RELATOS,
    BRONZE_CONFIRMACOES,
    BRONZE_LINHAS,
    BRONZE_PARADAS,
    BRONZE_LINHAS_PARADAS,
    BRONZE_TEMPERATURA,
)
