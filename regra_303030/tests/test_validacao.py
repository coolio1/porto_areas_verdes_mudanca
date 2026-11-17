import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validacao  # noqa: E402


def _df(n=1000, semente=1):
    r = np.random.default_rng(semente)
    c3, c30, c300 = (r.random(n) < 0.5 for _ in range(3))
    return pd.DataFrame({"c3": c3, "c30": c30, "c300": c300, "todos": c3 & c30 & c300, "nenhum": ~(c3 | c30 | c300)})


def test_amostra_sem_repeticoes_e_reprodutivel():
    df = _df()
    a = validacao.amostrar(df, por_estrato=20)
    assert a == validacao.amostrar(df, por_estrato=20)
    idx = [i for i, _ in a]
    assert len(idx) == len(set(idx))


def test_cada_ponto_pertence_ao_seu_estrato():
    df = _df()
    for i, e in validacao.amostrar(df, por_estrato=20):
        r = df.iloc[i]
        if e == "todos":
            assert r.todos
        elif e == "nenhum":
            assert r.nenhum
        elif e == "so_3":
            assert r.c3 and not r.c30 and not r.c300


def test_estrato_pequeno_leva_todos():
    df = _df(30)
    df["todos"] = False
    df.loc[0, ["c3", "c30", "c300", "todos"]] = True
    a = validacao.amostrar(df, por_estrato=20)
    assert sum(1 for _, e in a if e == "todos") == 1
