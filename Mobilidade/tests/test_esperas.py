import pandas as pd

from velocidade import esperas, geo

LON0, LAT0 = -8.6, 41.15
T0 = pd.Timestamp("2026-11-09T10:00:00Z")
PARAGENS = pd.DataFrame({"lon": [LON0], "lat": [LAT0]})


def leituras(*rows):
    """rows: (veiculo, segundos, dx_m, dy_m, kmh) relativos à paragem."""
    return pd.DataFrame({
        "veiculo": [r[0] for r in rows],
        "obs": [T0 + pd.Timedelta(seconds=r[1]) for r in rows],
        "lon": [LON0 + r[2] / geo.KX for r in rows],
        "lat": [LAT0 + r[3] / geo.KY for r in rows],
        "kmh": [float(r[4]) for r in rows],
    })


def espera_do_primeiro(*rows):
    df = leituras(*rows)
    return bool(esperas.marcar_esperas(df, PARAGENS).iloc[0])


def test_zero_no_meio_da_rua_nunca_e_espera():
    assert espera_do_primeiro(("a", 0, 200, 0, 0)) is False


def test_zero_em_paragem_sem_vizinhos_e_espera():
    assert espera_do_primeiro(("a", 0, 10, 0, 0)) is True


def test_zero_em_paragem_com_fila_a_volta_e_transito():
    assert espera_do_primeiro(("a", 0, 10, 0, 0), ("b", 0, 150, 0, 3), ("c", 60, 0, 200, 5)) is False


def test_zero_em_paragem_com_transito_fluido_e_espera():
    assert espera_do_primeiro(("a", 0, 10, 0, 0), ("b", 0, 150, 0, 25), ("c", 60, 0, 200, 25)) is True


def test_autocarros_parados_junto_da_paragem_nao_provam_transito():
    # b e c também estão parados, a 60-70 m da mesma paragem (regulação/fila da paragem): não são prova de trânsito lento
    assert espera_do_primeiro(("a", 0, 10, 0, 0), ("b", 0, 60, 0, 0), ("c", 30, 70, 0, 0)) is True


def test_leitura_em_movimento_junto_a_paragem_nunca_e_espera():
    assert espera_do_primeiro(("a", 0, 10, 0, 30)) is False


def test_vizinhos_do_mesmo_veiculo_ou_a_mais_de_3_minutos_nao_contam():
    # só 1 vizinho válido (o "c" está a 4 min) e o "a2" é o mesmo veículo -> inconclusivo -> espera
    assert espera_do_primeiro(("a", 0, 10, 0, 0), ("b", 0, 150, 0, 3), ("a", 30, 120, 0, 3), ("c", 240, 100, 0, 3)) is True


def test_paradas_longas():
    quinze = [("a", 60 * i, 3 * (i % 2), 0, 0) for i in range(15)]
    assert esperas.marcar_paradas_longas(leituras(*quinze)).all()
    catorze = quinze[:14]
    assert not esperas.marcar_paradas_longas(leituras(*catorze)).any()


def _viagem(*rows, viagem="v1"):
    df = leituras(*rows)
    df["viagem"], df["dia"] = viagem, T0.date()
    return df


def test_paradas_em_terminal_5_min_junto_ao_fim_da_viagem():
    # a fica parado 6 min no fim da viagem (última leitura = ponta da viagem) -> espera
    fim = [("a", 0, 0, 0, 20), ("a", 60, 400, 0, 20)] + [("a", 120 + 60 * i, 800 + 2 * (i % 2), 0, 0) for i in range(7)]
    assert esperas.marcar_paradas_em_terminal(_viagem(*fim)).iloc[2:].all()


def test_paradas_em_terminal_menos_de_5_min_ou_a_meio_do_percurso_nao():
    curta = [("a", 0, 0, 0, 20)] + [("a", 60 + 60 * i, 800, 0, 0) for i in range(4)]       # 3 min
    assert not esperas.marcar_paradas_em_terminal(_viagem(*curta)).iloc[1:].any()
    # 7 min parado a 1,5 km das pontas da viagem: trânsito, não terminal
    meio = ([("a", 0, 0, 0, 20), ("a", 60, 700, 0, 20)] + [("a", 120 + 60 * i, 1500, 0, 0) for i in range(8)]
            + [("a", 700, 3000, 0, 20)])
    assert not esperas.marcar_paradas_em_terminal(_viagem(*meio)).iloc[2:10].any()


def test_paradas_longas_nao_apanha_veiculo_em_movimento():
    mov = [("a", 60 * i, 235 * i, 0, 15) for i in range(20)]
    assert not esperas.marcar_paradas_longas(leituras(*mov)).any()
