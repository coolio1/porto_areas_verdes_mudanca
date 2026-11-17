import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copa500  # noqa: E402


def test_agregar_conta_blocos():
    m = np.zeros((20, 20), np.uint8)
    m[:10, :10] = 1       # bloco (0,0) todo copa
    m[10:, 10:] = 255     # bloco (1,1) sem dados
    c, v = copa500.agregar(m, 10)
    assert c.tolist() == [[100, 0], [0, 0]] and v.tolist() == [[100, 100], [100, 0]]


def test_convolucao_meio_copa_da_50_por_cento():
    n = 400
    copa = np.zeros((n, n), np.float32)
    copa[:, : n // 2] = 100       # metade esquerda: copa total (100 px por célula)
    val = np.full((n, n), 100, np.float32)
    pct, cob = copa500.convolucao(copa, val, 500)
    assert abs(pct[200, 199] - 0.5) < 0.02    # sobre a linha de separação
    assert pct[200, 5] > 0.9 and pct[200, 395] < 0.1
    assert cob[200, 200] > 0.99               # disco inteiro dentro da grelha


def test_cobertura_baixa_na_borda_e_pct_sobre_a_parte_valida():
    n = 400
    copa = np.full((n, n), 100, np.float32)   # tudo copa
    val = np.full((n, n), 100, np.float32)
    pct, cob = copa500.convolucao(copa, val, 500)
    assert abs(pct[200, 0] - 1.0) < 1e-3      # % = copa/válida, mesmo no bordo
    assert cob[200, 0] < 0.6                  # só ~metade do disco existe


def test_folha_sem_dados_nao_entra_no_denominador():
    n = 200
    copa = np.zeros((n, n), np.float32)
    val = np.full((n, n), 100, np.float32)
    val[:, :100] = 0                          # metade «má»/fora
    copa[:, 100:] = 50                        # na parte válida, 50 % de copa
    pct, _ = copa500.convolucao(copa, val, 500)
    assert abs(pct[100, 150] - 0.5) < 1e-3
