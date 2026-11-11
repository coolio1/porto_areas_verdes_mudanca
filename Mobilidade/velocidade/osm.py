"""Paragens e rotas de autocarro da STCP a partir do OpenStreetMap (Overpass), com cache em disco."""
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

CAIXA = "41.05,-8.80,41.30,-8.40"
SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
Q_PARAGENS = f"""[out:json][timeout:90];
(node["highway"="bus_stop"]({CAIXA});
 node["amenity"="bus_station"]({CAIXA});
 way["amenity"="bus_station"]({CAIXA}););
out center;"""
Q_ROTAS = f"""[out:json][timeout:180];
rel["type"="route"]["route"="bus"]["operator"~"STCP"]({CAIXA})->.r;
.r out body;
way(r.r);
out geom;"""


@dataclass
class Via:
    way_id: int
    nome: str
    coords: np.ndarray  # n×2, (lon, lat)
    nodes: list


@dataclass
class Rota:
    rel_id: int
    ref: str
    vias: list


def _pedir(url: str, consulta: str) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": consulta}).encode(),
                                 headers={"User-Agent": "porto-verde-mobilidade/1.0"})
    with urllib.request.urlopen(req, timeout=240) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return json.load(r)


def _consultar(consulta: str) -> dict:
    erros = []
    for url in SERVIDORES:
        try:
            dados = _pedir(url, consulta)
            if not isinstance(dados.get("elements"), list):
                raise RuntimeError("resposta sem 'elements'")
            return dados
        except Exception as e:  # falha de rede/servidor: tenta o seguinte, nunca grava
            erros.append(f"{url}: {e!r}")
    raise RuntimeError("Overpass indisponível: " + "; ".join(erros))


def descarregar(destino: Path) -> None:
    """Grava `paragens.json` e `rotas.json` em `destino`; só grava se as duas respostas chegarem."""
    import truststore
    truststore.inject_into_ssl()
    paragens = _consultar(Q_PARAGENS)
    rotas = _consultar(Q_ROTAS)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "paragens.json").write_text(json.dumps(paragens), encoding="utf-8")
    (destino / "rotas.json").write_text(json.dumps(rotas), encoding="utf-8")


def carregar_paragens(pasta: Path) -> pd.DataFrame:
    linhas = []
    for e in json.loads((Path(pasta) / "paragens.json").read_text(encoding="utf-8"))["elements"]:
        t = e.get("tags", {})
        if t.get("highway") != "bus_stop" and t.get("amenity") != "bus_station":
            continue
        c = e if "lat" in e else e.get("center")
        if c:
            linhas.append((c["lat"], c["lon"], t.get("name", "")))
    return pd.DataFrame(linhas, columns=["lat", "lon", "nome"])


def carregar_rotas(pasta: Path) -> list:
    els = json.loads((Path(pasta) / "rotas.json").read_text(encoding="utf-8"))["elements"]
    vias = {e["id"]: Via(e["id"], e.get("tags", {}).get("name", ""),
                         np.array([[g["lon"], g["lat"]] for g in e["geometry"]]), e.get("nodes", []))
            for e in els if e["type"] == "way" and e.get("geometry")}
    rotas = []
    for e in els:
        if e["type"] != "relation" or "stcp" not in e.get("tags", {}).get("operator", "").lower():
            continue
        membros = [vias[m["ref"]] for m in e.get("members", []) if m["type"] == "way" and m["ref"] in vias]
        rotas.append(Rota(e["id"], e["tags"].get("ref", ""), membros))
    return rotas
