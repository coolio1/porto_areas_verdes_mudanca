"""Propostas de medidas para as zonas mais lentas da rede (hipóteses a validar, não um estudo de tráfego).

Passos: (1) só entram troços críticos (< 14 km/h) em ≥ 75 % dos dias, com ≥ 2 linhas e ≥ 50 leituras; (2) juntam-se os troços ligados
entre si numa zona de ≥ 300 m; (3) cada zona recebe um tipo provável (trânsito de ponta, tempo na paragem, rotunda, semáforo ou
atraso fixo) pelos sinais que os dados permitem ver; (4) o tipo dá a medida: corredor BUS só onde o problema é trânsito de ponta
e o OSM indica ≥ 2 faixas por sentido; (5) o ganho de um corredor estima-se com a velocidade dos troços que já têm corredor.
Dados que NÃO temos: contagens de carros, passageiros, largura real da rua, estacionamento; por isso o custo para o resto do
trânsito fica «sem dados».
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

from velocidade import geo, trocos

MIN_ESTAB, MIN_LEIT, MIN_LINHAS, MIN_DIAS, MIN_EXT_M = 0.75, 50, 2, 3, 300.0
RACIO_FIXO = 0.7          # velocidade na ponta ÷ fora da ponta: ≥ 0,7 = lenta o dia todo (atraso fixo), < 0,7 = trânsito de ponta
PARAGEM_PCT = 0.5         # ≥ 50 % das leituras paradas ficam a < 40 m de uma paragem = tempo na paragem
SEMAFORO_M = 30.0
DIAS_PARA_ALTA = 10       # «confiança alta» só com ≥ 10 dias úteis típicos
MAX_ZONAS = 15
PERIODOS = {"am": (7, 9), "pm": (17, 19)}
RESTO = (10, 15)
SEMAFOROS = "semaforos_cmp.geojson"   # Câmara do Porto, dados abertos (CC0): dadosabertos.cm-porto.pt/dataset/sistema-de-gestao-de-trafego-semaforos


def faixas_sentido(tags: dict, d: int):
    """Faixas por sentido segundo o OSM (None se desconhecido). Em vias de dois sentidos sem `lanes:forward/backward`, o total ÷ 2."""
    def num(s):
        try:
            return float(str(s).split(";")[0])
        except ValueError:
            return None
    if d == 1 and "lanes:forward" in tags:
        return num(tags["lanes:forward"])
    if d == -1 and "lanes:backward" in tags:
        return num(tags["lanes:backward"])
    n = num(tags["lanes"]) if "lanes" in tags else None
    if n is None:
        return None
    return n if tags.get("oneway") in ("yes", "-1", "true", "1") or tags.get("junction") == "roundabout" else n / 2


def tipo_zona(racio, pct_paragem, rotunda: bool, semaforos: int) -> str:
    """Tipo provável do bloqueio (hipótese). A ordem importa: paragem > rotunda > lenta o dia todo > trânsito de ponta."""
    if pct_paragem is not None and pct_paragem >= PARAGEM_PCT:
        return "paragem"
    if rotunda:
        return "rotunda"
    if racio is not None and racio >= RACIO_FIXO:
        return "semaforo" if semaforos > 0 else "fixo"
    return "transito"


def medida_zona(tipo: str, com_frac: float, faixas) -> tuple[str, str]:
    """(código, texto) da medida proposta."""
    if tipo == "transito":
        if com_frac >= 0.5:
            return "ja_tem", "Já tem corredor e continua lento na ponta: ver o cumprimento e os cruzamentos"
        if faixas is None:
            return "corredor_verificar", "Corredor BUS: por verificar (o OSM não diz quantas faixas tem)"
        if faixas >= 2:
            return "corredor", "Corredor BUS"
        return "sem_espaco", "Uma só faixa por sentido: sem espaço para corredor; ver prioridade semafórica e estacionamento"
    return {"paragem": ("paragem", "Rever a paragem (baia ou paragem fora da faixa)"),
            "rotunda": ("rotunda", "Rever a rotunda (prioridade ao autocarro)"),
            "semaforo": ("semaforo", "Prioridade semafórica ou avanço do autocarro no semáforo"),
            "fixo": ("fixo", "Atraso o dia todo sem causa visível nos dados: ver no local")}[tipo]


def ganho_min_h(linhas: list, alvo_kmh: float, cap_kmh) -> float:
    """Minutos de autocarro poupados por hora: Σ ph × comp × (1/v − 1/v_alvo). `linhas` = [(comp_m, v_kmh, ph)].
    O alvo nunca passa a velocidade do próprio troço fora da ponta (`cap_kmh`)."""
    vt = min(alvo_kmh, cap_kmh) if cap_kmh else alvo_kmh
    tot = 0.0
    for comp, v, ph in linhas:
        v = max(v, 2.0)
        if vt > v:
            tot += ph * (comp / (v / 3.6) - comp / (vt / 3.6)) / 60
    return tot


def confianca(dias_uteis: int, dias_crit: int, dias_obs: int, linhas: int, n: int) -> str:
    if dias_uteis >= DIAS_PARA_ALTA and dias_crit == dias_obs and linhas >= 3 and n >= 200:
        return "alta"
    return "média" if dias_obs >= 3 and dias_crit / max(1, dias_obs) >= MIN_ESTAB and linhas >= MIN_LINHAS and n >= 100 else "baixa"


def _tags_vias(pasta_osm: Path) -> dict:
    f = pasta_osm / "rotas.json"
    if not f.exists():
        return {}
    return {e["id"]: e.get("tags", {}) for e in json.loads(f.read_text(encoding="utf-8")).get("elements", []) if e.get("type") == "way"}


def _semaforos(caminho: Path):
    if not caminho.exists():
        return None
    fs = [f for f in json.loads(caminho.read_text(encoding="utf-8"))["features"] if f.get("geometry")]
    xy = geo.xy([f["geometry"]["coordinates"][0] for f in fs], [f["geometry"]["coordinates"][1] for f in fs])
    inst = np.array([f["properties"].get("traffic_signal_installation_number") for f in fs])
    return shapely.STRtree(shapely.points(xy)), inst


def _componente(semente: str, ids: list, t: pd.DataFrame) -> list:
    """Troços da zona ligados à semente por nós partilhados (a zona tem de ser contínua)."""
    no_de = {i: t.nos[i] for i in ids}
    comp, fila = {semente}, [semente]
    while fila:
        a = fila.pop()
        for b in ids:
            if b not in comp and no_de[a] & no_de[b]:
                comp.add(b)
                fila.append(b)
    return sorted(comp)


def calcular(ub: pd.DataFrame, t: pd.DataFrame, info: pd.DataFrame, pasta_dados: Path, aneis_km: list) -> dict:
    """`ub`: leituras coladas (dias típicos), `info`: grupo/f_com/perto/km por troço (de `agregar._classificar_corredores`)."""
    x = ub[(ub.tipo_dia == "util") & ub.troco_id.notna()]
    mov = x[~x.espera]
    dias_uteis = int(x.dia.nunique())
    ag, por_dia, nlin = {}, {}, {}
    for p, (h0, h1) in PERIODOS.items():
        ag[p] = trocos.agregar(ub, t, p, "util")
        y = mov[mov.hora.between(h0, h1)]
        g = y.groupby(["troco_id", "dir", "dia"]).kmh.agg(["mean", "size"]).reset_index()
        por_dia[p] = g[g["size"] >= 5]
        nlin[p] = y.groupby(["troco_id", "dir"]).linha.nunique().rename("nlinhas")
    rob = []
    for p, a in ag.items():
        c = trocos.criticos(a)
        g = por_dia[p].assign(c=lambda d: d["mean"] < trocos.LIMIAR_KMH)
        est = g.groupby(["troco_id", "dir"]).c.agg(dias_obs="size", dias_crit="sum").reset_index()
        c = c.merge(est, on=["troco_id", "dir"]).merge(nlin[p].reset_index(), on=["troco_id", "dir"]).assign(per=p)
        c = c[(c.dias_obs >= MIN_DIAS) & (c.dias_crit >= MIN_ESTAB * c.dias_obs) & (c.n >= MIN_LEIT) & (c.nlinhas >= MIN_LINHAS)]
        rob.append(c)
    rob = pd.concat(rob, ignore_index=True)
    if rob.empty:
        return {"zonas": [], "dias_uteis": dias_uteis}
    tags = _tags_vias(Path(pasta_dados) / "osm")
    sem = _semaforos(Path(pasta_dados) / SEMAFOROS)
    pool = {p: ag[p].join(info[["grupo", "km"]], on="troco_id").query("grupo == 'com'") for p in ag}
    zonas = []
    for z in trocos.marcadores(rob[["troco_id", "dir", "perdido", "v"]], t, maximo=MAX_ZONAS * 3):
        sem_id = max(z["troco_ids"], key=lambda i: rob[rob.troco_id == i].perdido.sum())
        ids = _componente(sem_id, z["troco_ids"], t)
        ext = float(t.comprimento_m[ids].sum())
        if ext < MIN_EXT_M:
            continue
        rz = rob[rob.troco_id.isin(ids)]
        p = rz.groupby("per").perdido.sum().idxmax()
        rp = rz[rz.per == p]
        h0, h1 = PERIODOS[p]
        v_pont = float(np.average(rp.v, weights=rp.n))
        pares = set(zip(rp.troco_id, rp.dir))
        base = x[x.troco_id.isin(ids)]
        resto = mov[mov.troco_id.isin(ids) & mov.hora.between(*RESTO)]
        resto = resto[[(a, b) in pares for a, b in zip(resto.troco_id, resto.dir)]]
        v_resto = float(resto.kmh.mean()) if len(resto) >= 30 else None
        parados = base[base.hora.between(h0, h1) & (base.kmh <= 2)]
        pct_par = float(parados.esp_par.mean()) if len(parados) >= 20 and "esp_par" in parados else None
        pior = rp.loc[rp.perdido.idxmax()]
        vias = [t.way_id[i] for i in ids]
        rotunda = any(tags.get(w, {}).get("junction") == "roundabout" for w in vias)
        ni = 0
        if sem:
            ni = len({sem[1][k] for k in sem[0].query(shapely.union_all(list(t.geom[ids])), predicate="dwithin", distance=SEMAFORO_M)})
        faixas = faixas_sentido(tags.get(t.way_id[pior.troco_id], {}), int(pior.dir))
        com_frac = float((info.f_com[ids] >= 0.6).mean())
        racio = v_pont / v_resto if v_resto else None
        tipo = tipo_zona(racio, pct_par, rotunda, ni)
        cod, txt = medida_zona(tipo, com_frac, faixas)
        lins = base[base.hora.between(h0, h1)].linha.astype(str).value_counts()
        z_out = {"rua": z["rua"], "cruzamento": z["cruzamento"], "ext_m": round(ext), "per": p, "perdido": round(float(rp.perdido.sum()), 1),
                 "v": round(v_pont, 1), "v_resto": round(v_resto, 1) if v_resto else None, "racio": round(racio, 2) if racio else None,
                 "pct_paragem": round(pct_par * 100) if pct_par is not None else None, "semaforos": ni, "rotunda": rotunda,
                 "faixas": faixas, "com_frac": round(com_frac, 2), "tipo": tipo, "medida": cod, "medida_txt": txt,
                 "linhas": list(lins.index[:8]), "n_linhas": int(len(lins)), "ph": round(float(rp.ph.mean()), 1), "n": int(rp.n.sum()),
                 "dias_crit": int(pior.dias_crit), "dias_obs": int(pior.dias_obs),
                 "conf": confianca(dias_uteis, int(pior.dias_crit), int(pior.dias_obs), int(len(lins)), int(rp.n.sum())),
                 "km": round(float(info.km[ids].mean()), 1), "tracado": [[[round(a, 5), round(b, 5)] for a, b in t.latlon[i]] for i in ids],
                 "ganho": None}
        if cod in ("corredor", "corredor_verificar"):
            ring = next(((lo, hi) for lo, hi in aneis_km if lo <= z_out["km"] < hi), None)
            pl = pool[p]
            sel = pl[(pl.km >= ring[0]) & (pl.km < ring[1])] if ring else pl
            if len(sel) < 10:
                sel = pl
            if len(sel) >= 3:
                alvo = {q: float(np.percentile(sel.v, q)) for q in (25, 50, 75)}
                var = []
                for excl in [None] + sorted(por_dia[p].dia.unique()):
                    ln = []
                    for r in rp.itertuples():
                        g = por_dia[p]
                        g = g[(g.troco_id == r.troco_id) & (g.dir == r.dir)]
                        g = g if excl is None else g[g.dia != excl]
                        v = float(np.average(g["mean"], weights=g["size"])) if len(g) else r.v
                        ln.append((float(t.comprimento_m[r.troco_id]), v, float(r.ph)))
                    for q in (25, 50, 75):
                        var.append(ganho_min_h(ln, alvo[q], v_resto))
                central = var[1]
                z_out["ganho"] = {"lo": round(min(var), 1), "c": round(central, 1), "hi": round(max(var), 1), "alvo": round(alvo[50], 1),
                                  "n_corredor": int(len(sel))}
        zonas.append(z_out)
    zonas = sorted(zonas, key=lambda d: -d["perdido"])[:MAX_ZONAS]
    for i, d in enumerate(zonas, 1):
        d["rank"] = i
    cont = lambda k: sum(1 for d in zonas if d["medida"] == k)  # noqa: E731
    return {"zonas": zonas, "dias_uteis": dias_uteis, "n_robustos": int(rob.drop_duplicates(["troco_id", "dir"]).shape[0]),
            "resumo": {k: cont(k) for k in ("corredor", "corredor_verificar", "ja_tem", "sem_espaco", "semaforo", "rotunda", "paragem", "fixo")},
            "perdido_zonas": round(sum(d["perdido"] for d in zonas), 1),
            "perdido_total": round(float(sum(a.perdido.sum() for a in ag.values())), 1), "semaforos": bool(sem), "osm_tags": bool(tags)}
