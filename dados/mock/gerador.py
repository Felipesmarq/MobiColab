"""Gerador de dados mockados (RD02, issue #28).

Grava usuários, relatos e confirmações no banco do app, com o mesmo esquema
dos dados reais, e escreve a série horária de temperatura em
`dados/externos/temperatura/`. Tudo sai de `config.yaml` e de uma semente
fixa: a mesma configuração gera sempre os mesmos dados.

Os dados são marcados como mock pelo domínio do e-mail dos usuários
(`@mock.mobicolab.invalid`); o pipeline usa essa marca para rotular cada
relato.
"""

import csv
import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from relatos.models import ArCondicionado, Confirmacao, ConfortoTermico, Lotacao, Relato, VagaPcd
from transporte.models import Linha, Sentido

DOMINIO_MOCK = "mock.mobicolab.invalid"
PASTA_TEMPERATURA = Path(settings.BASE_DIR).parent / "dados" / "externos" / "temperatura"
ARQUIVO_TEMPERATURA = "temperatura_mock.csv"
MOTIVO_REMOCAO = "Removido pela moderação (dado mockado)"

NIVEIS = [Lotacao.VAZIO, Lotacao.MODERADO, Lotacao.LOTADO]


class GeracaoInvalida(Exception):
    pass


@dataclass
class Resultado:
    usuarios: int = 0
    relatos: int = 0
    substituidos: int = 0
    removidos: int = 0
    confirmacoes: int = 0
    contestacoes: int = 0
    horas_temperatura: int = 0
    arquivo_temperatura: Path | None = None


def eh_mock(email):
    return email.endswith("@" + DOMINIO_MOCK)


def limpar_mock():
    """Apaga só o que o gerador criou. Dados reais nunca são tocados."""
    Usuario = get_user_model()
    usuarios = Usuario.objects.filter(email__endswith="@" + DOMINIO_MOCK)
    with transaction.atomic():
        Confirmacao.objects.filter(usuario__in=usuarios).delete()
        Confirmacao.objects.filter(relato__usuario__in=usuarios).delete()
        Relato.objects.filter(usuario__in=usuarios).delete()
        return usuarios.delete()[1].get(Usuario._meta.label, 0)


def gerar(config, fim=None, pasta_temperatura=None):
    """Gera o período de `config['periodo.dias']` dias terminando em `fim` (padrão: hoje)."""
    Usuario = get_user_model()
    if Usuario.objects.filter(email__endswith="@" + DOMINIO_MOCK).exists():
        raise GeracaoInvalida("Já existem dados mockados. Use --limpar para gerar de novo.")

    trajetos = _trajetos()
    if not trajetos:
        raise GeracaoInvalida(
            "Nenhuma linha ativa. Carregue as linhas antes: python manage.py loaddata linhas_dev"
        )

    fuso = ZoneInfo(settings.TIME_ZONE)
    agora = timezone.now()
    fim = fim or timezone.localdate()
    dias = [fim - timedelta(days=d) for d in range(config["periodo.dias"] - 1, -1, -1)]
    rng = np.random.default_rng(config["reprodutibilidade.semente"])
    resultado = Resultado()

    temperatura = _temperatura(config, dias, rng)
    resultado.arquivo_temperatura = _gravar_temperatura(
        temperatura, dias, fuso, pasta_temperatura or PASTA_TEMPERATURA
    )
    resultado.horas_temperatura = len(temperatura)

    with transaction.atomic():
        usuarios, pesos, trolls = _usuarios(config, rng)
        resultado.usuarios = len(usuarios)
        falha_por_linha = _falha_do_ar_por_linha(config, trajetos, rng)

        relatos, eh_troll = [], []
        substituicoes = []  # (índice do relato antigo, índice do novo)
        for dia in dias:
            fim_de_semana = dia.weekday() >= 5
            for hora in range(24):
                fator = config["volume.perfil_horario"][hora]
                if fim_de_semana:
                    fator *= config["volume.fator_fim_de_semana"]
                media = config["volume.relatos_por_hora_pico"] * fator
                inicio_hora = datetime.combine(dia, time(hora), tzinfo=fuso)
                for linha, sentido, passa_terminal in trajetos:
                    for _ in range(rng.poisson(media)):
                        criado_em = inicio_hora + timedelta(seconds=int(rng.integers(0, 3600)))
                        if criado_em > agora:
                            continue
                        autor = int(rng.choice(len(usuarios), p=pesos))
                        troll = autor in trolls
                        relato = _relato(
                            config,
                            rng,
                            usuarios[autor],
                            linha,
                            sentido,
                            criado_em,
                            hora,
                            passa_terminal,
                            temperatura[(dia, hora)],
                            falha_por_linha[linha.pk],
                            troll,
                        )
                        relatos.append(relato)
                        eh_troll.append(troll)
                        _talvez_remover(config, rng, relato, troll, agora)

                        if not troll and rng.random() < config["interacoes.prob_substituicao"]:
                            atraso = rng.uniform(1, settings.RELATO_INTERVALO_MIN - 0.5)
                            novo_em = criado_em + timedelta(minutes=float(atraso))
                            if novo_em <= agora:
                                novo = _relato(
                                    config,
                                    rng,
                                    usuarios[autor],
                                    linha,
                                    sentido,
                                    novo_em,
                                    hora,
                                    passa_terminal,
                                    temperatura[(dia, hora)],
                                    falha_por_linha[linha.pk],
                                    False,
                                )
                                substituicoes.append((len(relatos) - 1, len(relatos)))
                                relatos.append(novo)
                                eh_troll.append(False)

        Relato.objects.bulk_create(relatos, batch_size=2000)
        antigos = []
        for i_antigo, i_novo in substituicoes:
            relatos[i_antigo].substituido_por = relatos[i_novo]
            antigos.append(relatos[i_antigo])
        Relato.objects.bulk_update(antigos, ["substituido_por"], batch_size=2000)

        confirmacoes = _confirmacoes(config, rng, relatos, eh_troll, usuarios, antigos, agora)
        Confirmacao.objects.bulk_create(confirmacoes, batch_size=2000)

    resultado.relatos = len(relatos)
    resultado.substituidos = len(antigos)
    resultado.removidos = sum(1 for r in relatos if r.removido_em)
    resultado.confirmacoes = sum(1 for c in confirmacoes if c.ainda_vale)
    resultado.contestacoes = len(confirmacoes) - resultado.confirmacoes
    return resultado


