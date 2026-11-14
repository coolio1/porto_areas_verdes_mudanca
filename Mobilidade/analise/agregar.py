"""Agregados da recolha própria para a página «Análise» (Mobilidade/analise.html): só números por dia×hora, linha, rua; nunca por veículo.

Velocidades e troços usam só a recolha própria (velocidade medida): a velocidade calculada do pacote da STCP subestima e
infla os troços «críticos» (calibração de 2026-11-13, dias 9–12). Com `com_pacote=True` o pacote entra nos gráficos de nível.
Os dias atípicos (quarta 11 de Novembro: viagens 18 % mais curtas, causa desconhecida) saem do «dia útil típico» e têm o seu capítulo.
"""
import datetime as dt
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from velocidade import dados, esperas, geo, linhas, osm, trocos  # noqa: E402

DIAS_SEM = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
DIAS_ATIPICOS = {dt.date(2026, 11, 11)}
CENTRO = (41.1496, -8.6110)                       # Aliados
ANEL_M, N_ANEIS = 500.0, 20
PERIODOS = {"am": (7, 9), "almoco": (12, 14), "pm": (17, 19)}
BINS_V = np.arange(0, 52.5, 2.5)


def _marcar(df, paragens):
    df["esp_par"] = esperas.marcar_esperas(df, paragens)
    df["esp_longa"] = esperas.marcar_paradas_longas(df)
    df["esp_term"] = esperas.marcar_paradas_em_terminal(df)
    df["espera"] = df.esp_par | df.esp_longa | df.esp_term
    return df


def _h(h0, h1, s):            # horas [h0, h1)
    return s.hora.between(h0, h1 - 1)


def _episodios_por_dia(df, min_s=300.0, raio_m=25.0):
    """Nº de paragens ≥ 5 min no mesmo sítio, por dia (todas as leituras, sem identificar veículos)."""
    o = df.sort_values(["veiculo", "obs"])
    p = geo.xy(o.lon, o.lat)
    t = (o.obs - o.obs.min()).dt.total_seconds().to_numpy()
    v, d = o.veiculo.to_numpy(), o.dia.to_numpy()
    cont, durs = {}, []
    i, n = 0, len(o)
    while i < n:
        j = i + 1
        while j < n and v[j] == v[i] and math.hypot(*(p[j] - p[i])) < raio_m:
            j += 1
        if t[j - 1] - t[i] >= min_s:
            cont[d[i]] = cont.get(d[i], 0) + 1
            durs.append((t[j - 1] - t[i]) / 60)
        i = j
    return {k.isoformat(): n for k, n in sorted(cont.items())}, durs


CORREDORES = "corredores_bus.geojson"      # Câmara do Porto, dados abertos (CC0): dadosabertos.cm-porto.pt/dataset/corredores-bus
COM_MIN, PERTO_M, COM_M = 0.6, 30.0, 15.0   # «com corredor»: ≥ 60 % do troço a ≤ 15 m de um corredor activo; «sem»: nenhum a ≤ 30 m
ANEIS_KM = [(0, 1), (1, 2), (2, 3.5), (3.5, 6)]
MIN_RUA = 4                                  # troços-sentido-período, de cada lado, para comparar a mesma rua


def _lidar(v: pd.Series) -> list:
    n = len(v)
    return [round(float(v.mean()), 2), int(n), round(float(v.std(ddof=1) / math.sqrt(n)), 2) if n > 1 else None]


