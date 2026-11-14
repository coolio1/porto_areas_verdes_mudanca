"""Velocidade média «habitual» da rede por hora, para comparar com a vista «Agora» (tempo real)."""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from . import geo

RAIO_ESPERA_M = 40.0
RAIO_TERMINAL_M = 100.0
PARADO_KMH = 2.0
MIN_LEITURAS_HORA = 500


def terminais(df: pd.DataFrame, celula_m: float = 80.0, min_pontas: int = 10) -> list[list[float]]:
    """Centros (lat, lon) das células com ≥ `min_pontas` inícios/fins de viagem: terminais e pontos de regulação."""
    g = df.groupby(["veiculo", "viagem", "dia"])
    pontas = pd.concat([g.head(1), g.tail(1)])
    xy = geo.xy(pontas.lon, pontas.lat)
    cel = pd.DataFrame({"a": (xy[:, 0] // celula_m).astype(int), "b": (xy[:, 1] // celula_m).astype(int),
                        "lon": pontas.lon.to_numpy(), "lat": pontas.lat.to_numpy()})
    c = cel.groupby(["a", "b"]).agg(n=("lon", "size"), lon=("lon", "mean"), lat=("lat", "mean"))
    c = c[c.n >= min_pontas]
    return [[round(float(la), 5), round(float(lo), 5)] for la, lo in zip(c.lat, c.lon)]


def por_hora(df: pd.DataFrame, paragens: pd.DataFrame, hoje=None, min_leituras: int = MIN_LEITURAS_HORA) -> dict:
    """Média de `kmh` por hora local (0–23) nos dias úteis anteriores a `hoje`, sem esperas, + paragens e terminais para a página.

    Espera = ≤ 2 km/h a < 40 m de uma paragem ou a < 100 m de um terminal; é a mesma regra que a página aplica às
    posições ao vivo, para que «agora» e «habitual» sejam comparáveis. Horas com menos de `min_leituras` ficam `None`.
    """
    hoje = hoje or pd.Timestamp.now(tz="Europe/Lisbon").date()
    pos = geo.xy(df.lon, df.lat)
    d = cKDTree(geo.xy(paragens.lon, paragens.lat)).query(pos)[0]
    term = terminais(df)
    dt = cKDTree(geo.xy(*np.array([[o, a] for a, o in term]).T)).query(pos)[0] if term else np.full(len(df), np.inf)
    x = df[~((df.kmh <= PARADO_KMH) & ((d < RAIO_ESPERA_M) | (dt < RAIO_TERMINAL_M)))]
    util = x[(x.tipo_dia == "util") & (x.dia < hoje)]
    g = util.groupby("hora").kmh.agg(["mean", "size"])
    horas = [round(float(g.loc[h, "mean"]), 1) if h in g.index and g.loc[h, "size"] >= min_leituras else None for h in range(24)]
    return {"horas": horas, "dias": int(util.dia.nunique()), "terminais": term,
            "paragens": [[round(float(a), 5), round(float(o), 5)] for a, o in zip(paragens.lat, paragens.lon)]}
