import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mapa_png  # noqa: E402


def test_grelha_cobre_os_limites_a_3_m():
    w, h, tr = mapa_png.grelha()
    assert 4000 < w < 5000 and 2000 < h < 2500
    assert abs(tr.a * 111320 * np.cos(np.radians(41.16)) - 3.0) < 0.1     # ~3 m em x
    assert abs(-tr.e * 111320 - 3.0) < 0.1                                  # ~3 m em y


def test_numeros_pesa_por_residente_e_hectares():
    df = pd.DataFrame({"todos": [True, False, False], "nenhum": [False, False, True], "c3": [True, True, False],
                       "c30": [True, False, False], "c300": [True, False, True]})
    pop = np.array([10.0, 30.0, 60.0])
    ha = np.array([1e4, 2e4, 1e4])
    n = mapa_png.numeros(df, pop, ha)
    assert n["todos"] == {"edificios_pct": 33.3, "residentes_pct": 10.0, "ha": 1.0}
    assert n["c3"]["residentes_pct"] == 40.0
    assert n["total"] == {"edificios": 3, "residentes": 100, "ha": 4.0}


def test_png_1bit_valido_e_com_a_forma_certa():
    import struct
    import zlib
    m = np.zeros((5, 20), bool)
    m[2, 3:9] = True
    b = mapa_png.png_1bit(m)
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">IIBB", b[16:26]) == (20, 5, 1, 3)           # largura, altura, 1 bit, paleta
    i = b.index(b"IDAT")
    n = struct.unpack(">I", b[i - 4:i])[0]
    cru = zlib.decompress(b[i + 4:i + 4 + n])
    assert len(cru) == 5 * 4                                           # 5 linhas × (1 filtro + 3 bytes)
    assert sum(bin(x).count("1") for k in range(5) for x in cru[k * 4 + 1:(k + 1) * 4]) == 6


def test_camadas_conhecidas():
    df = pd.DataFrame({k: [True] for k in ("todos", "nenhum", "c3", "c30", "c300")})
    assert set(mapa_png.categorias(df)) == set(mapa_png.CAMADAS)


def test_edificios_fora_do_concelho_nao_contam():
    df = pd.DataFrame({"todos": [True, True, False], "nenhum": [False, False, True], "c3": [True, True, False],
                       "c30": [True, True, False], "c300": [True, True, False], "dentro": [True, False, True]})
    pop = np.array([10.0, 0.0, 90.0])
    ha = np.array([1e4, 5e4, 1e4])
    n = mapa_png.numeros(df, pop, ha)
    assert n["todos"] == {"edificios_pct": 50.0, "residentes_pct": 10.0, "ha": 1.0}     # o de fora não entra em nada
    assert n["total"] == {"edificios": 2, "residentes": 100, "ha": 2.0}
