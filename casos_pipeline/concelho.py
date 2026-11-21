"""Pertença ao concelho do Porto e freguesia, pela CAOP 2025 (`dtmnfr` começa por 1312)."""
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

CAOP = Path(__file__).resolve().parents[1] / "CAOP_Continente_2025-gpkg" / "Continente_CAOP2025.gpkg"


@lru_cache(maxsize=1)
def _freguesias():
    g = gpd.read_file(CAOP, layer="cont_freguesias")
    return g[g["dtmnfr"].str.startswith("1312")].reset_index(drop=True)  # EPSG:3763


def _ponto(lat: float, lon: float) -> Point:
    return gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(3763).iloc[0]


def freguesia_de(lat: float, lon: float):
    """Nome da freguesia do Porto que contém o ponto; `None` se estiver fora do concelho."""
    p, g = _ponto(lat, lon), _freguesias()
    dentro = g[g.geometry.contains(p)]
    return None if dentro.empty else str(dentro.iloc[0]["freguesia"])


def dentro_do_porto(lat: float, lon: float) -> bool:
    return freguesia_de(lat, lon) is not None
