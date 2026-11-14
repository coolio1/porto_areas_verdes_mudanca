"""Leitura e limpeza dos CSV da recolha de autocarros STCP."""
from pathlib import Path

import numpy as np
import pandas as pd

from . import geo

PERIODOS: dict[str, tuple[int, int]] = {"dia": (6, 21), "am": (7, 9), "pm": (17, 19)}
ATRASO_MAX_S = 300
KMH_MAX = 90.0


COLUNAS = ["obs", "veiculo", "lon", "lat", "kmh", "direccao", "linha", "viagem", "dia", "hora", "tipo_dia", "derivada"]
CADENCIA_MIN_S, CADENCIA_MAX_S = 30.0, 150.0     # intervalo entre leituras que dá uma velocidade derivada fiável
PARADO_M = 5.0                                    # deslocamento abaixo disto: sem rumo novo (mantém o anterior)


def _marcar_dia(df: pd.DataFrame) -> pd.DataFrame:
    local = df.obs.dt.tz_convert("Europe/Lisbon")
    df["dia"] = local.dt.date
    df["hora"] = local.dt.hour
    df["tipo_dia"] = ["fds" if d >= 5 else "util" for d in local.dt.day_of_week]
    return df


def carregar_stcp(pasta: Path) -> pd.DataFrame:
    """Lê `AAAA-MM-DD.csv` do pacote de posições da STCP (sem velocidade nem rumo) e deriva ambos das posições.

    `kmh` = distância em linha recta ÷ tempo entre duas leituras seguidas do mesmo veículo (30–150 s); `direccao` = rumo
    desse deslocamento (mantém o último rumo se o autocarro quase não se mexeu). A primeira leitura de cada veículo e
    as que seguem um intervalo fora dessa janela ficam de fora: nunca se inventa uma velocidade. `derivada` = True.
    """
    ficheiros = sorted(Path(pasta).glob("????-??-??.csv"))        # só as posições diárias (a pasta tem também horários e passagens)
    if not ficheiros:
        return pd.DataFrame(columns=COLUNAS)
    p = pd.concat([pd.read_csv(f, dtype=str) for f in ficheiros], ignore_index=True)
    p["obs"] = pd.to_datetime(p.observed_at, utc=True)
    atraso = (pd.to_datetime(p.received_at, utc=True) - p.obs).dt.total_seconds()
    p = p[(atraso >= 0) & (atraso <= ATRASO_MAX_S)].copy()
    p["lon"], p["lat"] = p.longitude.astype(float), p.latitude.astype(float)
    p = p.drop_duplicates(["vehicle_id", "obs"]).sort_values(["vehicle_id", "obs"])
    g = p.groupby("vehicle_id")
    dt = g.obs.diff().dt.total_seconds()
    dx, dy = g.lon.diff() * geo.KX, g.lat.diff() * geo.KY
    d = np.hypot(dx, dy)
    p["kmh"] = np.where((dt >= CADENCIA_MIN_S) & (dt <= CADENCIA_MAX_S), d / dt * 3.6, np.nan)
    rumo = (np.degrees(np.arctan2(dx, dy)) % 360).where(d >= PARADO_M)
    p["direccao"] = rumo.groupby(p.vehicle_id).ffill()
    p = p[p.kmh.notna() & (p.kmh <= KMH_MAX) & p.direccao.notna()].copy()
    p = p.rename(columns={"vehicle_id": "veiculo", "route_id": "linha", "trip_id": "viagem"})
    p["derivada"] = True
    return _marcar_dia(p)[COLUNAS].reset_index(drop=True)


def carregar(pasta: Path, pasta_stcp: Path | None = None) -> pd.DataFrame:
    """Lê `posicoes_*.csv[.gz]` (recolha própria, com velocidade medida), limpa e acrescenta `dia`, `hora` (locais) e `tipo_dia`.

    Com `pasta_stcp`, junta os dias do pacote da STCP que a recolha própria não tem (velocidade derivada, `derivada` = True).
    Nos dias que existem nas duas fontes vale sempre a recolha própria: tem a velocidade medida e quase todas as posições do
    pacote já lá estão (mesmos veículos e instantes).
    """
    partes = [pd.read_csv(f, dtype={"linha": str, "viagem": str, "veiculo": str})
              for f in sorted(Path(pasta).glob("posicoes_*.csv*"))]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates(["veiculo", "observado_utc"])
    df["obs"] = pd.to_datetime(df.observado_utc, utc=True)
    atraso = (pd.to_datetime(df.recebido_utc, utc=True) - df.obs).dt.total_seconds()
    df["kmh"] = df.velocidade * 3.6
    df = df[(atraso >= 0) & (atraso <= ATRASO_MAX_S) & (df.kmh <= KMH_MAX)].copy()
    df["derivada"] = False
    df = _marcar_dia(df)[COLUNAS].reset_index(drop=True)
    if pasta_stcp is not None and Path(pasta_stcp).is_dir():
        novo = carregar_stcp(pasta_stcp)
        novo = novo[~novo.dia.isin(set(df.dia))]
        df = pd.concat([df, novo], ignore_index=True)
    return df


def dias_com_dados(df: pd.DataFrame, periodo: str, tipo_dia: str) -> int:
    """Nº de dias distintos com leituras nesse período e tipo de dia."""
    h0, h1 = PERIODOS[periodo]
    x = df[(df.tipo_dia == tipo_dia) & df.hora.between(h0, h1)]
    return int(x.dia.nunique())
