from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from relatos.models import (
    ArCondicionado,
    ConfortoTermico,
    Lotacao,
    Relato,
    VagaPcd,
)
from relatos.regras import (
    RelatoInvalido,
    UsuarioBloqueado,
    UsuarioNaoAutenticado,
    confirmar_relato,
    registrar_relato,
    status_linha,
)
from transporte.models import Linha, Sentido


class EnvioRelatoSerializer(serializers.Serializer):
    linha = serializers.PrimaryKeyRelatedField(queryset=Linha.objects.filter(ativa=True))
    sentido = serializers.ChoiceField(choices=Sentido.choices)
    lotacao = serializers.ChoiceField(choices=Lotacao.choices)
    conforto_termico = serializers.ChoiceField(
        choices=ConfortoTermico.choices, required=False, allow_blank=True
    )
    ar_condicionado = serializers.ChoiceField(
        choices=ArCondicionado.choices, required=False, allow_blank=True
    )
    vaga_pcd = serializers.ChoiceField(choices=VagaPcd.choices, required=False, allow_blank=True)
    prefixo_veiculo = serializers.CharField(max_length=20, required=False, allow_blank=True)


class ConfirmacaoSerializer(serializers.Serializer):
    ainda_vale = serializers.BooleanField()


def _resposta_erro_regra(erro):
    return Response(erro.args[0], status=status.HTTP_400_BAD_REQUEST)


def _resposta_autenticacao(usuario):
    if not usuario.is_authenticated:
        return Response({"detail": "Autenticação necessária."}, status=status.HTTP_401_UNAUTHORIZED)
    if not usuario.is_active:
        return Response({"detail": "Conta bloqueada."}, status=status.HTTP_403_FORBIDDEN)
    return None


class StatusLinhaApi(APIView):
    def get(self, request, pk):
        linha = get_object_or_404(Linha, pk=pk, ativa=True)
        sentido = request.query_params.get("sentido", Sentido.IDA)
        try:
            dimensoes = status_linha(linha, sentido)
        except RelatoInvalido as erro:
            return _resposta_erro_regra(erro)
        return Response({"linha": linha.pk, "sentido": sentido, "dimensoes": dimensoes})


class EnvioRelatoApi(APIView):
    def post(self, request):
        erro_autenticacao = _resposta_autenticacao(request.user)
        if erro_autenticacao:
            return erro_autenticacao
        serializer = EnvioRelatoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        dados = serializer.validated_data.copy()
        linha = dados.pop("linha")
        try:
            relato = registrar_relato(request.user, linha, **dados)
        except RelatoInvalido as erro:
            return _resposta_erro_regra(erro)
        except UsuarioNaoAutenticado:
            return Response(
                {"detail": "Autenticação necessária."}, status=status.HTTP_401_UNAUTHORIZED
            )
        except UsuarioBloqueado:
            return Response({"detail": "Conta bloqueada."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            {
                "id": relato.pk,
                "criado_em": relato.criado_em,
                "substituiu": relato.substituiu.exists(),
            },
            status=status.HTTP_201_CREATED,
        )


class ConfirmacaoApi(APIView):
    def post(self, request, pk):
        erro_autenticacao = _resposta_autenticacao(request.user)
        if erro_autenticacao:
            return erro_autenticacao
        serializer = ConfirmacaoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        relato = get_object_or_404(Relato, pk=pk)
        try:
            confirmacao = confirmar_relato(
                request.user, relato, serializer.validated_data["ainda_vale"]
            )
        except RelatoInvalido as erro:
            return _resposta_erro_regra(erro)
        except UsuarioNaoAutenticado:
            return Response(
                {"detail": "Autenticação necessária."}, status=status.HTTP_401_UNAUTHORIZED
            )
        except UsuarioBloqueado:
            return Response({"detail": "Conta bloqueada."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            {"id": confirmacao.pk, "ainda_vale": confirmacao.ainda_vale},
            status=status.HTTP_201_CREATED,
        )
