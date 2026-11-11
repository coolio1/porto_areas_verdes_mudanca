"""Agregação por troço, tempo perdido, troços críticos e marcadores."""
import numpy as np
import pandas as pd
import shapely

from . import dados, geo

V_REF_KMH = 25.0
V_MIN_KMH = 2.0
LIMIAR_KMH = 14.0
MIN_LEITURAS, MIN_VEICULOS, MIN_DIAS = 20, 3, 2
FUNDIR_M = 100.0
COLUNAS = ["troco_id", "dir", "n", "veic", "dias", "v", "ph", "perdido"]


def agregar(df: pd.DataFrame, trocos: pd.DataFrame, periodo: str, tipo_dia: str) -> pd.DataFrame:
    """Uma linha por (troço, direcção) com amostra suficiente (≥ 20 leituras, ≥ 3 veículos, ≥ 2 dias).

    `v` é a média das leituras que não são espera; as passagens/hora contam todas as leituras (esperas incluídas)
    e dividem só pelos dias que têm leituras nesse período. `perdido` = minutos de autocarro perdidos por hora.
    """
    h0, h1 = dados.PERIODOS[periodo]
    dias = dados.dias_com_dados(df, periodo, tipo_dia)
    if dias == 0:
        return pd.DataFrame(columns=COLUNAS)
    x = df[(df.tipo_dia == tipo_dia) & df.hora.between(h0, h1) & df.troco_id.notna()]
    zero = x.dir == 0  # sem direcção: conta nas duas
    x = pd.concat([x[~zero], x[zero].assign(dir=1), x[zero].assign(dir=-1)])
    passagem = x.veiculo.astype(str) + "|" + x.viagem.astype(str) + "|" + x.dia.astype(str)
    pas = passagem.groupby([x.troco_id, x.dir]).nunique().rename("passagens")
    k = x[~x.espera].groupby(["troco_id", "dir"]).agg(
        n=("kmh", "size"), veic=("veiculo", "nunique"), dias=("dia", "nunique"), v=("kmh", "mean"))
    g = k.join(pas).reset_index()
    g = g[(g.n >= MIN_LEITURAS) & (g.veic >= MIN_VEICULOS) & (g.dias >= MIN_DIAS)].copy()
    g["ph"] = g.passagens / (dias * (h1 - h0 + 1))
    comp = trocos.comprimento_m.reindex(g.troco_id).to_numpy()
    v = np.maximum(g.v.to_numpy(), V_MIN_KMH)
    atraso_s = np.maximum(0.0, comp / (v / 3.6) - comp / (V_REF_KMH / 3.6))
    g["perdido"] = g.ph * atraso_s / 60
    return g[COLUNAS].reset_index(drop=True)


def criticos(agg: pd.DataFrame, limiar: float = LIMIAR_KMH) -> pd.DataFrame:
    return agg[(agg.v < limiar) & (agg.perdido > 0)]


def marcadores(crit: pd.DataFrame, trocos: pd.DataFrame, maximo: int = 15) -> list:
    """Funde troços críticos contíguos (mesma via, índices seguidos, ou a < 100 m) num ponto e nomeia-o.

    O marcador fica a meio do pior troço do grupo; `perdido` é a soma do grupo; `cruzamento` é o nome da
    via de outra rota que partilha um nó com o pior troço (ou com os vizinhos, até 3 troços de distância).
    """
    if crit.empty:
        return []
    ids = list(dict.fromkeys(crit.troco_id))
    pai = {i: i for i in ids}

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    def unir(a, b):
        pai[raiz(a)] = raiz(b)

    por_via: dict = {}
    for i in ids:
        via, n = i.split(":")
        por_via.setdefault(via, {})[int(n)] = i
    for d in por_via.values():
        for n, i in d.items():
            if n + 1 in d:
                unir(i, d[n + 1])
    geoms = trocos.geom.reindex(ids).to_numpy()
    a, b = shapely.STRtree(geoms).query(geoms, predicate="dwithin", distance=FUNDIR_M)
    for p, q in zip(a, b):
        if p < q:
            unir(ids[p], ids[q])

    nos: dict = {}
    for tid, row in trocos[["way_id", "nome", "nos"]].iterrows():
        for no in row.nos:
            nos.setdefault(no, set()).add((row.way_id, row.nome))

    def cruzamento(tid, rua):
        via, n = tid.split(":")
        for off in (0, 1, -1, 2, -2, 3, -3):
            j = f"{via}:{int(n) + off}"
            if j not in trocos.index:
                continue
            for no in sorted(trocos.nos[j]):
                for w2, nome2 in sorted(nos.get(no, ())):
                    if str(w2) != via and nome2 and nome2 != rua:
                        return nome2
        return ""

    grupos: dict = {}
    for r in crit.itertuples():
        grupos.setdefault(raiz(r.troco_id), []).append(r)
    resultado = []
    for rows in grupos.values():
        pior = max(rows, key=lambda r: r.perdido)
        nome = trocos.nome[pior.troco_id] or next((trocos.nome[r.troco_id] for r in sorted(rows, key=lambda r: -r.perdido)
                                                   if trocos.nome[r.troco_id]), "")
        meio = trocos.geom[pior.troco_id].interpolate(0.5, normalized=True)
        resultado.append({"lat": meio.y / geo.KY, "lon": meio.x / geo.KX, "rua": nome,
                          "cruzamento": cruzamento(pior.troco_id, nome), "perdido": float(sum(r.perdido for r in rows)),
                          "v": float(pior.v), "troco_ids": sorted({r.troco_id for r in rows})})
    resultado.sort(key=lambda m: -m["perdido"])
    return resultado[:maximo]
