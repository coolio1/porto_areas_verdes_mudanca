"""Carregador comum dos edifícios do 3-30-300 (a mesma ordem que `rede300.py` usa em edificios_300.gpkg)."""
import os
from pathlib import Path

import geopandas as gpd

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
EXCLUIR = {"roof", "shed", "garage", "garages", "ruins", "construction", "carport", "service", "hut", "kiosk"}


CAOP = Path(__file__).resolve().parents[1] / "CAOP_Continente_2025-gpkg" / "CAOP2025_municipios.shp"


def dentro_do_porto(ed):
    """Máscara booleana: ponto representativo do edifício dentro do concelho do Porto (CAOP 2025, dtmn 1312).
    O OSM traz edifícios que só tocam o limite; os totais contam só os de dentro."""
    caop = gpd.read_file(CAOP)
    poly = caop[caop["dtmn"] == "1312"].to_crs(3763).geometry.iloc[0]
    return ed.geometry.representative_point().within(poly).values


def carregar():
    """Edifícios OSM do Porto sem anexos/ruínas, índice 0..N-1 (EPSG:3763). Ordem = linhas de edificios_300.gpkg."""
    ed = gpd.read_file(DADOS / "edificios_osm.gpkg")
    return ed[~ed["building"].isin(EXCLUIR)].reset_index(drop=True)
