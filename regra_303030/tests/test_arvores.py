import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arvores  # noqa: E402


def _copa(ndsm):
    return np.isfinite(ndsm) & (ndsm >= 3.0)


def _cone(n, centro, raio, h):
    y, x = np.ogrid[:n, :n]
    d = np.hypot(y - centro[0], x - centro[1])
    return np.where(d < raio, h * (1 - d / raio) + 3.0, 0.0)


def test_duas_copas_separadas_dao_dois_picos():
    nd = np.zeros((120, 120), "float32")
    nd += _cone(120, (30, 30), 15, 8)      # raio 7,5 m, área ~177 m²
    nd += _cone(120, (90, 90), 15, 6)
    r, c, h, a = arvores.picos(nd, _copa(nd))
    assert len(r) == 2
    assert a.min() >= arvores.MIN_COPA_M2


def test_mancha_pequena_e_ruido():
    nd = np.zeros((60, 60), "float32")
    nd[10:14, 10:14] = 5.0                 # 16 px = 4 m² < 25 m²
    assert len(arvores.picos(nd, _copa(nd))[0]) == 0


def test_sem_copa():
    nd = np.zeros((20, 20), "float32")
    assert len(arvores.picos(nd, _copa(nd))[0]) == 0


def test_deduplicar_prefere_cmp():
    lidar = [(0.0, 0.0), (10.0, 0.0), (50.0, 50.0)]
    cmp_ = [(1.0, 0.0), (49.0, 50.0)]       # a 1 m do 1.º e a 1 m do 3.º
    assert list(arvores.deduplicar(lidar, cmp_)) == [False, True, False]


def test_deduplicar_sem_cmp():
    assert list(arvores.deduplicar([(0, 0)], [])) == [True]


def test_grua_acima_de_45_m_nao_e_arvore():
    nd = np.zeros((120, 120), "float32")
    nd += _cone(120, (60, 60), 15, 60)     # pico ~63 m
    assert len(arvores.picos(nd, _copa(nd))[0]) == 0
