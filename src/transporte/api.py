from django.db.models import Q
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from transporte.models import Linha


class LinhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Linha
        fields = (
            "id",
            "codigo",
            "nome",
            "modal",
            "operadora",
            "destino_ida",
            "destino_volta",
        )


class BuscaLinhaApi(APIView):
    def get(self, request):
        termo = request.query_params.get("q", "").strip()
        linhas = Linha.objects.filter(ativa=True)
        if termo:
            linhas = linhas.filter(Q(codigo__icontains=termo) | Q(nome__icontains=termo))
        return Response(LinhaSerializer(linhas.order_by("codigo"), many=True).data)
