"""Agregados do pacote STCP (passagens estimadas + horários) para a página «Análise».

Só agregados por linha, paragem, troço entre paragens, janela ou dia; nunca por veículo. Não usa a velocidade derivada
das posições do pacote (subestima): só atrasos face ao horário, intervalos entre autocarros e oferta programada.

Uso: python agregar_stcp.py <pasta_pacote> <saida.json> [--atipicos 2026-11-11] [--recolha <pasta>]
(colocar em Mobilidade/analise/ para que `velocidade` se importe)
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

JANELAS = ["manha", "entre_pontas", "tarde"]
MIN_VIAGENS, MIN_DIAS = 20, 2              # o mesmo mínimo de publicação do pacote (LEIA-ME)
ADIANT_S, PONTUAL_S, ATRASO5_S = -60, 180, 300
INICIO, FIM = 0.15, 0.85                   # fracção do percurso: «início» e «fim» da viagem
N_DECIS = 10
PELOTAO, BURACO = 0.5, 1.5                 # intervalo real ÷ programado
INTERVALO_MAX_S = 20 * 60                  # só serviço frequente (intervalo programado ≤ 20 min)


def _q(s, q):
    return round(float(s.quantile(q)) / 60, 2)


def _seg_locais(iso: pd.Series, datas: pd.Series) -> np.ndarray:
    """Segundos desde a meia-noite local (Europe/Lisbon) da data de serviço."""
    t = pd.to_datetime(iso, utc=True, format="ISO8601").dt.tz_convert("Europe/Lisbon")
    meia = pd.to_datetime(datas).dt.tz_localize("Europe/Lisbon")
    return (t - meia).dt.total_seconds().to_numpy()


def carregar(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p = pd.read_csv(pasta / "passagens_estimadas.csv",
                    dtype={"trip_id": str, "stop_id": str, "route_id": str, "vehicle_id": str},
                    usecols=["service_date", "trip_id", "stop_id", "route_id", "direction_id", "window",
                             "estimated_passage", "scheduled_arrival", "delay_seconds", "accepted"])
    p = p[p.accepted == 1].drop(columns="accepted")
    p["sched_s"] = np.rint(_seg_locais(p.scheduled_arrival, p.service_date)).astype(int)
    p["est_s"] = _seg_locais(p.estimated_passage, p.service_date)
    h = pd.read_csv(pasta / "horarios_aplicados.csv", dtype={"trip_id": str, "route_id": str, "stop_id": str},
                    usecols=["service_date", "trip_id", "route_id", "direction_id", "route_position", "stop_id",
                             "stop_name", "scheduled_arrival_seconds"])
    r = pd.read_csv(pasta / "horarios_referencia.csv", dtype={"route_id": str, "stop_id": str, "service_id": str},
                    usecols=["reference_date", "route_id", "direction_id", "service_id", "reference_trip_id",
                             "route_position", "stop_id", "stop_name", "latitude", "longitude", "arrival_time"])
    hh = r.arrival_time.str.split(":", expand=True).astype(int)
    r["s"] = hh[0] * 3600 + hh[1] * 60 + hh[2]
    # posição no percurso: junta pela chave do LEIA-ME (data + viagem + paragem) e confere pela hora programada
    p = p.merge(h[["service_date", "trip_id", "stop_id", "route_position", "stop_name", "scheduled_arrival_seconds"]],
                on=["service_date", "trip_id", "stop_id"], how="inner")
    p = p[p.sched_s == p.scheduled_arrival_seconds].drop(columns="scheduled_arrival_seconds")
    pmax = h.groupby(["route_id", "direction_id"]).route_position.max().rename("pos_max")
    p = p.join(pmax, on=["route_id", "direction_id"])
    p["prog"] = (p.route_position - 1) / (p.pos_max - 1)
    return p, h, r


def _classes(d: pd.Series) -> dict:
    n = len(d)
    return {"n": int(n), "med": round(float(d.median()) / 60, 2),
            "adiant": round(float((d < ADIANT_S).mean() * 100), 1),
            "pontual": round(float(d.between(ADIANT_S, PONTUAL_S).mean() * 100), 1),
            "a3_5": round(float(((d > PONTUAL_S) & (d <= ATRASO5_S)).mean() * 100), 1),
            "a5": round(float((d > ATRASO5_S).mean() * 100), 1)}


def por_dia(p: pd.DataFrame) -> list:
    """Pontualidade por dia e janela (todos os dias, incluindo os atípicos), com a mediana por viagem."""
    out = []
    for (d, j), s in p.groupby(["service_date", "window"]):
        v = s.groupby("trip_id").delay_seconds.mean()
        out.append({"d": d, "j": j, "viag": int(len(v)), "med_viag": round(float(v.median()) / 60, 2), **_classes(s.delay_seconds)})
    return out


def progresso(p: pd.DataFrame) -> dict:
    """Atraso pela fracção do percurso (decis), por janela: nasce no terminal ou acumula-se na rua?"""
    p = p.assign(dec=np.minimum((p.prog * N_DECIS).astype(int), N_DECIS - 1))
    out = {}
    for j in JANELAS + ["todas"]:
        s = p if j == "todas" else p[p.window == j]
        out[j] = [{"dec": int(k), "n": int(len(g)), "viag": int(g.trip_id.nunique()), "p10": _q(g.delay_seconds, .1),
                   "p25": _q(g.delay_seconds, .25), "med": _q(g.delay_seconds, .5), "p75": _q(g.delay_seconds, .75),
                   "p90": _q(g.delay_seconds, .9), "a5": round(float((g.delay_seconds > ATRASO5_S).mean() * 100), 1)}
                  for k, g in s.groupby("dec")]
    return out


def linhas(p: pd.DataFrame) -> list:
    """Por linha: atraso no início e no fim da viagem (slope chart) e % de viagens a chegar > 5 min atrasadas."""
    ini = p[p.prog <= INICIO].sort_values("prog").groupby(["service_date", "trip_id"]).first()
    fim = p[p.prog >= FIM].sort_values("prog").groupby(["service_date", "trip_id"]).last()
    v = ini[["route_id", "window", "delay_seconds"]].rename(columns={"delay_seconds": "ini"}).join(
        fim[["delay_seconds"]].rename(columns={"delay_seconds": "fim"}), how="inner").reset_index()
    out = []
    for lin, s in v.groupby("route_id"):
        if len(s) < MIN_VIAGENS or s.service_date.nunique() < MIN_DIAS:
            continue
        ganho = s.fim - s.ini
        out.append({"l": str(lin), "viag": int(len(s)), "dias": int(s.service_date.nunique()),
                    "ini": round(float(s.ini.median()) / 60, 2), "fim": round(float(s.fim.median()) / 60, 2),
                    "ganho": round(float(ganho.median()) / 60, 2), "ganho_p25": _q(ganho, .25), "ganho_p75": _q(ganho, .75),
                    "fim5": round(float((s.fim > ATRASO5_S).mean() * 100), 1),
                    "ini_adiant": round(float((s.ini < ADIANT_S).mean() * 100), 1),
                    **{f"fim_{j}": (round(float(s[s.window == j].fim.median()) / 60, 2) if (s.window == j).sum() >= MIN_VIAGENS else None)
                       for j in JANELAS}})
    return sorted(out, key=lambda d: -d["ganho"])


def acumulacao(p: pd.DataFrame, r: pd.DataFrame, top: int = 20) -> dict:
    """Troços entre paragens fisicamente consecutivas (mesma viagem): quanto atraso se ganha (ou recupera) em cada um."""
    q = p.sort_values(["service_date", "trip_id", "route_position"])
    nxt = q.groupby(["service_date", "trip_id"]).shift(-1)
    ok = nxt.route_position == q.route_position + 1
    s = pd.DataFrame({"a": q.stop_id[ok], "b": nxt.stop_id[ok], "linha": q.route_id[ok], "dia": q.service_date[ok],
                      "viagem": q.trip_id[ok], "janela": q.window[ok],
                      "delta": (nxt.delay_seconds - q.delay_seconds)[ok],
                      "prog_s": (nxt.sched_s - q.sched_s)[ok]})
    coords = r.drop_duplicates("stop_id").set_index("stop_id")[["stop_name", "latitude", "longitude"]]
    g = s.groupby(["a", "b"]).agg(n=("viagem", "size"), dias=("dia", "nunique"), med=("delta", "median"),
                                  p25=("delta", lambda x: x.quantile(.25)), p75=("delta", lambda x: x.quantile(.75)),
                                  prog=("prog_s", "median"), linhas=("linha", lambda x: sorted(set(x))))
    # tempos intermédios do horário são reconstruídos (85 % «inferred»): só troços com tempo programado ≥ 20 s
    g = g[(g.n >= MIN_VIAGENS) & (g.dias >= MIN_DIAS) & (g.prog >= 20)].reset_index()
    g = g.join(coords.add_prefix("a_"), on="a").join(coords.add_prefix("b_"), on="b")
    g["dist_m"] = np.hypot((g.b_longitude - g.a_longitude) * 111320 * math.cos(math.radians(41.15)),
                           (g.b_latitude - g.a_latitude) * 111320)

    def fmt(df):
        return [{"de": x.a_stop_name, "para": x.b_stop_name, "linhas": x.linhas[:8], "n": int(x.n), "dias": int(x.dias),
                 "med_s": round(float(x.med)), "p25_s": round(float(x.p25)), "p75_s": round(float(x.p75)),
                 "prog_s": round(float(x.prog)), "dist_m": round(float(x.dist_m)),
                 "lat": round(float((x.a_latitude + x.b_latitude) / 2), 5), "lon": round(float((x.a_longitude + x.b_longitude) / 2), 5)}
                for x in df.itertuples()]
    soma = s.delta.sum()
    pos = g.med.clip(lower=0).sort_values(ascending=False).to_numpy()
    return {"pares": int(len(s)), "trocos": int(len(g)), "media_s": round(float(s.delta.mean()), 1),
            "frac_troco_positivo": round(float((g.med > 0).mean() * 100), 1),
            # robusto: no top só entram troços onde até o 1.º quartil ganha atraso (ou, nos que recuperam, o 3.º perde)
            "top_ganho": fmt(g[g.p25 > 0].sort_values("med", ascending=False).head(top)),
            "top_recupera": fmt(g[g.p75 < 0].sort_values("med").head(top // 2)),
            "concentracao": {"n": int(len(pos)), "top10pct": round(float(pos[: max(1, len(pos) // 10)].sum() / max(1e-9, pos.sum()) * 100), 1)},
            "_soma_s": float(soma)}


def pelotoes(p: pd.DataFrame, r: pd.DataFrame) -> dict:
    """Intervalo real entre autocarros seguidos da mesma linha/sentido numa paragem ÷ intervalo programado.

    Só pares consecutivos também no horário de referência (dia útil: nenhum autocarro programado entre os dois), em
    serviço frequente (≤ 20 min), na mesma janela. Pelotão = < 0,5 do programado; buraco = > 1,5.
    """
    util = r[r.service_id.str.startswith("UTIL")]
    ref = {k: np.sort(g.s.to_numpy()) for k, g in util.groupby(["route_id", "direction_id", "stop_id"])}
    q = p.sort_values(["service_date", "route_id", "direction_id", "stop_id", "est_s"])
    k = ["service_date", "route_id", "direction_id", "stop_id", "window"]
    nxt = q.groupby(k).shift(-1)
    m = nxt.est_s.notna()
    d = pd.DataFrame({"l": q.route_id[m], "dirc": q.direction_id[m], "stop": q.stop_id[m], "dia": q.service_date[m],
                      "j": q.window[m], "prog": q.prog[m], "s0": q.sched_s[m], "s1": nxt.sched_s[m].astype(int),
                      "h_obs": (nxt.est_s - q.est_s)[m]})
    d["h_prog"] = d.s1 - d.s0
    d = d[(d.h_prog > 0) & (d.h_prog <= INTERVALO_MAX_S)]
    entre = np.zeros(len(d), dtype=int)
    for i, (key, idx) in enumerate(d.groupby(["l", "dirc", "stop"]).indices.items()):
        arr = ref.get(key)
        if arr is None:
            entre[idx] = -1
            continue
        s0, s1 = d.s0.to_numpy()[idx] % 86400, d.s1.to_numpy()[idx] % 86400
        entre[idx] = np.searchsorted(arr, s1, "left") - np.searchsorted(arr, s0, "right")
    d = d[entre == 0].copy()
    d["rz"] = d.h_obs / d.h_prog

    def resumo(s):
        return {"pares": int(len(s)), "pelotao": round(float((s.rz < PELOTAO).mean() * 100), 1),
                "buraco": round(float((s.rz > BURACO).mean() * 100), 1),
                "cv": round(float(((s.h_obs - s.h_prog) / s.h_prog).std()), 3)}

    dec = np.minimum((d.prog * N_DECIS).astype(int), N_DECIS - 1)
    por_l = []
    for (lin), s in d.groupby("l"):
        if len(s) >= 100 and s.dia.nunique() >= MIN_DIAS:
            por_l.append({"l": str(lin), "h_prog_min": round(float(s.h_prog.median()) / 60, 1), **resumo(s)})
    hist, _ = np.histogram(np.clip(d.rz, 0, 3), bins=np.arange(0, 3.01, 0.1))
    return {"total": resumo(d), "por_janela": {j: resumo(s) for j, s in d.groupby("j")},
            "por_decil": [{"dec": int(k), **resumo(s)} for k, s in d.groupby(dec)],
            "linhas": sorted(por_l, key=lambda x: -x["pelotao"]),
            "hist_razao": {"bins": [round(x, 1) for x in np.arange(0, 3.01, 0.1)], "c": hist.tolist()}}


def oferta(r: pd.DataFrame) -> dict:
    """Viagens programadas por hora de partida (1.ª paragem) nos três tipos de dia de referência, e por linha (útil)."""
    ini = r.sort_values("route_position").groupby(["reference_date", "reference_trip_id"]).first()
    ini["h"] = (ini.s // 3600) % 24
    ini["tipo"] = ini.service_id.str.split(r"[ :|]", regex=True).str[0].map({"UTIL": "util", "SABADO": "sab", "DOM": "dom"})
    out = {}
    for tipo, s in ini.groupby("tipo"):
        c = s.groupby("h").size()
        out[tipo] = {"data": s.index.get_level_values(0)[0], "viagens": int(len(s)), "linhas": int(s.route_id.nunique()),
                     "por_hora": [int(c.get(h, 0)) for h in range(24)]}
    u = ini[ini.tipo == "util"]
    out["util_linha"] = {str(lin): [int(x) for x in s.groupby("h").size().reindex(range(24), fill_value=0)]
                         for lin, s in u.groupby("route_id")}
    # duração programada da viagem (1.ª → última paragem) por hora de partida: o horário já conta com a ponta?
    fim = r.sort_values("route_position").groupby(["reference_date", "reference_trip_id"]).last()
    dur = (fim.s - ini.s).rename("dur")
    u2 = ini.join(dur)[lambda x: x.tipo == "util"].reset_index()
    base = u2[u2.h.between(10, 15)].groupby(["route_id", "direction_id"]).dur.median().rename("base")
    u2 = u2.join(base, on=["route_id", "direction_id"])
    u2["rel"] = u2.dur / u2.base
    out["dur_prog_rel_hora"] = [round(float(u2[u2.h == h].rel.median()), 3) if (u2.h == h).sum() >= 30 else None for h in range(24)]
    return out


# ---------- recolha própria × horário de referência (dia útil de 26 Out) ----------
CHAVE_RE = r"\|\d+\|"                 # «200_0_1|333|D1|T18|N7» → «200_0_1|D1|T18|N7» (o 2.º campo muda de versão)
COBERTURA_MIN = 0.7                      # leituras por minuto de viagem (a cadência é ~1/min)


def _viagens_recolha(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (dia, viagem, veículo) da recolha própria: início, fim, leituras, distância percorrida."""
    import math as _m
    kx, ky = 111320.0 * _m.cos(_m.radians(41.15)), 111320.0
    d = df.sort_values(["veiculo", "obs"])
    d = d.assign(ds=d.dia.astype(str))
    k = ["ds", "linha", "viagem", "veiculo"]
    g = d.groupby(k)
    d["dd"] = np.hypot(g.lon.diff() * kx, g.lat.diff() * ky)
    t = d.groupby(k).agg(t0=("obs", "min"), t1=("obs", "max"), n=("obs", "size"), dist=("dd", "sum")).reset_index()
    t["dur"] = (t.t1 - t.t0).dt.total_seconds() / 60
    t["key"] = t.viagem.str.replace(CHAVE_RE, "|", regex=True)
    return t


