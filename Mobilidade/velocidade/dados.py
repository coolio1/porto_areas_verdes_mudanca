"""Leitura e limpeza dos CSV da recolha de autocarros STCP."""
from pathlib import Path

import pandas as pd

PERIODOS: dict[str, tuple[int, int]] = {"dia": (6, 21), "am": (7, 9), "pm": (17, 19)}
ATRASO_MAX_S = 300
KMH_MAX = 90.0


def carregar(pasta: Path) -> pd.DataFrame:
    """Lê `posicoes_*.csv[.gz]`, limpa e acrescenta `dia`, `hora` (locais) e `tipo_dia` ('util'|'fds')."""
    partes = [pd.read_csv(f, dtype={"linha": str, "viagem": str, "veiculo": str})
              for f in sorted(Path(pasta).glob("posicoes_*.csv*"))]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates(["veiculo", "observado_utc"])
    df["obs"] = pd.to_datetime(df.observado_utc, utc=True)
    atraso = (pd.to_datetime(df.recebido_utc, utc=True) - df.obs).dt.total_seconds()
    df["kmh"] = df.velocidade * 3.6
    df = df[(atraso >= 0) & (atraso <= ATRASO_MAX_S) & (df.kmh <= KMH_MAX)].copy()
    local = df.obs.dt.tz_convert("Europe/Lisbon")
    df["dia"] = local.dt.date
    df["hora"] = local.dt.hour
    df["tipo_dia"] = ["fds" if d >= 5 else "util" for d in local.dt.day_of_week]
    cols = ["obs", "veiculo", "lon", "lat", "kmh", "direccao", "linha", "viagem", "dia", "hora", "tipo_dia"]
    return df[cols].reset_index(drop=True)


def dias_com_dados(df: pd.DataFrame, periodo: str, tipo_dia: str) -> int:
    """Nº de dias distintos com leituras nesse período e tipo de dia."""
    h0, h1 = PERIODOS[periodo]
    x = df[(df.tipo_dia == tipo_dia) & df.hora.between(h0, h1)]
    return int(x.dia.nunique())
