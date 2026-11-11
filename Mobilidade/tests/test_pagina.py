import datetime
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from velocidade import geo, linhas, pagina
from velocidade.osm import Rota, Via

TEMPLATE = Path(__file__).resolve().parents[1] / "velocidade" / "template.html"
LON0, LAT0 = -8.6, 41.15
VAZIO = pd.DataFrame(columns=["troco_id", "dir", "n", "veic", "dias", "v", "ph", "perdido"])


def trocos_sinteticos(n_vias=1):
    vias = []
    for i in range(n_vias):
        xs = np.linspace(0, 650, 7)
        coords = np.array([(LON0 + x / geo.KX, LAT0 + i * 0.001) for x in xs])
        vias.append(Via(100 + i, f"Rua {i}", coords, list(range(i * 10, i * 10 + 7))))
    return linhas.dividir([Rota(1, "A", vias)])


def resultado(n_vias=1, fds=0):
    t = trocos_sinteticos(n_vias)
    ids = list(t.index)
    a = pd.DataFrame({"troco_id": ids, "dir": 1, "n": 30, "veic": 4, "dias": 2, "v": np.linspace(3, 20, len(ids)),
                      "ph": 12.5, "perdido": np.linspace(30, 0.5, len(ids))})
    marc = [{"lat": LAT0, "lon": LON0, "rua": "Rua 0", "cruzamento": "Rua Y", "perdido": 30.0, "v": 3.0, "troco_ids": ids[:2]}]
    agg = {(td, p): VAZIO for td in ("util", "fds") for p in ("dia", "am", "pm")}
    mk = {k: [] for k in agg}
    agg[("util", "pm")] = a
    mk[("util", "pm")] = marc
    return {"trocos": t, "agg": agg, "marcadores": mk, "dias": {"util": 2, "fds": fds}, "coladas_pct": 94.7,
            "intervalo": (datetime.date(2026, 11, 9), datetime.date(2026, 11, 10))}


def html(**kw):
    return pagina.renderizar(resultado(**kw), TEMPLATE)


def test_html_sem_fetch_e_com_chave_carto():
    h = html()
    assert "fetch(" not in h
    urls = re.findall(r"https://[^\"'\s]*basemaps\.cartocdn\.com[^\"'\s]*", h)
    assert urls and all("?key=" in u for u in urls)


def test_html_nao_diz_AMP_e_diz_STCP():
    h = html()
    assert not re.search(r"\bAMP\b", h)
    titulo = re.search(r"<title>(.*?)</title>", h, re.S).group(1)
    assert "STCP" in titulo and "STCP" in h.split("</title>")[1]


def test_so_dados_publicaveis():
    h = html()
    for proibido in ("recebido_utc", "veiculo", "viagem"):
        assert proibido not in h
    assert not re.search(r"[A-Za-z0-9._-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}", h)
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", h.replace("1.9.4", ""))


def test_tamanho_maximo_3MB():
    r = resultado(n_vias=1500)                      # ~9 000 troços, mais do que os reais
    ids = list(r["trocos"].index)
    for k in (("util", "pm"), ("util", "am"), ("util", "dia")):
        r["agg"][k] = r["agg"][("util", "pm")].assign(troco_id=ids[: len(r["agg"][("util", "pm")])])
    assert len(pagina.renderizar(r, TEMPLATE).encode("utf-8")) <= 3 * 1024 * 1024


def test_fim_de_semana_desactivado_sem_dados():
    h = html(fds=0)
    botao = re.search(r"<button[^>]*data-dia=\"fds\"[^>]*>.*?</button>", h, re.S).group(0)
    assert "disabled" in botao and "16 de Novembro" in botao


def test_fim_de_semana_com_um_so_dia_continua_desactivado():
    botao = re.search(r"<button[^>]*data-dia=\"fds\"[^>]*>.*?</button>", html(fds=1), re.S).group(0)
    assert "disabled" in botao and "16 de Novembro" in botao      # o mínimo de amostra exige 2 dias


def test_fim_de_semana_activo_com_dados():
    botao = re.search(r"<button[^>]*data-dia=\"fds\"[^>]*>.*?</button>", html(fds=2), re.S).group(0)
    assert "disabled" not in botao


def test_dados_json_estrutura_compacta():
    d = pagina.dados_json(resultado())
    v = d["variantes"]["util|pm"]
    assert len(v) == 3 and len(v[0]) == 6                       # [idx, dir, v, ph, perdido, n]
    assert d["variantes"]["util|am"] == []                       # sem amostra → lista vazia
    assert len(d["trocos"]) == 3                                 # só os troços usados, geometria uma vez
    assert d["marcadores"]["util|pm"][0]["rua"] == "Rua 0"
    assert d["dias"] == {"util": 2, "fds": 0} and d["intervalo"] == "9 a 10 de Novembro de 2026"


def test_variante_sem_amostra_diz_sem_dados():
    h = html()
    assert "Sem dados suficientes" in h