def _corredores(ub, t, caminho: Path):
    """Velocidade dos troços com e sem corredor BUS (activos), por anel de distância ao centro e na mesma rua. None sem ficheiro."""
    if not caminho.exists():
        return None
    import json
    import shapely
    from shapely.geometry import LineString
    gj = json.loads(caminho.read_text(encoding="utf-8"))
    activos = [f for f in gj["features"] if f["properties"].get("estado_corredor") == "Ativo"]
    partes = []
    for f in activos:
        gm = f["geometry"]
        for p in ([gm["coordinates"]] if gm["type"] == "LineString" else gm["coordinates"]):
            c = np.array(p)
            partes.append(LineString(geo.xy(c[:, 0], c[:, 1])))
    uniao = shapely.union_all(partes)
    b_com, b_perto = uniao.buffer(COM_M), uniao.buffer(PERTO_M)
    centro = shapely.Point(*geo.xy([CENTRO[1]], [CENTRO[0]])[0])
    info = pd.DataFrame({"f_com": [g.intersection(b_com).length / g.length for g in t.geom],
                         "perto": [g.intersects(b_perto) for g in t.geom],
                         "km": [centro.distance(g) / 1000 for g in t.geom], "nome": t.nome.to_numpy()}, index=t.index)
    info["grupo"] = np.where(info.f_com >= COM_MIN, "com", np.where(~info.perto, "sem", "meio"))
    linhas_ = []
    for per in ("am", "pm"):
        a = trocos.agregar(ub, t, per, "util")
        linhas_.append(a.assign(per=per).join(info, on="troco_id"))
    d = pd.concat(linhas_, ignore_index=True)
    r = {"activos": len(activos), "ruas_com_corredor": len({f["properties"]["toponimo"] for f in activos}),
         "troços_com": int((info.grupo == "com").sum()), "troços_total": int(len(info)),
         "bruto": {g: _lidar(d[d.grupo == g].v) for g in ("com", "meio", "sem")}, "aneis": [], "ruas": []}
    for lo, hi in ANEIS_KM:
        x = d[(d.km >= lo) & (d.km < hi)]
        r["aneis"].append({"lo": lo, "hi": hi, "com": _lidar(x[x.grupo == "com"].v) if (x.grupo == "com").any() else None,
                           "sem": _lidar(x[x.grupo == "sem"].v) if (x.grupo == "sem").any() else None})
    cs = d[d.grupo.isin(["com", "sem"])].groupby(["nome", "grupo"]).v.agg(["mean", "size"]).unstack()
    for nome, x in cs.iterrows():
        if x[("size", "com")] >= MIN_RUA and x[("size", "sem")] >= MIN_RUA:
            r["ruas"].append({"rua": nome, "com": round(float(x[("mean", "com")]), 2), "sem": round(float(x[("mean", "sem")]), 2),
                              "n_com": int(x[("size", "com")]), "n_sem": int(x[("size", "sem")])})
    r["ruas"].sort(key=lambda z: z["com"] - z["sem"], reverse=True)   # maior vantagem do corredor primeiro
    return r