def _ref_viagens(r: pd.DataFrame) -> pd.DataFrame:
    u = r[r.service_id.str.startswith("UTIL")].sort_values("route_position")
    v = u.groupby("reference_trip_id").agg(l=("route_id", "first"), s0=("s", "first"), s1=("s", "last")).reset_index()
    v["key"] = v.reference_trip_id.str.replace(CHAVE_RE, "|", regex=True)
    v["h"] = (v.s0 // 3600) % 24
    return v


def realizacao(t: pd.DataFrame, ref: pd.DataFrame, dias: list[str]) -> dict:
    """Fracção das viagens programadas (dia útil) que aparecem no GPS, por hora de partida programada.

    Limite inferior do serviço prestado: uma viagem feita por um autocarro sem GPS, ou com outro identificador, conta
    como «não vista». Não se publica por linha (identificadores mudam com alterações de percurso).
    """
    vistas = {d: set(t[t.ds == d].key) for d in dias}
    ref = ref.assign(**{d: ref.key.isin(vistas[d]) for d in dias})
    ref["real"] = ref[dias].mean(axis=1)
    hh = ref.groupby("h").agg(prog=("key", "size"), real=("real", "mean"))
    por_dia = {d: round(float(ref[d].mean() * 100), 1) for d in dias}
    sem_par = {d: round(float((~t[t.ds == d].key.isin(set(ref.key))).mean() * 100), 1) for d in dias}
    return {"dias": dias, "por_dia": por_dia, "obs_sem_par_pct": sem_par,
            "por_hora": [{"h": int(h), "prog": int(x.prog), "vistas_pct": round(float(x.real * 100), 1)} for h, x in hh.iterrows()]}


def duracao_vs_horario(t: pd.DataFrame, ref: pd.DataFrame, dias: list[str], atipicos: list[str]) -> dict:
    """Duração real ÷ programada da MESMA viagem (chave sem versão), por hora de partida programada e por linha."""
    v = t.merge(ref[["key", "s0", "s1"]], on="key")
    v["dur_prog"] = (v.s1 - v.s0) / 60
    v = v[(v.dur > 10) & (v.n >= COBERTURA_MIN * v.dur) & (v.dur_prog > 10)].copy()
    v["rz"] = v.dur / v.dur_prog
    v["hp"] = (v.s0 // 3600) % 24
    v["vc"] = v.dist / 1000 / (v.dur / 60)                      # velocidade comercial (paragens incluídas)
    norm = v[v.ds.isin(dias)]

    def q(s):
        return {"n": int(len(s)), "med": round(float(s.median()), 3), "p25": round(float(s.quantile(.25)), 3),
                "p75": round(float(s.quantile(.75)), 3)}
    hora = [{"h": int(h), **q(s.rz)} for h, s in norm.groupby("hp") if len(s) >= 50]
    dia_hora = {d: {int(h): round(float(s.rz.median()), 3) for h, s in v[v.ds == d].groupby("hp") if len(s) >= 20}
                for d in sorted(set(dias) | set(atipicos))}
    pk = norm[norm.hp.between(7, 19)]
    lin = []
    for l, s in pk.groupby("linha"):
        if len(s) >= 40 and s.ds.nunique() >= MIN_DIAS:
            lin.append({"l": str(l), "n": int(len(s)), "dias": int(s.ds.nunique()), "rz_med": round(float(s.rz.median()), 3),
                        "rz_p10": round(float(s.rz.quantile(.1)), 3), "rz_p90": round(float(s.rz.quantile(.9)), 3),
                        "vc": round(float(s.dist.sum() / 1000 / (s.dur.sum() / 60)), 1)})
    return {"dias": dias, "por_hora": hora, "por_dia_hora": dia_hora, "linhas": lin}


def calcular_recolha(pasta_recolha: Path, r: pd.DataFrame, dias: list[str], atipicos: list[str]) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from velocidade import dados                                   # noqa: E402  (Mobilidade/velocidade)
    t = _viagens_recolha(dados.carregar(pasta_recolha))
    ref = _ref_viagens(r)
    return {"realizacao": realizacao(t, ref, dias), "duracao": duracao_vs_horario(t, ref, dias, atipicos)}


def calcular(pasta: Path, atipicos: set[str]) -> dict:
    p, h, r = carregar(pasta)
    tip = p[~p.service_date.isin(atipicos)]
    out = {"fonte": "STCP (horários) e Associação Porto Digital (GPS); passagens estimadas pelo projecto do pacote",
           "dias": sorted(p.service_date.unique().tolist()), "atipicos": sorted(atipicos),
           "passagens": int(len(p)), "viagens": int(p.groupby(["service_date", "trip_id"]).ngroups),
           "linhas_n": int(p.route_id.nunique()),
           "classes_janela": {j: _classes(s.delay_seconds) for j, s in tip.groupby("window")},
           "classes_total": _classes(tip.delay_seconds),
           "por_dia": por_dia(p), "progresso": progresso(tip), "linhas": linhas(tip),
           "acumula": acumulacao(tip, r), "pelotoes": pelotoes(tip, r), "oferta": oferta(r)}
    out["acumula"].pop("_soma_s")
    out["_r"] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--atipicos", nargs="*", default=["2026-11-11"])
    ap.add_argument("--recolha", type=Path, help="pasta posicoes_*.csv[.gz] da recolha própria")
    ap.add_argument("--dias-recolha", nargs="*", default=["2026-11-09", "2026-11-10", "2026-11-12"],
                    help="dias úteis completos e normais para a realização (o 13 está incompleto)")
    a = ap.parse_args()
    res = calcular(a.pasta, set(a.atipicos))
    r = res.pop("_r")
    if a.recolha:
        res["recolha_x_horario"] = calcular_recolha(a.recolha, r, a.dias_recolha, a.atipicos)
    a.saida.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{a.saida}: {a.saida.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