def _trajetos():
    """(linha, sentido, passa por Terminal Integrado) para cada sentido de cada linha ativa."""
    trajetos = []
    for linha in Linha.objects.filter(ativa=True).prefetch_related("itinerario__parada"):
        sentidos = [Sentido.IDA] if linha.eh_circular else [Sentido.IDA, Sentido.VOLTA]
        for sentido in sentidos:
            terminal = any(
                item.parada.eh_terminal
                for item in linha.itinerario.all()
                if item.sentido == sentido
            )
            trajetos.append((linha, sentido, terminal))
    return trajetos


def _temperatura(config, dias, rng):
    """Série horária sintética: ciclo diário em cosseno + variação entre dias + ruído."""
    serie = {}
    for dia in dias:
        media = config["temperatura.media_diaria_c"] + rng.normal(
            0, config["temperatura.variacao_entre_dias_c"]
        )
        for hora in range(24):
            fase = 2 * math.pi * (hora - config["temperatura.hora_mais_quente"]) / 24
            valor = media + config["temperatura.amplitude_diaria_c"] * math.cos(fase)
            valor += rng.normal(0, config["temperatura.ruido_horario_c"])
            serie[(dia, hora)] = round(float(valor), 1)
    return serie


def _gravar_temperatura(serie, dias, fuso, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ARQUIVO_TEMPERATURA
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["data_hora", "temperatura_c", "fonte"])
        for dia in dias:
            for hora in range(24):
                momento = datetime.combine(dia, time(hora), tzinfo=fuso)
                escritor.writerow([momento.isoformat(), serie[(dia, hora)], "mock"])
    return caminho


def _usuarios(config, rng):
    Usuario = get_user_model()
    quantidade = config["usuarios.quantidade"]
    novos = []
    for i in range(1, quantidade + 1):
        usuario = Usuario(email=f"mock-{i:04d}@{DOMINIO_MOCK}")
        usuario.set_unusable_password()
        novos.append(usuario)
    usuarios = Usuario.objects.bulk_create(novos, batch_size=2000)

    atividade = rng.lognormal(0, config["usuarios.dispersao_atividade"], size=quantidade)
    n_trolls = round(quantidade * config["usuarios.fracao_trolls"])
    trolls = (
        set(rng.choice(quantidade, size=n_trolls, replace=False).tolist()) if n_trolls else set()
    )
    for i in trolls:
        atividade[i] *= config["usuarios.atividade_troll"]
    return usuarios, atividade / atividade.sum(), trolls


def _falha_do_ar_por_linha(config, trajetos, rng):
    """Probabilidade de o ar estar quebrado, variando entre linhas (H2)."""
    linhas = {linha.pk for linha, _, _ in trajetos}
    return {
        pk: float(
            np.clip(
                rng.normal(
                    config["climatizacao.prob_ar_nao_funcionando"],
                    config["climatizacao.variacao_ar_entre_linhas"],
                ),
                0.02,
                0.95,
            )
        )
        for pk in sorted(linhas)
    }


def _escolher(rng, distribuicao):
    valores = list(distribuicao)
    probs = np.array([distribuicao[v] for v in valores], dtype=float)
    return valores[int(rng.choice(len(valores), p=probs / probs.sum()))]


def _distribuicao_lotacao(config, hora, passa_terminal):
    if hora in config["lotacao.horas_pico"]:
        base = dict(config["lotacao.pico"])
    elif hora in config["lotacao.horas_madrugada"]:
        base = dict(config["lotacao.madrugada"])
    else:
        base = dict(config["lotacao.fora_do_pico"])
    if passa_terminal:
        acrescimo = min(config["lotacao.acrescimo_lotado_terminal"], 1 - base["lotado"])
        do_vazio = min(acrescimo, base["vazio"])
        base["vazio"] -= do_vazio
        base["moderado"] -= acrescimo - do_vazio
        base["lotado"] += acrescimo
    return base


