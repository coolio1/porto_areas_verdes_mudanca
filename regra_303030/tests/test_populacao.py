import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import populacao  # noqa: E402


def test_distribuir_conserva_e_pesa():
    cel = [1, 1, 1, 2]
    pop, perdida = populacao.distribuir(cel, {1: 100.0, 2: 40.0, 3: 7.0}, [10, 30, 60, 5], [True, True, True, True])
    assert pop.tolist() == [10.0, 30.0, 60.0, 40.0]
    assert perdida == 7.0                      # célula 3 sem edifícios


def test_nao_residenciais_ficam_sem_peso_salvo_se_forem_os_unicos():
    pop, _ = populacao.distribuir([1, 1, 2], {1: 100.0, 2: 50.0}, [50, 50, 10], [True, False, False])
    assert pop.tolist() == [100.0, 0.0, 50.0]  # célula 2: só há não residencial, fica com tudo


def test_pesos_zero_nao_dividem_por_zero():
    pop, perdida = populacao.distribuir([1], {1: 10.0}, [0.0], [True])
    assert pop.tolist() == [0.0] and perdida == 10.0
