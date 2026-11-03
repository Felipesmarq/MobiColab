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

# ---------------------------------------------------------------- prata

_COLUNAS_RELATO_PRATA = (
    _c("id", "inteiro", "Identificador do relato"),
    _c("usuario_id", "inteiro", "Autor (só o número)"),
    _c("linha_id", "inteiro", "Linha relatada"),
    _c("sentido", "texto", "ida ou volta"),
    _c("lotacao", "texto", "vazio, moderado ou lotado"),
    _c("conforto_termico", "texto", "frio, agradavel, quente ou nao_informado"),
    _c("ar_condicionado", "texto", "funcionando, nao_funcionando, sem_ar ou nao_informado"),
    _c("vaga_pcd", "texto", "disponivel, ocupada ou nao_informado"),
    _c("prefixo_informado", "booleano", "O passageiro informou o prefixo do veículo"),
    _c("criado_em", "data_hora", "Momento do relato (UTC)"),
    _c("data", "data", "Dia do relato no fuso America/Recife"),
    _c("hora", "inteiro", "Hora do relato (0 a 23) no fuso America/Recife"),
    _c("dia_semana", "inteiro", "0 = segunda … 6 = domingo"),
    _c("fim_de_semana", "booleano", "Sábado ou domingo"),
    _c(
        "faixa_horaria",
        "texto",
        "madrugada, inicio_manha, pico_manha, entre_picos, pico_tarde, noite",
    ),
    _c("origem", "texto", "mock ou real"),
)

PRATA_RELATOS_HISTORICO = Tabela(
    "prata",
    "relatos_historico",
    "Versão atual de todo relato da bronze, inclusive removidos e substituídos, com o motivo de "
    "cada um ficar fora da análise.",
    _COLUNAS_RELATO_PRATA
    + (
        _c("removido", "booleano", "Removido pela moderação (RF07)"),
        _c(
            "substituido", "booleano", "Substituído por um relato mais novo do mesmo usuário (RN05)"
        ),
        _c("fora_do_dominio", "booleano", "Algum valor fora dos domínios da RN01"),
        _c("valido", "booleano", "Entra na análise: não removido, não substituído, no domínio"),
    ),
    chave=("id",),
)

PRATA_RELATOS = Tabela(
    "prata",
    "relatos",
    "Relatos válidos para análise, já com os dados da linha e os votos recebidos.",
    _COLUNAS_RELATO_PRATA
    + (
        _c("linha_codigo", "texto", "Código público da linha"),
        _c("linha_nome", "texto", "Nome da linha"),
        _c("modal", "texto", "onibus, brt ou metro"),
        _c("operadora", "texto", "Operadora ou nao_informada"),
        _c("destino", "texto", "Para onde o veículo ia no sentido relatado"),
        _c(
            "passa_por_terminal",
            "booleano",
            "O itinerário desse sentido passa por Terminal Integrado",
        ),
        _c("n_confirmacoes", "inteiro", "Votos 'ainda está assim'"),
        _c("n_contestacoes", "inteiro", "Votos 'não está mais assim'"),
    ),
    chave=("id",),
)

PRATA_CONFIRMACOES = Tabela(
    "prata",
    "confirmacoes",
    "Votos atuais sobre relatos que existem na prata.",
    (
        _c("id", "inteiro", "Identificador do voto"),
        _c("relato_id", "inteiro", "Relato votado"),
        _c("usuario_id", "inteiro", "Quem votou (só o número)"),
        _c("ainda_vale", "booleano", "Verdadeiro = confirmação; falso = contestação"),
        _c("criado_em", "data_hora", "Momento do voto (UTC)"),
    ),
    chave=("id",),
)

