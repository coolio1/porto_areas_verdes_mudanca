"""Separar esperas (paragens, terminais, garagens) de lentidão por trânsito.

Regra do spec: um zero junto a uma paragem só é espera se o trânsito à volta não estiver também lento;
sem vizinhos suficientes para testar conta como espera. Zeros fora de paragens nunca se descartam.
"""
import math

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from . import geo

PARADO_KMH = 2.0
RAIO_VIZINHOS_M = 300.0
JANELA_S = 180.0
MIN_VIZINHOS = 2
LENTO_KMH = 8.0
_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def _segundos(obs: pd.Series) -> np.ndarray:
    return (obs - _EPOCH).dt.total_seconds().to_numpy()


def marcar_esperas(df: pd.DataFrame, paragens: pd.DataFrame, raio_m: float = 40.0) -> pd.Series:
    """True nas leituras que são espera: ≤ 2 km/h a < `raio_m` de uma paragem, sem trânsito lento à volta."""
    p = geo.xy(df.lon, df.lat)
    perto = cKDTree(geo.xy(paragens.lon, paragens.lat)).query(p)[0] < raio_m
    t = _segundos(df.obs)
    kmh = df.kmh.to_numpy()
    veic = df.veiculo.to_numpy()
    fora = np.where(~perto)[0]
    # eixo do tempo em metros (1 s = 1,67 m) só para a procura; o filtro final é exacto (300 m e ± 180 s)
    esc = RAIO_VIZINHOS_M / JANELA_S
    arvore = cKDTree(np.c_[p[fora], t[fora] * esc])
    espera = perto & (kmh <= PARADO_KMH)
    for i in np.where(espera)[0]:
        cand = fora[arvore.query_ball_point([p[i, 0], p[i, 1], t[i] * esc], RAIO_VIZINHOS_M * math.sqrt(2))]
        cand = cand[(veic[cand] != veic[i]) & (np.abs(t[cand] - t[i]) <= JANELA_S)
                    & (np.hypot(*(p[cand] - p[i]).T) < RAIO_VIZINHOS_M)]
        if len(cand) >= MIN_VIZINHOS and np.median(kmh[cand]) < LENTO_KMH:
            espera[i] = False
    return pd.Series(espera, index=df.index)


def marcar_paradas_longas(df: pd.DataFrame, min_leituras: int = 15, raio_m: float = 15.0) -> pd.Series:
    """True em sequências de ≥ `min_leituras` leituras seguidas do mesmo veículo a < `raio_m` da primeira."""
    ordem = df.sort_values(["veiculo", "obs"])
    p = geo.xy(ordem.lon, ordem.lat).tolist()
    veic = ordem.veiculo.tolist()
    flags = np.zeros(len(ordem), bool)
    i, n = 0, len(ordem)
    while i < n:
        j = i + 1
        while j < n and veic[j] == veic[i] and math.hypot(p[j][0] - p[i][0], p[j][1] - p[i][1]) < raio_m:
            j += 1
        if j - i >= min_leituras:
            flags[i:j] = True
        i = j
    return pd.Series(flags, index=ordem.index).reindex(df.index)
