import datetime

import pandas as pd

from velocidade import habitual

LON0, LAT0 = -8.6, 41.15
PARAGENS = pd.DataFrame({"lon": [LON0], "lat": [LAT0]})


def leituras(linhas):
    """linhas: (dia, hora, tipo_dia, kmh, lon, lat)."""
    df = pd.DataFrame(linhas, columns=["dia", "hora", "tipo_dia", "kmh", "lon", "lat"])
    df["veiculo"] = [f"v{i}" for i in range(len(df))]         # cada leitura é uma viagem à parte, só para o cálculo dos terminais
    df["viagem"] = "x"
    return df


LONGE = LON0 + 0.01      # ~ 840 m da paragem
D1, D2, HOJE = datetime.date(2026, 11, 9), datetime.date(2026, 11, 10), datetime.date(2026, 11, 13)


def test_media_por_hora_so_de_dias_uteis_anteriores_a_hoje():
    df = leituras([(D1, 17, "util", 10.0, LONGE, LAT0), (D2, 17, "util", 20.0, LONGE, LAT0),
                   (HOJE, 17, "util", 90.0, LONGE, LAT0),          # hoje não entra no habitual
                   (D1, 17, "fds", 50.0, LONGE, LAT0)])            # fim-de-semana também não
    r = habitual.por_hora(df, PARAGENS, hoje=HOJE, min_leituras=1)
    assert r["horas"][17] == 15.0 and r["dias"] == 2


def test_esperas_junto_a_paragens_saem_mas_o_transito_parado_longe_conta():
    df = leituras([(D1, 8, "util", 0.0, LON0, LAT0),               # parado numa paragem: espera
                   (D1, 8, "util", 0.0, LONGE, LAT0),              # parado no meio da rua: trânsito
                   (D1, 8, "util", 12.0, LONGE, LAT0)])
    assert habitual.por_hora(df, PARAGENS, hoje=HOJE, min_leituras=1)["horas"][8] == 6.0      # (0 + 12) / 2: a espera da paragem não conta


def test_horas_com_poucas_leituras_ficam_sem_habitual():
    df = leituras([(D1, 9, "util", 10.0, LONGE, LAT0)])
    assert habitual.por_hora(df, PARAGENS, hoje=HOJE, min_leituras=2)["horas"][9] is None
