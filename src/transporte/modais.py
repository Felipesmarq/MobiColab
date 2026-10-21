"""Mapeamento entre o GTFS e os modais do MobiColab (ADR 0016).

É o único lugar que traduz `route_type` do GTFS para `Modal`. O GTFS não tem
um tipo próprio para BRT; a importação (fase 1) identifica BRT pelos dados da
linha e usa este mapeamento só como padrão.
"""

from .models import Modal

ROUTE_TYPE_PARA_MODAL = {
    1: Modal.METRO,  # subway / metro
    2: Modal.METRO,  # rail (trens urbanos da CBTU)
    3: Modal.ONIBUS,  # bus
}


def modal_do_gtfs(route_type):
    """Devolve o `Modal` de um `route_type` do GTFS, ou None se não for atendido."""
    return ROUTE_TYPE_PARA_MODAL.get(int(route_type))
