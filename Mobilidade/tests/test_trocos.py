import numpy as np
import pandas as pd
import pytest

from velocidade import geo, linhas, trocos
from velocidade.osm import Via

DIAS = ("2026-11-09", "2026-11-10")


def leit(n, veics=("a", "b", "c"), dias=DIAS, kmh=20.0, hora=17, dir_=1, espera=False, troco="T1"):
    return pd.DataFrame([{
        "troco_id": troco, "dir": dir_, "espera": espera, "kmh": kmh, "veiculo": veics[i % len(veics)],
        "viagem": f"v{i}", "dia": pd.Timestamp(dias[i % len(dias)]).date(), "hora": hora, "tipo_dia": "util",
    } for i in range(n)])


TROCOS = pd.DataFrame({"comprimento_m": [200.0]}, index=pd.Index(["T1"], name="troco_id"))


def agg(df, periodo="pm"):
    return trocos.agregar(df, TROCOS, periodo, "util")


def test_velocidade_ignora_esperas_mas_mantem_zeros_de_transito():
    df = pd.concat([leit(12, kmh=0.0), leit(12, kmh=30.0), leit(6, kmh=0.0, espera=True)], ignore_index=True)
    r = agg(df)
    assert len(r) == 1 and r.n.iloc[0] == 24 and r.v.iloc[0] == pytest.approx(15.0)


def test_passagens_contam_todas_as_leituras_e_so_dias_com_periodo():
    pm = leit(24, kmh=20.0)                                         # 2 dias, 24 passagens distintas na ponta da tarde
    manha = leit(4, dias=("2026-11-11",), hora=8, troco="T9")       # 3.º dia só de manhã
    r = agg(pd.concat([pm, manha], ignore_index=True))
    assert r.ph.iloc[0] == pytest.approx(24 / (2 * 3))              # 2 dias × 3 horas, não 3 dias


def test_passagens_incluem_as_leituras_de_espera():
    df = pd.concat([leit(24, kmh=20.0), leit(6, kmh=0.0, espera=True).assign(viagem=lambda d: "e" + d.viagem)], ignore_index=True)
    assert agg(df).ph.iloc[0] == pytest.approx(30 / 6)


@pytest.mark.parametrize("n,veics,dias", [(19, 3, 2), (24, 2, 2), (24, 3, 1)])
def test_minimo_de_amostra(n, veics, dias):
    df = leit(n, veics=("a", "b", "c")[:veics], dias=DIAS[:dias])
    assert agg(df).empty


def test_minimo_de_amostra_exacto_passa():
    assert len(agg(leit(20))) == 1


def test_tempo_perdido_valor_exacto():
    # L = 200 m a 10 km/h: 72 s; a 25 km/h: 28,8 s; 30 passagens/h -> 30 * 43,2 / 60 = 21,6
    df = leit(180, veics=("a", "b", "c"), kmh=10.0)               # 180 passagens / (2 dias × 3 h) = 30/h
    r = agg(df)
    assert r.ph.iloc[0] == pytest.approx(30.0) and r.perdido.iloc[0] == pytest.approx(21.6)


def test_leitura_com_dir_zero_conta_nas_duas_direccoes():
    r = agg(leit(24, dir_=0))
    assert sorted(r.dir) == [-1, 1] and set(r.n) == {24}


def test_tipo_de_dia_e_periodo_filtram():
    assert trocos.agregar(leit(24), TROCOS, "am", "util").empty
    assert trocos.agregar(leit(24), TROCOS, "pm", "fds").empty


def test_criticos_limiar():
    a = pd.DataFrame({"troco_id": ["a", "b"], "dir": [1, 1], "v": [13.9, 14.0], "perdido": [5.0, 5.0]})
    assert list(trocos.criticos(a).troco_id) == ["a"]


# --- marcadores ---
def via(way_id, nome, p0, p1, nodes):
    xs = np.linspace(p0[0], p1[0], len(nodes)); ys = np.linspace(p0[1], p1[1], len(nodes))
    return Via(way_id, nome, np.array([(-8.6 + x / geo.KX, 41.15 + y / geo.KY) for x, y in zip(xs, ys)]), nodes)


def test_marcadores_fundem_trocos_contiguos_e_nomeiam():
    from velocidade.osm import Rota
    x = via(1, "Rua X", (0, 0), (650, 0), [10, 11, 12, 13, 14, 15, 16])      # nó 13 a 325 m (troço 1)
    y = via(2, "Rua Y", (325, 0), (325, -300), [13, 21, 22, 23])
    t = linhas.dividir([Rota(1, "A", [x, y])])
    crit = pd.DataFrame({"troco_id": ["1:0", "1:1", "1:2"], "dir": [1, 1, 1], "v": [8.0, 6.0, 9.0], "perdido": [10.0, 30.0, 5.0]})
    m = trocos.marcadores(crit, t)
    assert len(m) == 1
    assert m[0]["rua"] == "Rua X" and m[0]["cruzamento"] == "Rua Y"
    assert m[0]["perdido"] == pytest.approx(45.0) and m[0]["v"] == pytest.approx(6.0)
    assert m[0]["troco_ids"] == ["1:0", "1:1", "1:2"]
    assert m[0]["lon"] == pytest.approx(-8.6 + 325 / geo.KX, abs=2e-5)   # meio do pior troço (o 1:1)
    assert m[0]["lat"] == pytest.approx(41.15, abs=1e-5)


def test_marcadores_nao_encadeiam_corredores_longos():
    from velocidade.osm import Rota
    x = via(1, "Rua X", (0, 0), (1600, 0), list(range(10, 25)))               # 8 troços seguidos
    t = linhas.dividir([Rota(1, "A", [x])])
    ids = [f"1:{i}" for i in range(8)]
    crit = pd.DataFrame({"troco_id": ids, "dir": 1, "v": 5.0, "perdido": [float(i + 1) for i in range(8)]})
    m = trocos.marcadores(crit, t)
    assert len(m) >= 3                                       # um corredor de 1,6 km não é um só ponto
    assert all(len(k["troco_ids"]) <= 3 for k in m)
    assert sorted(i for k in m for i in k["troco_ids"]) == sorted(ids)   # nenhum troço perdido nem repetido


def test_marcadores_sem_cruzamento_nao_rebenta():
    from velocidade.osm import Rota
    x = via(1, "Rua X", (0, 0), (150, 0), [10, 11, 12])
    t = linhas.dividir([Rota(1, "A", [x])])
    m = trocos.marcadores(pd.DataFrame({"troco_id": ["1:0"], "dir": [1], "v": [5.0], "perdido": [9.0]}), t)
    assert m[0]["cruzamento"] == ""


def test_marcadores_maximo():
    from velocidade.osm import Rota
    vias = [via(100 + i, f"Rua {i}", (i * 1000, 0), (i * 1000 + 150, 0), [i * 10, i * 10 + 1, i * 10 + 2]) for i in range(30)]
    t = linhas.dividir([Rota(1, "A", vias)])
    crit = pd.DataFrame({"troco_id": [f"{100 + i}:0" for i in range(30)], "dir": 1, "v": 5.0, "perdido": [float(i + 1) for i in range(30)]})
    m = trocos.marcadores(crit, t)
    assert len(m) == 15
    assert [round(k["perdido"]) for k in m] == list(range(30, 15, -1))   # os 15 maiores, por ordem decrescente
