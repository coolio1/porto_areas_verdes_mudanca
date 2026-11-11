import json

import pytest

from velocidade import osm


def escrever(pasta, nome, elementos):
    (pasta / nome).write_text(json.dumps({"elements": elementos}), encoding="utf-8")


def via(i, nome, pts, nodes):
    return {"type": "way", "id": i, "tags": {"name": nome, "highway": "primary"} if nome else {},
            "nodes": nodes, "geometry": [{"lat": a, "lon": b} for a, b in pts]}


def rel(i, ref, operator, vias):
    return {"type": "relation", "id": i, "tags": {"type": "route", "route": "bus", "ref": ref, "operator": operator},
            "members": [{"type": "way", "ref": v, "role": ""} for v in vias] + [{"type": "node", "ref": 9, "role": "stop"}]}


def test_carregar_rotas_filtra_stcp_e_junta_vias(tmp_path):
    escrever(tmp_path, "rotas.json", [
        via(11, "Rua X", [(41.15, -8.60), (41.15, -8.59)], [1, 2]),
        via(12, "", [(41.15, -8.59), (41.16, -8.59)], [2, 3]),
        rel(100, "205", "STCP", [12, 11]),
        rel(101, "9999", "UNIR", [11]),
    ])
    rotas = osm.carregar_rotas(tmp_path)
    assert [(r.rel_id, r.ref) for r in rotas] == [(100, "205")]
    assert [v.way_id for v in rotas[0].vias] == [12, 11]          # ordem dos membros
    assert rotas[0].vias[1].nome == "Rua X" and rotas[0].vias[0].nome == ""
    assert rotas[0].vias[1].coords.shape == (2, 2)
    assert tuple(rotas[0].vias[1].coords[0]) == (-8.60, 41.15)      # (lon, lat)
    assert rotas[0].vias[1].nodes == [1, 2]


def test_carregar_paragens_ignora_nao_paragens(tmp_path):
    escrever(tmp_path, "paragens.json", [
        {"type": "node", "id": 1, "lat": 41.15, "lon": -8.6, "tags": {"highway": "bus_stop", "name": "Aliados"}},
        {"type": "way", "id": 2, "center": {"lat": 41.14, "lon": -8.61}, "tags": {"amenity": "bus_station"}},
        {"type": "node", "id": 3, "lat": 41.13, "lon": -8.62, "tags": {"amenity": "waste_basket"}},
    ])
    p = osm.carregar_paragens(tmp_path)
    assert len(p) == 2
    assert set(p.columns) >= {"lat", "lon", "nome"}
    assert "Aliados" in set(p.nome)


def test_descarregar_nao_grava_em_falha(tmp_path, monkeypatch):
    def falha(url, consulta):
        raise OSError("sem rede")
    monkeypatch.setattr(osm, "_pedir", falha)
    with pytest.raises(RuntimeError):
        osm.descarregar(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_descarregar_grava_as_duas_respostas(tmp_path, monkeypatch):
    monkeypatch.setattr(osm, "_pedir", lambda url, consulta: {"elements": [{"type": "node", "id": 1}]})
    osm.descarregar(tmp_path)
    assert (tmp_path / "paragens.json").exists() and (tmp_path / "rotas.json").exists()
