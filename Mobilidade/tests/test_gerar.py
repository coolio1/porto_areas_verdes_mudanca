import json

import numpy as np
import pytest

import gerar_autocarros
from velocidade import geo

LON0, LAT0 = -8.6, 41.15


def ll(x, y):
    return LON0 + x / geo.KX, LAT0 + y / geo.KY


def osm_sintetico(pasta):
    pts = [ll(x, 0) for x in np.linspace(0, 650, 7)]
    via = {"type": "way", "id": 11, "tags": {"name": "Rua X"}, "nodes": list(range(10, 17)),
           "geometry": [{"lat": la, "lon": lo} for lo, la in pts]}
    rel = {"type": "relation", "id": 1, "tags": {"ref": "A", "operator": "STCP"},
           "members": [{"type": "way", "ref": 11, "role": ""}]}
    (pasta / "rotas.json").write_text(json.dumps({"elements": [via, rel]}), encoding="utf-8")
    lo, la = ll(300, 5000)  # paragem longe de tudo
    (pasta / "paragens.json").write_text(json.dumps({"elements": [
        {"type": "node", "id": 1, "lat": la, "lon": lo, "tags": {"highway": "bus_stop", "name": "Longe"}}]}), encoding="utf-8")


def test_calcular_sintetico(pasta_csv, tmp_path):
    lon, lat = ll(300, 3)
    linhas = []
    for dia in ("2026-11-09", "2026-11-10"):               # segunda e terça
        for i, veic in enumerate(("a", "b", "c") * 4):     # 12 leituras por dia, 3 veículos
            lon, lat = ll(240 + 40 * (i // 3), 3)          # em marcha lenta (40 m cada 3 min), não parado no mesmo sítio
            linhas.append({"veiculo": veic, "observado_utc": f"{dia}T17:{i:02d}:00Z", "recebido_utc": f"{dia}T17:{i:02d}:30Z",
                           "velocidade": 1.4, "direccao": 90, "linha": "A", "viagem": f"v{i}", "lon": lon, "lat": lat})
    lon, lat = ll(300, 3)
    linhas.append({"veiculo": "z", "observado_utc": "2026-11-09T17:30:00Z", "recebido_utc": "2026-11-09T17:30:30Z",
                   "velocidade": 5, "direccao": 90, "linha": "107", "viagem": "x", "lon": lon, "lat": lat})   # linha sem rota
    pasta_dados = pasta_csv("posicoes_2026-11-09.csv", linhas)
    pasta_osm = tmp_path / "osm"
    pasta_osm.mkdir()
    osm_sintetico(pasta_osm)

    r = gerar_autocarros.calcular(pasta_dados, pasta_osm)

    assert r["dias"] == {"util": 2, "fds": 0}
    assert r["coladas_pct"] == pytest.approx(24 / 25 * 100)
    a = r["agg"][("util", "pm")]
    assert list(a.troco_id) == ["11:1"] and list(a.dir) == [1] and a.n.iloc[0] == 24
    assert a.v.iloc[0] == pytest.approx(1.4 * 3.6)
    assert r["agg"][("fds", "pm")].empty and r["agg"][("util", "am")].empty
    m = r["marcadores"][("util", "pm")]
    assert len(m) == 1 and m[0]["rua"] == "Rua X"
    assert r["intervalo"] == (pytest.importorskip("datetime").date(2026, 11, 9), pytest.importorskip("datetime").date(2026, 11, 10))
