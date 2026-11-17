"""Carregador comum dos edifícios do 3-30-300 (a mesma ordem que `rede300.py` usa em edificios_300.gpkg)."""
import os
from pathlib import Path

import geopandas as gpd

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
EXCLUIR = {"roof", "shed", "garage", "garages", "ruins", "construction", "carport", "service", "hut", "kiosk"}


def carregar():
    """Edifícios OSM do Porto sem anexos/ruínas, índice 0..N-1 (EPSG:3763). Ordem = linhas de edificios_300.gpkg."""
    ed = gpd.read_file(DADOS / "edificios_osm.gpkg")
    return ed[~ed["building"].isin(EXCLUIR)].reset_index(drop=True)
