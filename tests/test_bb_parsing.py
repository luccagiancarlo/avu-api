from datetime import date
from decimal import Decimal

from app.bb.parsing import extrair_pagamento, parse_horario_pix


def test_parse_horario_iso_com_timezone():
    dt = parse_horario_pix("2026-06-25T13:30:00.000-03:00")
    assert dt.year == 2026 and dt.month == 6 and dt.day == 25
    assert dt.hour == 13 and dt.minute == 30


def test_parse_horario_iso_sem_milissegundos():
    dt = parse_horario_pix("2026-06-25T13:30:00-03:00")
    assert dt.hour == 13


def test_extrair_pagamento_feliz():
    cobranca = {
        "status": "CONCLUIDA",
        "pix": [{"horario": "2026-06-25T13:30:00.000-03:00", "valor": "120.00", "txid": "x"}],
    }
    result = extrair_pagamento(cobranca)
    assert result == (date(2026, 6, 25), Decimal("120.00"))


def test_extrair_pagamento_sem_pix():
    assert extrair_pagamento({"status": "CONCLUIDA", "pix": []}) is None
    assert extrair_pagamento({"status": "CONCLUIDA"}) is None


def test_extrair_pagamento_payload_malformado():
    assert extrair_pagamento({"pix": [{"horario": "nao-eh-data"}]}) is None
    assert extrair_pagamento({"pix": [{"valor": "10"}]}) is None  # sem horario
    assert extrair_pagamento({"pix": [{"horario": "2026-06-25T13:30:00-03:00", "valor": "abc"}]}) is None
