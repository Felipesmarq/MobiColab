import csv
import io
import re
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from transporte.modais import modal_do_gtfs
from transporte.models import Linha, LinhaParada, Modal, Parada, Sentido

# No feed do Grande Recife, a maioria das paradas tem só o código como nome ("130220")
# e as nomeadas terminam com ele ("Terminal De Piedade - 010307"). Ver docs/dados/02.
_CODIGO_NO_FIM = re.compile(r"\s+-\s+\d+$")
_SO_CODIGO = re.compile(r"\d+")


def _sem_codigo_no_fim(nome):
    return _CODIGO_NO_FIM.sub("", nome).strip() or nome


def _ultimo_nome_legivel(percurso, objetos_parada):
    """Nome da última parada do percurso que não é só um código; None se não houver."""
    for stop_id in reversed(percurso):
        nome = objetos_parada[stop_id].nome
        if not _SO_CODIGO.fullmatch(nome):
            return nome
    return None


class Command(BaseCommand):
    help = "Importa linhas, paradas e itinerários de um arquivo GTFS estático (.zip)."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", type=Path, help="Arquivo ZIP do feed GTFS estático.")

    def handle(self, *args, **options):
        arquivo = options["arquivo"]
        if not arquivo.is_file() or not zipfile.is_zipfile(arquivo):
            raise CommandError(f"Arquivo GTFS ZIP não encontrado ou inválido: {arquivo}")

        with zipfile.ZipFile(arquivo) as feed:
            nomes = {Path(nome).name: nome for nome in feed.namelist()}
            obrigatorios = {"routes.txt", "stops.txt", "trips.txt", "stop_times.txt"}
            faltantes = obrigatorios - nomes.keys()
            if faltantes:
                raise CommandError(
                    f"Feed GTFS sem arquivos obrigatórios: {', '.join(sorted(faltantes))}"
                )
            tabelas = {
                nome: self._ler_csv(feed, nomes[nome])
                for nome in obrigatorios | {"agency.txt"}
                if nome in nomes
            }

        try:
            contagens = self._importar(tabelas)
        except (InvalidOperation, ValueError, IntegrityError) as erro:
            raise CommandError(
                f"Feed GTFS inválido; nenhuma alteração foi aplicada: {erro}"
            ) from erro
        self.stdout.write(
            self.style.SUCCESS(
                "Importação concluída: "
                f"{contagens['linhas']} linhas, {contagens['paradas']} paradas e "
                f"{contagens['itinerarios']} trechos de itinerário."
            )
        )

    @staticmethod
    def _ler_csv(feed, nome):
        with feed.open(nome) as arquivo:
            leitor = csv.DictReader(io.TextIOWrapper(arquivo, encoding="utf-8-sig", newline=""))
            return list(leitor)

    def _importar(self, tabelas):
        operadores = {
            agencia.get("agency_id", ""): agencia.get("agency_name", "")
            for agencia in tabelas.get("agency.txt", [])
        }
        paradas_gtfs = {}
        for linha in tabelas["stops.txt"]:
            stop_id = linha.get("stop_id", "").strip()
            nome = linha.get("stop_name", "").strip()
            if not stop_id or not nome:
                continue
            try:
                lat = Decimal(linha.get("stop_lat", ""))
                lon = Decimal(linha.get("stop_lon", ""))
            except InvalidOperation:
                continue
            if not lat.is_finite() or not lon.is_finite():
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180) or len(stop_id) > 64:
                continue
            paradas_gtfs[stop_id] = {
                "nome": _sem_codigo_no_fim(nome)[:160],
                "lat": lat.quantize(Decimal("0.000001")),
                "lon": lon.quantize(Decimal("0.000001")),
                "eh_terminal": linha.get("location_type") == "1"
                or bool(re.search(r"\b(ti|terminal)\b", nome, re.IGNORECASE)),
            }

        viagens = {}
        for viagem in tabelas["trips.txt"]:
            trip_id = viagem.get("trip_id", "").strip()
            route_id = viagem.get("route_id", "").strip()
            direction_id = viagem.get("direction_id", "0").strip() or "0"
            if trip_id and route_id:
                viagens[trip_id] = (route_id, direction_id)

        horarios = defaultdict(list)
        for horario in tabelas["stop_times.txt"]:
            trip_id = horario.get("trip_id", "").strip()
            if trip_id not in viagens:
                continue
            try:
                sequencia = int(horario.get("stop_sequence", ""))
            except ValueError:
                continue
            horarios[trip_id].append((sequencia, horario.get("stop_id", "").strip()))
        for percurso in horarios.values():
            percurso.sort()

        melhores_viagens = {}
        for trip_id, (route_id, direction_id) in viagens.items():
            if direction_id not in ("0", "1") or not horarios.get(trip_id):
                continue
            chave = (route_id, direction_id)
            percurso = horarios[trip_id]
            atual = melhores_viagens.get(chave)
            if atual is None or (len(percurso), trip_id) > (len(atual[0]), atual[1]):
                melhores_viagens[chave] = (percurso, trip_id)

        rotas = {}
        for rota in tabelas["routes.txt"]:
            route_id = rota.get("route_id", "").strip()
            if route_id:
                rotas[route_id] = rota

        with transaction.atomic():
            objetos_parada = {}
            for stop_id, campos in paradas_gtfs.items():
                parada, _ = Parada.objects.update_or_create(gtfs_stop_id=stop_id, defaults=campos)
                objetos_parada[stop_id] = parada

            linhas_importadas = 0
            trechos_importados = 0
            for route_id, rota in rotas.items():
                try:
                    route_type = int(rota.get("route_type", ""))
                except ValueError:
                    continue
                modal = modal_do_gtfs(route_type)
                codigo = (rota.get("route_short_name") or route_id).strip()
                nome = (
                    rota.get("route_long_name") or rota.get("route_short_name") or codigo
                ).strip()
                if not modal or not codigo or not nome:
                    continue
                if re.search(r"\bbrt\b", f"{codigo} {nome}", re.IGNORECASE):
                    modal = Modal.BRT
                if len(codigo) > 20 or len(route_id) > 64:
                    raise ValueError(f"Identificador da linha excede o limite: {route_id}")

                destinos = {}
                percursos = {}
                for direction_id, sentido in (("0", Sentido.IDA), ("1", Sentido.VOLTA)):
                    escolhido = melhores_viagens.get((route_id, direction_id))
                    if not escolhido:
                        continue
                    percurso = [stop_id for _, stop_id in escolhido[0] if stop_id in objetos_parada]
                    if not percurso:
                        continue
                    destinos[sentido] = _ultimo_nome_legivel(percurso, objetos_parada) or nome
                    percursos[sentido] = percurso

                destino_ida = destinos.get(Sentido.IDA) or nome[:120]
                destino_volta = destinos.get(Sentido.VOLTA, "")[:120]
                agencia_id = rota.get("agency_id", "")
                operadora = operadores.get(agencia_id, "")
                if not agencia_id and len(operadores) == 1:
                    operadora = next(iter(operadores.values()))
                defaults = {
                    "codigo": codigo,
                    "nome": nome[:120],
                    "modal": modal,
                    "operadora": operadora[:120],
                    "destino_ida": destino_ida[:120],
                    "destino_volta": destino_volta,
                    "ativa": True,
                }
                linha = Linha.objects.filter(gtfs_route_id=route_id).first()
                if linha is None:
                    linha = Linha.objects.filter(codigo=codigo).first()
                    if linha and linha.gtfs_route_id:
                        raise ValueError(
                            f"O código {codigo} já está vinculado ao GTFS {linha.gtfs_route_id}"
                        )
                if linha is None:
                    linha = Linha(gtfs_route_id=route_id, **defaults)
                else:
                    linha.gtfs_route_id = route_id
                    for campo, valor in defaults.items():
                        setattr(linha, campo, valor)
                linha.save()
                linhas_importadas += 1

                LinhaParada.objects.filter(linha=linha).delete()
                for sentido, percurso in percursos.items():
                    vistos = set()
                    ordem = 0
                    for stop_id in percurso:
                        if stop_id in vistos:
                            continue
                        vistos.add(stop_id)
                        ordem += 1
                        LinhaParada.objects.create(
                            linha=linha,
                            parada=objetos_parada[stop_id],
                            sentido=sentido,
                            ordem=ordem,
                        )
                        trechos_importados += 1

        return {
            "linhas": linhas_importadas,
            "paradas": len(objetos_parada),
            "itinerarios": trechos_importados,
        }