def calcular(pasta_dados: Path, pasta_stcp: Path | None = None, com_pacote: bool = False) -> dict:
    todos = dados.carregar(pasta_dados, pasta_stcp if com_pacote else None)
    paragens = osm.carregar_paragens(pasta_dados / "osm")
    t = linhas.dividir(osm.carregar_rotas(pasta_dados / "osm"))
    nivel = _marcar(todos, paragens)                                    # base dos gráficos de velocidade
    tip = nivel[~nivel.dia.isin(DIAS_ATIPICOS)]
    mov = tip[~tip.espera]
    util = mov[mov.tipo_dia == "util"].copy()
    ntip = tip[tip.tipo_dia == "util"]
    out = {"com_pacote": com_pacote, "leituras": int(len(nivel)), "veiculos": int(nivel.veiculo.nunique()), "linhas": int(nivel.linha.nunique()),
           "atipicos": sorted(d.isoformat() for d in DIAS_ATIPICOS), "dias_tipicos": int(util.dia.nunique())}

    # G12A / calendário dia × hora (todos os dias da recolha própria)
    dias = sorted(nivel.dia.unique())
    idx = {d: i for i, d in enumerate(dias)}
    out["dias"] = [{"d": d.isoformat(), "w": DIAS_SEM[pd.Timestamp(d).dayofweek], "at": d in DIAS_ATIPICOS} for d in dias]
    g = nivel[~nivel.espera].groupby(["dia", "hora"]).kmh.agg(["mean", "size"])
    out["dh"] = [[idx[d], int(h), round(float(r["mean"]), 2), int(r["size"])] for (d, h), r in g.iterrows() if r["size"] >= 200]
    out["paradas_longas_dia"], durs = _episodios_por_dia(nivel)
    out["paradas_longas_dur"] = {"mediana_min": round(float(np.median(durs)), 1), "n": len(durs), "horas_dia": round(sum(durs) / 60 / max(1, nivel.dia.nunique()), 1)}

    # G1 orçamento do tempo (dias úteis típicos, todas as leituras)
    cat = np.select([ntip.esp_term, ntip.esp_par | ntip.esp_longa, ntip.kmh <= 2, ntip.kmh < 10], ["terminal", "paragem", "transito", "devagar"], "andar")
    ntip = ntip.assign(cat=cat)
    orc = []
    for h in range(24):
        x = ntip[ntip.hora == h]
        if len(x) < 500:
            orc.append(None)
            continue
        f = x.cat.value_counts(normalize=True) * 100
        orc.append({"andar": round(float(f.get("andar", 0)), 1), "devagar": round(float(f.get("devagar", 0)), 1),
                    "transito": round(float(f.get("transito", 0)), 1), "paragem": round(float(f.get("paragem", 0) + f.get("terminal", 0)), 1), "n": int(len(x))})
    out["orcamento"] = {"horas": orc, "dias": int(ntip.dia.nunique())}

    # G2 distribuição da velocidade por hora
    dist = []
    for h in range(24):
        x = util[util.hora == h].kmh
        if len(x) < 500:
            dist.append(None)
            continue
        c, _ = np.histogram(np.clip(x, 0, 50), bins=BINS_V)
        dist.append({"c": (c / c.sum()).round(4).tolist(), "med": round(float(x.median()), 1), "p10": round(float(x.quantile(.1)), 1),
                     "p90": round(float(x.quantile(.9)), 1), "n": int(len(x)), "parados": round(float((x < 2).mean() * 100), 1)})
    out["dist"] = {"bins": BINS_V.tolist(), "horas": dist, "dias": int(util.dia.nunique())}

    # G4 maré (entra / sai) e perfil radial
    cx, cy = geo.xy(np.array([CENTRO[1]]), np.array([CENTRO[0]]))[0]
    p = geo.xy(util.lon, util.lat)
    vx, vy = cx - p[:, 0], cy - p[:, 1]
    d_centro = np.hypot(vx, vy)
    azim = np.degrees(np.arctan2(vx, vy)) % 360
    cosang = np.cos(np.radians(util.direccao.to_numpy(float) - azim))
    util = util.assign(dist=d_centro, cosang=cosang, ds=util.dia.astype(str))
    m = util[util.dist.between(1500, 8000)]
    m = m.assign(sent=np.select([m.cosang > .5, m.cosang < -.5], ["entra", "sai"], "trans"))
    mare = []
    for h in range(24):
        x = m[m.hora == h]
        e, s = x[x.sent == "entra"].kmh, x[x.sent == "sai"].kmh
        mare.append({"entra": [round(float(e.mean()), 2), int(len(e))], "sai": [round(float(s.mean()), 2), int(len(s))]} if len(e) >= 300 and len(s) >= 300 else None)
    por_dia = {}
    for ds, x in m.groupby("ds"):
        for nome, (h0, h1) in (("am", (7, 9)), ("pm", (17, 19))):
            y = x[_h(h0, h1, x)]
            e, s = y[y.sent == "entra"].kmh, y[y.sent == "sai"].kmh
            if len(e) >= 300 and len(s) >= 300:
                por_dia.setdefault(ds, {})[nome] = [round(float(e.mean()), 2), round(float(s.mean()), 2)]
    util["anel"] = np.minimum((util.dist // ANEL_M).astype(int), N_ANEIS - 1)
    perfil = {}
    for nome, (h0, h1) in PERIODOS.items():
        s = util[_h(h0, h1, util)]
        a = s.groupby("anel").kmh.agg(["mean", "size", lambda v: v.quantile(.25), lambda v: v.quantile(.75)])
        perfil[nome] = [[int(i), round(float(r.iloc[0]), 2), int(r.iloc[1]), round(float(r.iloc[2]), 1), round(float(r.iloc[3]), 1)]
                        for i, r in a.iterrows() if r.iloc[1] >= 300]
    out["mare"] = {"horas": mare, "dias": por_dia}
    out["radial"] = {"anel_m": ANEL_M, "perfil": perfil}

    # G6 linhas (velocidade em movimento, manhã e tarde)
    por_l = []
    for lin, s in util.groupby("linha"):
        if len(s) < 800 or s.veiculo.nunique() < 3:
            continue
        am, pm = s[_h(7, 9, s)].kmh, s[_h(17, 19, s)].kmh
        por_l.append({"l": str(lin), "v": round(float(s.kmh.mean()), 2),
                      "am": round(float(am.mean()), 2) if len(am) > 150 else None, "pm": round(float(pm.mean()), 2) if len(pm) > 150 else None,
                      "n": int(len(s)), "veic": int(s.veiculo.nunique())})
    out["linhas_dados"] = sorted(por_l, key=lambda d: d["v"])

    # G5 ruas: tempo perdido por troço (min/h face a 25 km/h) nos picos, dias úteis típicos
    ub = linhas.colar(tip.copy(), t)
    nomes = t.nome.to_dict()
    tot = {}
    for per in ("am", "pm"):
        a = trocos.agregar(ub, t, per, "util")
        for r in a.itertuples():
            tot.setdefault((r.troco_id, int(r.dir)), {})[per] = float(r.perdido)
    ordem = sorted(tot.items(), key=lambda kv: -sum(kv[1].values()))
    perd = np.array([sum(v.values()) for _, v in ordem])
    cum = np.cumsum(perd) / max(1e-9, perd.sum())
    passos = np.unique(np.r_[np.arange(0, len(perd), max(1, len(perd) // 150)), len(perd) - 1])
    out["lorenz"] = {"n": int(len(perd)), "total_min_h": round(float(perd.sum()), 1),
                     "curva": [[round(float((i + 1) / len(perd)), 4), round(float(cum[i]), 4)] for i in passos]}
    por_rua, pos_rua = {}, {}
    for rank, ((tid, _), v) in enumerate(ordem):
        nm = nomes.get(tid) or "(sem nome)"
        r = por_rua.setdefault(nm, {"am": 0.0, "pm": 0.0, "n": 0})
        r["am"] += v.get("am", 0); r["pm"] += v.get("pm", 0); r["n"] += 1
        pos_rua.setdefault(nm, []).append([round((rank + 1) / len(perd), 4), round(float(cum[rank]), 4)])
    top = sorted(por_rua.items(), key=lambda kv: -(kv[1]["am"] + kv[1]["pm"]))[:15]
    out["ruas"] = [{"rua": k, "am": round(v["am"], 1), "pm": round(v["pm"], 1), "n": v["n"], "pontos": pos_rua[k][:60]} for k, v in top]

    out["corredores"] = _corredores(ub, t, pasta_dados / CORREDORES)

    # serviço: autocarros e viagens por hora (dias úteis típicos)
    g = ntip.groupby(["dia", "hora"]).agg(veic=("veiculo", "nunique"), viag=("viagem", "nunique"))
    mm = g.groupby("hora").mean()
    out["servico"] = {"dias": int(ntip.dia.nunique()), "veic": [round(float(mm.veic.get(h, 0)), 1) for h in range(24)],
                      "viag": [round(float(mm.viag.get(h, 0)), 1) for h in range(24)]}
    return out
