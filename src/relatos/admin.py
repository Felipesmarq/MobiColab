from django.contrib import admin
from django.db.models import Count, Q

from .models import Confirmacao, Relato


class ConfirmacaoInline(admin.TabularInline):
    model = Confirmacao
    extra = 0
    fields = ("usuario", "ainda_vale", "criado_em")
    readonly_fields = fields
    can_delete = False


class RemovidoFilter(admin.SimpleListFilter):
    title = "removido"
    parameter_name = "removido"

    def lookups(self, request, model_admin):
        return (("sim", "Sim"), ("nao", "Não"))

    def queryset(self, request, queryset):
        if self.value() == "sim":
            return queryset.filter(removido_em__isnull=False)
        if self.value() == "nao":
            return queryset.filter(removido_em__isnull=True)
        return queryset


@admin.register(Relato)
class RelatoAdmin(admin.ModelAdmin):
    """Esboço da fila de revisão do RF07: ordene por contestações para ver os suspeitos.

    A fila completa (com `LIMIAR_CONTESTACAO` e a ação de remover) é tarefa da fase 2.
    """

    list_display = (
        "criado_em",
        "linha",
        "sentido",
        "lotacao",
        "ar_condicionado",
        "usuario",
        "contestacoes",
        "removido",
    )
    list_filter = ("sentido", "lotacao", "ar_condicionado", "linha__modal", RemovidoFilter)
    search_fields = ("linha__codigo", "linha__nome", "usuario__email", "prefixo_veiculo")
    date_hierarchy = "criado_em"
    autocomplete_fields = ["linha"]
    raw_id_fields = ("usuario", "substituido_por", "removido_por")
    inlines = [ConfirmacaoInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("linha", "usuario")
            .annotate(_contestacoes=Count("confirmacoes", filter=Q(confirmacoes__ainda_vale=False)))
        )

    @admin.display(description="contestações", ordering="_contestacoes")
    def contestacoes(self, obj):
        return obj._contestacoes

    @admin.display(boolean=True)
    def removido(self, obj):
        return obj.removido


@admin.register(Confirmacao)
class ConfirmacaoAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "relato", "usuario", "ainda_vale")
    list_filter = ("ainda_vale",)
    raw_id_fields = ("relato", "usuario")
