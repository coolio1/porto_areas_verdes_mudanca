"""Página «Análise»: o gerador preenche todos os marcadores e embute JSON válido."""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))

import gerar_analise  # noqa: E402


def _stub():
    return {"leituras": 1030681, "veiculos": 434, "linhas": 71, "dias": [{"d": "2026-11-08", "w": "dom", "at": False}, {"d": "2026-11-13", "w": "sex", "at": False}],
            "stcp": {"passagens": 379162, "dias": ["2026-10-19", "2026-10-20"]}}


def _html():
    return gerar_analise.renderizar(_stub(), AQUI / "analise" / "template.html")


def test_renderizar_preenche_marcadores():
    html = _html()
    for marca in ("__NAV__", "__LEITURAS__", "__VEICULOS__", "__LINHAS__", "__INTERVALO__", "__PASSAGENS__", "__DIASPACOTE__", "__DADOS__"):
        assert marca not in html
    assert "1 030 681" in html and "379 162" in html


def test_dados_embutidos_sao_json_valido():
    corpo = _html().split("const D = ", 1)[1].split(";\nconst S", 1)[0]
    assert json.loads(corpo)["stcp"]["passagens"] == 379162


def test_menu_tem_separador_analise():
    html = _html()
    assert 'href="analise.html"' in html and "Análise" in html


def test_corredores_sem_ficheiro_devolve_none(tmp_path):
    from analise import agregar
    assert agregar._classificar_corredores(None, tmp_path / "nao_existe.geojson") is None
