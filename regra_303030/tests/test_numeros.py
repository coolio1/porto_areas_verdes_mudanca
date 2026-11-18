import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numeros  # noqa: E402


def _arv():
    return pd.DataFrame({"origem": ["lidar", "lidar", "cmp", "lidar"],
                         "mancha_m2": [30.0, 80.0, np.nan, 30.0],
                         "altura_m": [5.0, 6.0, np.nan, 3.5]})


def test_n3_variante_filtra_so_copas_lidar():
    arv = _arv()
    b = np.array([0, 0, 0, 0]); t = np.array([0, 1, 2, 3]); d = np.array([10., 20., 25., 28.])
    assert numeros.n3_variante(b, t, d, arv, 1)[0] == 4
    assert numeros.n3_variante(b, t, d, arv, 1, copa_m2=50)[0] == 2       # saem as de 30 m² (t=0 e 3)
    assert numeros.n3_variante(b, t, d, arv, 1, altura=4.0)[0] == 3       # sai a de 3,5 m
    assert numeros.n3_variante(b, t, d, arv, 1, raio3=20)[0] == 2         # a ≤ 20 m


def test_avaliar_combina_com_e():
    df = None
    n3 = np.array([3, 5, 0, 4]); copa = np.array([True, True, True, False]); d300 = np.array([True, False, True, True])
    c3, c30, c300, todos = numeros.avaliar(df, n3, copa, d300)
    assert todos.tolist() == [True, False, False, False]


def test_tabela_base_e_variantes():
    df = pd.DataFrame({"n3": [5, 5], "n30_sem_bloqueio": [6, 6], "copa400": [40., 10.], "copa500": [40., 10.], "copa600": [40., 10.],
                       "d_rede_05": [100., 100.], "d_rede_1": [100., 100.], "d_euc_05": [100., 100.], "d_euc_1": [100., 100.]})
    b = np.array([0, 0, 0, 1, 1, 1]); t = np.array([0, 1, 2, 0, 1, 2]); d = np.full(6, 10.0)
    arv = pd.DataFrame({"origem": ["cmp"] * 3, "mancha_m2": [np.nan] * 3, "altura_m": [np.nan] * 3})
    L = numeros.tabela(df, b, t, d, arv)
    base = L[0]
    assert base[1] == 100.0 and base[2] == 50.0 and base[3] == 100.0 and base[4] == 50.0
    assert len(L) == 11


def test_peso_dentro_zera_os_de_fora():
    df = pd.DataFrame({"dentro": [True, False, True]})
    assert list(numeros.peso_dentro(df)) == [1.0, 0.0, 1.0]
    assert list(numeros.peso_dentro(df, [2, 5, 3])) == [2.0, 0.0, 3.0]
    assert list(numeros.peso_dentro(pd.DataFrame({"x": [1, 2]}))) == [1.0, 1.0]       # sem coluna: todos contam
