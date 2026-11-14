"""Propostas de medidas: classificação do tipo de zona, medida, ganho, faixas do OSM e confiança."""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))

from analise import propostas as P  # noqa: E402


def test_faixas_sentido():
    assert P.faixas_sentido({"lanes": "2", "oneway": "yes"}, 1) == 2
    assert P.faixas_sentido({"lanes": "4"}, 1) == 2          # dois sentidos sem lanes:forward: total ÷ 2
    assert P.faixas_sentido({"lanes": "4", "lanes:forward": "3"}, 1) == 3
    assert P.faixas_sentido({"lanes": "4", "lanes:backward": "1"}, -1) == 1
    assert P.faixas_sentido({"lanes": "2", "junction": "roundabout"}, 1) == 2
    assert P.faixas_sentido({}, 1) is None
    assert P.faixas_sentido({"lanes": "x"}, 1) is None


def test_tipo_zona_ordem():
    assert P.tipo_zona(0.3, 0.6, True, 2) == "paragem"       # paragem vence rotunda e semáforo
    assert P.tipo_zona(0.3, 0.1, True, 2) == "rotunda"
    assert P.tipo_zona(0.9, 0.1, False, 2) == "semaforo"      # lenta o dia todo + semáforo
    assert P.tipo_zona(0.9, 0.1, False, 0) == "fixo"
    assert P.tipo_zona(0.4, 0.1, False, 3) == "transito"      # lenta só na ponta: trânsito, mesmo com semáforo
    assert P.tipo_zona(None, None, False, 0) == "transito"


def test_medida_corredor_so_com_duas_faixas():
    assert P.medida_zona("transito", 0.0, 2)[0] == "corredor"
    assert P.medida_zona("transito", 0.0, 1)[0] == "sem_espaco"
    assert P.medida_zona("transito", 0.0, None)[0] == "corredor_verificar"
    assert P.medida_zona("transito", 0.6, 3)[0] == "ja_tem"
    assert P.medida_zona("semaforo", 0.0, 3)[0] == "semaforo"
    assert P.medida_zona("paragem", 0.0, 3)[0] == "paragem"


def test_ganho_nunca_passa_a_velocidade_entre_pontas():
    linhas = [(200.0, 5.0, 20.0)]
    g_livre = P.ganho_min_h(linhas, 25.0, None)
    g_cap = P.ganho_min_h(linhas, 25.0, 10.0)
    assert g_cap < g_livre
    assert abs(g_cap - 20.0 * (200 / (5 / 3.6) - 200 / (10 / 3.6)) / 60) < 1e-9
    assert P.ganho_min_h(linhas, 4.0, None) == 0.0            # alvo mais lento que o troço: sem ganho


def test_confianca_alta_exige_muitos_dias():
    assert P.confianca(4, 4, 4, 5, 500) == "média"             # 4 dias: no máximo média
    assert P.confianca(12, 12, 12, 5, 500) == "alta"
    assert P.confianca(12, 9, 12, 5, 500) == "média"
    assert P.confianca(4, 1, 4, 5, 500) == "baixa"
