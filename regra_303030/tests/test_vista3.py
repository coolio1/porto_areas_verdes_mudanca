import sys
from pathlib import Path

import numpy as np
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vista3  # noqa: E402


def test_arvore_visivel_e_arvore_fora_do_raio():
    casa = box(0, 0, 10, 10)
    b, t, d, sem = vista3.calcular([casa], [(20, 5), (60, 5)])
    assert list(t) == [0] and d[0] <= 11 and sem[0] == 1


def test_arvore_atras_de_outro_edificio_e_bloqueada():
    casa = box(0, 0, 10, 10)
    muro = box(14, -50, 16, 50)           # parede comprida entre a casa e a árvore
    b, t, d, sem = vista3.calcular([casa, muro], [(25, 5)])
    assert 0 not in set(b)                # a casa não vê a árvore
    assert sem[0] == 1                    # mas ela estava a ≤ 30 m (sem bloqueio)


def test_janelas_ficam_fora_do_edificio():
    casa = box(0, 0, 10, 10)
    bi, x, y = vista3.janelas([casa])
    assert len(bi) >= 8
    assert not any(casa.contains(__import__("shapely").Point(a, c)) for a, c in zip(x, y))


def test_n3_conta_por_raio():
    b = np.array([0, 0, 0, 1])
    d = np.array([5.0, 15.0, 28.0, 10.0])
    assert list(vista3.n3(b, d, 2, raio=30)) == [3, 1]
    assert list(vista3.n3(b, d, 2, raio=20)) == [2, 1]


def test_arvore_so_visivel_de_uma_janela_conta_uma_vez():
    casa = box(0, 0, 10, 10)
    b, t, d, sem = vista3.calcular([casa], [(12, 5)])   # a 2 m da fachada: várias janelas a vêem
    assert len(b) == 1
