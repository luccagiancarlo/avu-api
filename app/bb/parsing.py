"""Helpers de parse das respostas do BB.

O BB devolve datas ISO-8601 com timezone (`2026-06-25T13:30:00.000-03:00`).
Python 3.11+ aceita esse formato em `datetime.fromisoformat`. Mantemos o
helper isolado para tratar variações observadas em homologação (sem `.000`,
sem timezone) sem espalhar try/except.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def parse_horario_pix(horario: str) -> datetime:
    """Converte string ISO-8601 do BB para datetime."""
    return datetime.fromisoformat(horario)


def extrair_pagamento(cobranca: dict) -> tuple[date, Decimal] | None:
    """Retorna (data_do_pagamento, valor_pago) do payload BB ou None se não há pix registrado.

    Espera-se que o caller só chame quando `status == "CONCLUIDA"`. Se a estrutura
    vier inesperada (BB mudou contrato), retorna None — o caller decide fallback.
    """
    pix_list = cobranca.get("pix") or []
    if not pix_list:
        return None

    primeiro = pix_list[0]
    horario_raw = primeiro.get("horario")
    valor_raw = primeiro.get("valor")
    if not horario_raw or not valor_raw:
        return None

    try:
        dt_pag = parse_horario_pix(horario_raw).date()
        vl_pago = Decimal(str(valor_raw))
    except (ValueError, InvalidOperation):
        return None

    return dt_pag, vl_pago
