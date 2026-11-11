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


def test_paradas_longas_nao_apanha_veiculo_em_movimento():
    mov = [("a", 60 * i, 235 * i, 0, 15) for i in range(20)]
    assert not esperas.marcar_paradas_longas(leituras(*mov)).any()
