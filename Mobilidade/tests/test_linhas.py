import numpy as np
import pandas as pd

from velocidade import geo, linhas
from velocidade.osm import Rota, Via

LON0, LAT0 = -8.6, 41.15


def pt(x, y):
    return (LON0 + x / geo.KX, LAT0 + y / geo.KY)


def via(way_id, nome, p0, p1, n=7):
    """Via recta de p0 a p1 (metros), n pontos, com ids de nós `way_id*100+k`."""
    xs = np.linspace(p0[0], p1[0], n); ys = np.linspace(p0[1], p1[1], n)
    return Via(way_id, nome, np.array([pt(x, y) for x, y in zip(xs, ys)]), [way_id * 100 + k for k in range(n)])


# W1: 650 m para leste (linha A); W2: 100 m a norte, só da linha B; W3: sentido oposto de W1, 8 m a norte (linha A)
W1 = via(11, "Rua X", (0, 0), (650, 0))
W2 = via(12, "Rua Y", (0, 100), (650, 100))
W3 = via(13, "Rua Z", (650, 8), (0, 8))
ROTAS = [Rota(1, "A", [W1]), Rota(2, "B", [W2])]


def leituras(*rows):
    """rows: (linha, x, y, kmh, direccao)"""
    return pd.DataFrame({
        "linha": [r[0] for r in rows],
        "lon": [pt(r[1], r[2])[0] for r in rows],
        "lat": [pt(r[1], r[2])[1] for r in rows],
        "kmh": [float(r[3]) for r in rows],
        "direccao": [r[4] for r in rows],
    })


def test_divide_em_trocos_de_cerca_de_200m():
    t = linhas.dividir(ROTAS)
    t1 = t[t.way_id == 11]
    assert list(t1.index) == ["11:0", "11:1", "11:2"]
    assert all(150 <= c <= 300 for c in t1.comprimento_m)
    assert abs(t1.comprimento_m.sum() - 650) < 1
    assert t1.refs.iloc[0] == frozenset({"A"}) and t1.nome.iloc[0] == "Rua X"
    assert len(t1.latlon.iloc[0]) >= 2 and len(t1.latlon.iloc[0][0]) == 2
    # nós do 1.º troço: só os que ficam dentro dele (0..216 m)
    assert W1.nodes[0] in t1.nos.iloc[0] and W1.nodes[-1] not in t1.nos.iloc[0]


def test_cola_so_a_vias_da_propria_linha():
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("A", 300, 105, 20, 90), ("A", 300, 5, 20, 90)), t)
    assert pd.isna(r.troco_id.iloc[0])           # perto da via da linha B: não cola
    assert r.troco_id.iloc[1] == "11:1"


def test_direccao_distingue_sentidos():
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("A", 300, 3, 20, 90), ("A", 300, 3, 20, 270)), t)
    assert list(r.dir) == [1, -1]
    assert list(r.troco_id) == ["11:1", "11:1"]   # a mesma via serve os dois sentidos


def test_parado_sem_direccao_cola_com_dir_zero():
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("A", 300, 3, 0, np.nan), ("A", 300, 3, 25, np.nan)), t)
    assert list(r.troco_id) == ["11:1", "11:1"]
    assert list(r.dir) == [0, 0]


def test_parado_com_direccao_usa_a_direccao():
    # o heading do GPS nunca vem nulo e mantém-se com o autocarro parado: decide o sentido (±90°)
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("A", 300, 3, 0, 90), ("A", 300, 3, 0, 270)), t)
    assert list(r.dir) == [1, -1]


def test_longe_de_tudo_nao_cola():
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("A", 300, 50, 20, 90)), t)
    assert pd.isna(r.troco_id.iloc[0])


def test_linha_sem_rota_nao_rebenta():
    t = linhas.dividir(ROTAS)
    r = linhas.colar(leituras(("107", 300, 3, 20, 90)), t)
    assert pd.isna(r.troco_id.iloc[0]) and r.dir.iloc[0] == 0


def test_prefere_via_alinhada_com_o_movimento():
    # W1 (sentido leste) a 3 m, W3 (sentido oeste) a 5 m: um autocarro que segue para oeste cola a W3
    t = linhas.dividir([Rota(1, "A", [W1, W3])])
    r = linhas.colar(leituras(("A", 300, 3, 20, 270)), t)
    assert r.troco_id.iloc[0].startswith("13:") and r.dir.iloc[0] == 1
