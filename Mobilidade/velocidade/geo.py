"""Projecção local simples (lon/lat -> metros) para a zona do Porto."""
import numpy as np

LAT0 = 41.15
KX = 111320.0 * np.cos(np.radians(LAT0))
KY = 111320.0


def xy(lon, lat) -> np.ndarray:
    """Devolve um array n×2 com (x, y) em metros."""
    return np.c_[np.asarray(lon, dtype=float) * KX, np.asarray(lat, dtype=float) * KY]
