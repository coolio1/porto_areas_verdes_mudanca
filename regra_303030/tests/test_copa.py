import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copa  # noqa: E402


def _cena():
    nd = np.zeros((10, 10), "float32")
    nd[0:3, 0:3] = 8.0           # edifício
    nd[5:8, 5:8] = 6.0           # copa
    nd[9, 9] = 2.0               # arbusto < 3 m
    peg = np.zeros((10, 10), bool)
    peg[0:3, 0:3] = True
    dentro = np.ones((10, 10), bool)
    return nd, peg, dentro


def test_mascara_classes():
    nd, peg, dentro = _cena()
    nd[4, 4] = np.nan
    m = copa.mascara(nd, peg, dentro)
    assert m[1, 1] == copa.EDIFICIO
    assert m[6, 6] == copa.COPA
    assert m[9, 9] == copa.SEM_COPA
    assert m[4, 4] == copa.NODATA


def test_fora_do_concelho_e_nodata():
    nd, peg, dentro = _cena()
    dentro[:, 5:] = False
    m = copa.mascara(nd, peg, dentro)
    assert (m[:, 5:] == copa.NODATA).all()


def test_diagnostico_folha_boa():
    nd, peg, dentro = _cena()
    neg, telh, c, ma, motivo = copa.diagnostico(nd, peg, dentro, 0)
    assert neg == 0 and telh == 8.0 and not ma and motivo == ""
    assert round(c, 1) == round(100 * 9 / 91, 1)


def test_folha_ma_exige_datas_e_negativos():
    nd, peg, dentro = _cena()
    nd[4:10:2, 0:5] = -5.0        # linhas finas e dispersas: >2 % de negativos
    assert copa.diagnostico(nd, peg, dentro, 100, min_agua=1000)[3] is True      # datas afastadas + negativos
    aviso = copa.diagnostico(nd, peg, dentro, 0, min_agua=1000)
    assert aviso[3] is False and "verificar" in aviso[4]            # datas próximas: só aviso
    nd2, peg2, dentro2 = _cena()
    assert copa.diagnostico(nd2, peg2, dentro2, 200)[3] is False   # datas afastadas sem negativos


def test_mancha_continua_e_agua():
    nd, peg, dentro = _cena()
    nd[3:10, 0:5] = -5.0          # mancha contínua = rio
    r = copa.diagnostico(nd, peg, dentro, 400, min_agua=20)
    assert r[3] is False and "água" in r[4]                         # datas afastadas mas só água: não é má