PRATA_LINHAS = Tabela(
    "prata",
    "linhas",
    "Cadastro atual de linhas.",
    (
        _c("id", "inteiro", "Identificador da linha"),
        _c("codigo", "texto", "Código público"),
        _c("nome", "texto", "Nome"),
        _c("modal", "texto", "onibus, brt ou metro"),
        _c("operadora", "texto", "Operadora ou nao_informada"),
        _c("destino_ida", "texto", "Destino no sentido ida"),
        _c("destino_volta", "texto", "Destino no sentido volta"),
        _c("ativa", "booleano", "Em operação"),
        _c("passa_por_terminal_ida", "booleano", "Itinerário de ida passa por Terminal Integrado"),
        _c(
            "passa_por_terminal_volta",
            "booleano",
            "Itinerário de volta passa por Terminal Integrado",
        ),
    ),
    chave=("id",),
)

PRATA_TEMPERATURA = Tabela(
    "prata",
    "temperatura",
    "Série horária única de temperatura: INMET quando houver, mock senão; lacunas de até 2 h "
    "interpoladas (RD02).",
    (
        _c("data_hora", "data_hora", "Início da hora (UTC)"),
        _c("data", "data", "Dia no fuso America/Recife"),
        _c("hora", "inteiro", "Hora (0 a 23) no fuso America/Recife"),
        _c("temperatura_c", "real", "Temperatura em °C (vazia em lacunas maiores que 2 h)"),
        _c("fonte", "texto", "inmet, mock, interpolada ou ausente"),
        _c("interpolada", "booleano", "Valor estimado entre duas medições"),
    ),
    chave=("data_hora",),
)

TABELAS_PRATA = (
    PRATA_RELATOS_HISTORICO,
    PRATA_RELATOS,
    PRATA_CONFIRMACOES,
    PRATA_LINHAS,
    PRATA_TEMPERATURA,
)

# ---------------------------------------------------------------- ouro
# Só agregados: nenhuma tabela da ouro tem identificador de relato ou de usuário (RF06).
# As taxas ficam com o numerador e o denominador, para o dashboard poder somar contagens
# em qualquer recorte e recalcular a taxa (média de taxas engana).

_CONTAGENS_DIMENSOES = (
    _c("n_relatos", "inteiro", "Relatos válidos"),
    _c("n_vazio", "inteiro", "Relatos com lotação vazio"),
    _c("n_moderado", "inteiro", "Relatos com lotação moderado"),
    _c("n_lotado", "inteiro", "Relatos com lotação lotado"),
    _c("n_ar_funcionando", "inteiro", "Ar-condicionado funcionando"),
    _c("n_ar_nao_funcionando", "inteiro", "Ar-condicionado não funcionando"),
    _c("n_sem_ar", "inteiro", "Veículo sem ar"),
    _c("n_ar_nao_informado", "inteiro", "Ar não informado"),
    _c("n_frio", "inteiro", "Conforto térmico frio"),
    _c("n_agradavel", "inteiro", "Conforto térmico agradável"),
    _c("n_quente", "inteiro", "Conforto térmico quente"),
    _c("n_conforto_nao_informado", "inteiro", "Conforto térmico não informado"),
    _c("n_vaga_disponivel", "inteiro", "Vaga PCD disponível"),
    _c("n_vaga_ocupada", "inteiro", "Vaga PCD ocupada"),
    _c("n_vaga_nao_informada", "inteiro", "Vaga PCD não informada"),
    _c("n_confirmacoes", "inteiro", "Confirmações recebidas por esses relatos"),
    _c("n_contestacoes", "inteiro", "Contestações recebidas por esses relatos"),
)

OURO_RELATOS_POR_HORA = Tabela(
    "ouro",
    "relatos_por_hora",
    "Contagens por dia, hora, linha e sentido: base de todos os gráficos e filtros do painel "
    "(modal, linha, período e faixa horária).",
    (
        _c("data", "data", "Dia (America/Recife)"),
        _c("hora", "inteiro", "Hora (0 a 23, America/Recife)"),
        _c("dia_semana", "inteiro", "0 = segunda … 6 = domingo"),
        _c("fim_de_semana", "booleano", "Sábado ou domingo"),
        _c("faixa_horaria", "texto", "Faixa horária da prata"),
        _c("linha_codigo", "texto", "Código da linha"),
        _c("linha_nome", "texto", "Nome da linha"),
        _c("modal", "texto", "onibus, brt ou metro"),
        _c("operadora", "texto", "Operadora ou nao_informada"),
        _c("sentido", "texto", "ida ou volta"),
        _c("destino", "texto", "Destino do sentido"),
        _c("passa_por_terminal", "booleano", "O sentido passa por Terminal Integrado"),
        _c("origem", "texto", "mock ou real"),
    )
    + _CONTAGENS_DIMENSOES
    + (
        _c("temperatura_c", "real", "Temperatura externa na hora (vazia se ausente)"),
        _c("temperatura_fonte", "texto", "inmet, mock, interpolada ou ausente"),
    ),
    chave=("data", "hora", "linha_codigo", "sentido", "origem"),
)

