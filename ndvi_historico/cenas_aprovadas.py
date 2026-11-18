"""Controlo de qualidade por cena e recta de ponte L8 -> L7, a partir de layers_historico/controlo_cenas.csv.

O CSV vem de controlo_cenas.py (NDVI de cada cena nos alvos estáveis: construído 1979∩2024 e árvores 1979∩2024).
- Cena aprovada: NDVI no construído a ≤ 3 desvios robustos (MAD) da mediana do seu sensor e, se medido, NDVI nas
  árvores a ≤ 3,5 desvios robustos; sem valor no construído (tudo mascarado) = rejeitada.
- Recta L8 -> L7: dois alvos (construído e árvores), medianas das cenas aprovadas em 2013-2021, anos em que L7 e L8
  operam juntos: NDVI7 = IC + SL * NDVI8. Substitui o desvio aditivo fixo (o desvio de sensor cresce com o NDVI).
"""
import os

import numpy as np
import pandas as pd

CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'layers_historico', 'controlo_cenas.csv')


def _z(g, c):
    m = g[c].median()
    mad = (g[c] - m).abs().median() * 1.4826
    return (g[c] - m) / mad


def carregar():
    d = pd.read_csv(CSV).drop_duplicates('id')
    d['ano'] = d['data'].str[:4].astype(int)
    d['zc'] = d.groupby('sensor', group_keys=False).apply(lambda g: _z(g, 'construido'))
    d['za'] = d.groupby('sensor', group_keys=False).apply(lambda g: _z(g, 'arvores'))
    d['ok'] = d['construido'].notna() & (d['zc'].abs() <= 3) & (d['za'].abs().le(3.5) | d['za'].isna())
    return d


def aprovadas(d=None):
    d = carregar() if d is None else d
    return d.loc[d.ok, 'id'].tolist()


def recta_l8_l7(d=None):
    """(IC, SL) com NDVI7 = IC + SL * NDVI8, pelas medianas dos dois alvos na sobreposição 2013-2021."""
    d = carregar() if d is None else d
    ov = d[d.ok & d.ano.between(2013, 2021)]
    a = ov.groupby('sensor')[['construido', 'arvores']].median()
    b7, t7 = a.loc['L7']
    b8, t8 = a.loc['L8']
    sl = (t7 - b7) / (t8 - b8)
    return float(b7 - sl * b8), float(sl)


if __name__ == '__main__':
    d = carregar()
    ic, sl = recta_l8_l7(d)
    print(f'{d.ok.sum()} cenas aprovadas de {len(d)}; NDVI7 = {ic:.4f} + {sl:.4f} * NDVI8')