def _relato(
    config,
    rng,
    usuario,
    linha,
    sentido,
    criado_em,
    hora,
    passa_terminal,
    temperatura,
    prob_falha,
    troll,
):
    if troll:
        # Trolls relatam ao acaso: sem relação com hora, temperatura ou lotação.
        return Relato(
            usuario=usuario,
            linha=linha,
            sentido=sentido,
            criado_em=criado_em,
            lotacao=NIVEIS[int(rng.integers(3))],
            conforto_termico=_ao_acaso(rng, ConfortoTermico),
            ar_condicionado=_ao_acaso(rng, ArCondicionado),
            vaga_pcd=_ao_acaso(rng, VagaPcd),
        )

    lotacao = _escolher(rng, _distribuicao_lotacao(config, hora, passa_terminal))

    fracao_ar = config["climatizacao.fracao_frota_com_ar_por_linha"].get(
        linha.codigo, config["climatizacao.fracao_frota_com_ar"]
    )
    if rng.random() < fracao_ar:
        estado_ar = (
            ArCondicionado.NAO_FUNCIONANDO
            if rng.random() < prob_falha
            else ArCondicionado.FUNCIONANDO
        )
    else:
        estado_ar = ArCondicionado.SEM_AR
    prob_informar_ar = {
        ArCondicionado.FUNCIONANDO: config["preenchimento.ar_quando_funcionando"],
        ArCondicionado.NAO_FUNCIONANDO: config["preenchimento.ar_quando_nao_funcionando"],
        ArCondicionado.SEM_AR: config["preenchimento.ar_quando_sem_ar"],
    }[estado_ar]

    conforto = ""
    if rng.random() < config["preenchimento.conforto_termico"]:
        chave = "ar_funcionando" if estado_ar == ArCondicionado.FUNCIONANDO else "sem_ar"
        p = config[f"conforto_termico.{chave}"]
        variacao = temperatura - config["conforto_termico.temperatura_referencia_c"]
        prob_quente = float(
            np.clip(p["prob_quente"] + p["aumento_por_grau"] * variacao, 0, 1 - p["prob_frio"])
        )
        conforto = _escolher(
            rng,
            {
                ConfortoTermico.QUENTE: prob_quente,
                ConfortoTermico.FRIO: p["prob_frio"],
                ConfortoTermico.AGRADAVEL: 1 - prob_quente - p["prob_frio"],
            },
        )

    vaga = ""
    if rng.random() < config["preenchimento.vaga_pcd"]:
        ocupada = rng.random() < config["vaga_pcd.prob_ocupada_por_lotacao"][lotacao]
        vaga = VagaPcd.OCUPADA if ocupada else VagaPcd.DISPONIVEL

    prefixo = ""
    if rng.random() < config["preenchimento.prefixo_veiculo"]:
        prefixo = f"{int(rng.integers(10000, 99999))}"

    return Relato(
        usuario=usuario,
        linha=linha,
        sentido=sentido,
        criado_em=criado_em,
        lotacao=lotacao,
        conforto_termico=conforto,
        ar_condicionado=estado_ar if rng.random() < prob_informar_ar else "",
        vaga_pcd=vaga,
        prefixo_veiculo=prefixo,
    )


def _ao_acaso(rng, choices):
    if rng.random() < 0.5:
        return ""
    return choices.values[int(rng.integers(len(choices.values)))]


def _talvez_remover(config, rng, relato, troll, agora):
    chave = "interacoes.prob_remocao_troll" if troll else "interacoes.prob_remocao_comum"
    if rng.random() < config[chave]:
        relato.removido_em = min(
            relato.criado_em + timedelta(minutes=float(rng.uniform(5, 120))), agora
        )
        relato.motivo_remocao = MOTIVO_REMOCAO


def _confirmacoes(config, rng, relatos, eh_troll, usuarios, substituidos, agora):
    """Votos de outros usuários (RN06: um por usuário, nunca no próprio relato)."""
    ids_substituidos = {r.pk for r in substituidos}
    confirmacoes = []
    for relato, troll in zip(relatos, eh_troll, strict=True):
        if relato.removido_em or relato.pk in ids_substituidos:
            continue
        quantidade = int(rng.poisson(config["interacoes.confirmacoes_por_relato"]))
        if not quantidade:
            continue
        candidatos = rng.choice(
            len(usuarios), size=min(quantidade + 1, len(usuarios)), replace=False
        )
        votantes = [usuarios[i] for i in candidatos if usuarios[i].pk != relato.usuario_id]
        prob_vale = config[
            "interacoes.prob_ainda_vale_troll" if troll else "interacoes.prob_ainda_vale"
        ]
        for votante in votantes[:quantidade]:
            criado_em = min(relato.criado_em + timedelta(minutes=float(rng.uniform(1, 30))), agora)
            confirmacoes.append(
                Confirmacao(
                    relato=relato,
                    usuario=votante,
                    ainda_vale=bool(rng.random() < prob_vale),
                    criado_em=criado_em,
                )
            )
    return confirmacoes
