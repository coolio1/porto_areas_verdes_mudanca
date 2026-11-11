import numpy as np
import pytest

from velocidade import dados, geo


def L(veiculo, obs, rec, v=10.0, **kw):
    return {"veiculo": veiculo, "observado_utc": obs, "recebido_utc": rec, "velocidade": v,
            "lon": -8.6, "lat": 41.15, "linha": "205", "viagem": "1", **kw}


def test_limpa_atraso_e_velocidade_absurda(pasta_csv):
    pasta = pasta_csv("posicoes_2026-11-09.csv", [
        L("a", "2026-11-09T10:00:00Z", "2026-11-09T10:00:30Z"),            # ok: atraso 30 s, 10 m/s
        L("b", "2026-11-09T10:00:00Z", "2026-11-09T09:59:55Z"),            # atraso -5 s
        L("c", "2026-11-09T10:00:00Z", "2026-11-09T10:06:40Z"),            # atraso 400 s
        L("d", "2026-11-09T10:00:00Z", "2026-11-09T10:00:30Z", v=33.34),   # 120 km/h
    ])
    df = dados.carregar(pasta)
    assert list(df.veiculo) == ["a"]
    assert df.kmh.iloc[0] == pytest.approx(36.0)


def test_ignora_duplicados_entre_ficheiros(pasta_csv):
    linha = L("a", "2026-11-09T23:59:50Z", "2026-11-10T00:00:10Z")
    pasta_csv("posicoes_2026-11-09.csv", [linha])
    pasta = pasta_csv("posicoes_2026-11-10.csv", [linha])
    assert len(dados.carregar(pasta)) == 1


def test_hora_local_e_tipo_dia(pasta_csv):
    pasta = pasta_csv("posicoes_2026-11-09.csv", [
        L("a", "2026-11-14T08:00:00Z", "2026-11-14T08:00:30Z"),  # sábado, inverno (UTC)
        L("b", "2026-11-09T17:30:00Z", "2026-11-09T17:30:30Z"),  # segunda
        L("c", "2026-07-01T16:30:00Z", "2026-07-01T16:30:30Z"),  # verão: Lisboa = UTC+1
    ])
    df = dados.carregar(pasta).set_index("veiculo")
    assert (df.loc["a", "hora"], df.loc["a", "tipo_dia"]) == (8, "fds")
    assert (df.loc["b", "hora"], df.loc["b", "tipo_dia"]) == (17, "util")
    assert df.loc["c", "hora"] == 17


def test_dias_com_dados_conta_so_dias_com_leituras_no_periodo(pasta_csv):
    pasta = pasta_csv("posicoes_2026-11-09.csv", [
        L("a", "2026-11-09T08:00:00Z", "2026-11-09T08:00:30Z"),   # segunda: só de manhã
        L("b", "2026-11-10T08:00:00Z", "2026-11-10T08:00:30Z"),   # terça: manhã
        L("c", "2026-11-10T17:30:00Z", "2026-11-10T17:30:30Z"),   # terça: tarde
    ])
    df = dados.carregar(pasta)
    assert dados.dias_com_dados(df, "pm", "util") == 1
    assert dados.dias_com_dados(df, "am", "util") == 2
    assert dados.dias_com_dados(df, "am", "fds") == 0


def test_geo_xy_metros():
    p = geo.xy(np.array([-8.6, -8.6]), np.array([41.15, 41.151]))
    assert p.shape == (2, 2)
    assert (p[1, 1] - p[0, 1]) == pytest.approx(111.32, abs=0.01)
