"""Dividir as vias das rotas STCP em troços e colar as leituras dos autocarros ao troço da sua linha."""
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString
from shapely.ops import substring

from . import geo


def dividir(rotas: list, alvo_m: float = 200.0) -> pd.DataFrame:
    """Um troço por pedaço de ~`alvo_m` de cada via; índice `troco_id` = "<way_id>:<n>"."""
    refs: dict[int, set] = {}
    vias = {}
    for r in rotas:
        for v in r.vias:
            vias[v.way_id] = v
            refs.setdefault(v.way_id, set()).add(r.ref)
    linhas = []
    for way_id, v in vias.items():
        xy = geo.xy(v.coords[:, 0], v.coords[:, 1])
        linha = LineString(xy)
        comp = linha.length
        if comp == 0:
            continue
        n = max(1, round(comp / alvo_m))
        # distância acumulada de cada nó, para saber que nós caem em cada troço
        acum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
        nos = np.array(v.nodes) if len(v.nodes) == len(acum) else None
        for i in range(n):
            a, b = i * comp / n, (i + 1) * comp / n
            geom = substring(linha, a, b)
            dentro = frozenset(nos[(acum >= a - 1e-6) & (acum <= b + 1e-6)].tolist()) if nos is not None else frozenset(v.nodes)
            ll = [[lat, lon] for lon, lat in (np.array(geom.coords) / [geo.KX, geo.KY])]
            linhas.append((f"{way_id}:{i}", way_id, v.nome, geom.length, geom, ll, frozenset(refs[way_id]), dentro))
    return pd.DataFrame(linhas, columns=["troco_id", "way_id", "nome", "comprimento_m", "geom", "latlon", "refs", "nos"]) \
        .set_index("troco_id")


def colar(df: pd.DataFrame, trocos: pd.DataFrame, max_dist_m: float = 30.0) -> pd.DataFrame:
    """Acrescenta `troco_id` (None se não colou) e `dir` (+1/−1 pelo sentido da via, 0 se a leitura não tem direcção).

    Só entram troços de vias da própria `linha`, a ≤ `max_dist_m`. Entre os candidatos, os alinhados com
    o movimento (heading dentro de ±90° da tangente) têm preferência; dentro de cada classe, o mais próximo.
    """
    n = len(df)
    out_id = np.full(n, None, dtype=object)
    out_dir = np.zeros(n, dtype=int)
    pts = shapely.points(geo.xy(df.lon, df.lat))
    head = df.direccao.to_numpy(float)
    linha = df.linha.astype(str).to_numpy()
    ids = trocos.index.to_numpy()
    geoms = trocos.geom.to_numpy()
    refs = trocos.refs.to_numpy()
    for ln in np.unique(linha):
        mask = np.array([ln in r for r in refs])
        if not mask.any():
            continue
        sel = np.where(linha == ln)[0]
        tg, ti = geoms[mask], ids[mask]
        a, b = shapely.STRtree(tg).query(pts[sel], predicate="dwithin", distance=max_dist_m)
        if len(a) == 0:
            continue
        p, g = pts[sel][a], tg[b]
        d = shapely.distance(p, g)
        s = shapely.line_locate_point(g, p)
        comp = shapely.length(g)
        p0 = shapely.line_interpolate_point(g, np.clip(s - 1.0, 0, comp))
        p1 = shapely.line_interpolate_point(g, np.clip(s + 1.0, 0, comp))
        tang = np.degrees(np.arctan2(shapely.get_x(p1) - shapely.get_x(p0), shapely.get_y(p1) - shapely.get_y(p0))) % 360
        h = head[sel][a]
        mov = ~np.isnan(h)  # o heading do GPS mantém-se com o autocarro parado; só a falta dele dá dir = 0
        alinhado = np.cos(np.radians(np.nan_to_num(h) - tang)) >= 0
        cand = pd.DataFrame({"a": a, "b": b, "classe": np.where(mov & ~alinhado, 1, 0), "d": d,
                             "dir": np.where(mov, np.where(alinhado, 1, -1), 0)})
        melhor = cand.sort_values(["a", "classe", "d"]).drop_duplicates("a")
        idx = sel[melhor.a.to_numpy()]
        out_id[idx] = ti[melhor.b.to_numpy()]
        out_dir[idx] = melhor.dir.to_numpy()
    res = df.copy()
    res["troco_id"] = out_id
    res["dir"] = out_dir
    return res