OURO_TAXAS_POR_LINHA = Tabela(
    "ouro",
    "taxas_por_linha",
    "Taxas por linha e faixa horária, com numerador e denominador (H1–H4 do RD01).",
    (
        _c("linha_codigo", "texto", "Código da linha"),
        _c("linha_nome", "texto", "Nome da linha"),
        _c("modal", "texto", "onibus, brt ou metro"),
        _c("operadora", "texto", "Operadora ou nao_informada"),
        _c("faixa_horaria", "texto", "Faixa horária"),
        _c("origem", "texto", "mock ou real"),
        _c("n_relatos", "inteiro", "Relatos válidos (denominador da taxa de lotado)"),
        _c("n_lotado", "inteiro", "Relatos lotado"),
        _c("taxa_lotado", "real", "n_lotado / n_relatos (H1)"),
        _c(
            "n_ar_climatizado_informado", "inteiro", "Relatos com ar funcionando ou não funcionando"
        ),
        _c("n_ar_nao_funcionando", "inteiro", "Relatos com ar não funcionando"),
        _c("taxa_ar_nao_funcionando", "real", "Falha entre veículos climatizados informados (H2)"),
        _c("n_conforto_informado", "inteiro", "Relatos com conforto térmico informado"),
        _c("n_quente", "inteiro", "Relatos quente"),
        _c("taxa_quente", "real", "n_quente / n_conforto_informado (H3)"),
        _c("n_vaga_informada", "inteiro", "Relatos com vaga PCD informada"),
        _c("n_vaga_ocupada", "inteiro", "Relatos com vaga ocupada"),
        _c("taxa_vaga_ocupada", "real", "n_vaga_ocupada / n_vaga_informada (H4)"),
    ),
    chave=("linha_codigo", "faixa_horaria", "origem"),
)

OURO_QUALIDADE_DIARIA = Tabela(
    "ouro",
    "qualidade_diaria",
    "Indicadores diários de qualidade e volume (página 'Qualidade dos dados' do painel).",
    (
        _c("data", "data", "Dia (America/Recife)"),
        _c("origem", "texto", "mock ou real"),
        _c("n_relatos_total", "inteiro", "Todos os relatos do dia, inclusive fora da análise"),
        _c("n_validos", "inteiro", "Relatos que entram na análise"),
        _c("n_removidos", "inteiro", "Removidos pela moderação"),
        _c("n_substituidos", "inteiro", "Substituídos pelo mesmo usuário (RN05)"),
        _c("n_fora_do_dominio", "inteiro", "Com valor fora da RN01"),
        _c("n_confirmacoes", "inteiro", "Confirmações recebidas pelos relatos válidos do dia"),
        _c("n_contestacoes", "inteiro", "Contestações recebidas pelos relatos válidos do dia"),
        _c("n_usuarios_ativos", "inteiro", "Usuários distintos que relataram"),
        _c("n_linhas_com_relato", "inteiro", "Linhas com ao menos um relato válido"),
        _c(
            "horas_com_temperatura",
            "inteiro",
            "Horas do dia com temperatura (medida ou interpolada)",
        ),
        _c("horas_temperatura_interpolada", "inteiro", "Horas com temperatura interpolada"),
    ),
    chave=("data", "origem"),
)

TABELAS_OURO = (OURO_RELATOS_POR_HORA, OURO_TAXAS_POR_LINHA, OURO_QUALIDADE_DIARIA)
