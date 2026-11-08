"""Recolhe posições dos autocarros STCP (FIWARE/Orion, dados abertos do Porto).

Pede o endpoint a cada INTERVALO segundos e acrescenta a um CSV diário só as
observações novas (veículo + observationDateTime). Falhas vão para o log e
nunca se gravam como dados.

Uso: python recolher_autocarros.py --out <pasta> [--intervalo 20] [--duracao <seg>]
"""
import argparse
import csv
import gzip
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = ("https://broker.fiware.urbanplatform.portodigital.pt/v2/entities"
       "?q=vehicleType==bus&limit=1000")
CAMPOS = ["recebido_utc", "observado_utc", "veiculo", "lon", "lat",
          "velocidade", "direccao", "linha", "sentido", "viagem"]


def val(e, k):
    v = e.get(k)
    return v.get("value") if isinstance(v, dict) else None


def anot(e, prefixo):
    for a in val(e, "annotations") or []:
        if a.startswith(prefixo):
            return a[len(prefixo):]
    return ""


def linha(e, recebido):
    loc = val(e, "location") or {}
    c = loc.get("coordinates") or [None, None]
    return [recebido, val(e, "observationDateTime"), val(e, "fleetVehicleId"),
            c[0], c[1], val(e, "speed"), val(e, "heading"),
            anot(e, "stcp:route:"), anot(e, "stcp:sentido:"),
            anot(e, "stcp:nr_viagem:")]


def pedir():
    req = urllib.request.Request(URL, headers={"User-Agent": "porto-verde-mobilidade/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        dados = json.load(r)
    if not isinstance(dados, list):
        raise RuntimeError("resposta não é uma lista")
    return dados


def comprimir_antigos(pasta, hoje):
    for f in pasta.glob("posicoes_*.csv"):
        if f.stem != f"posicoes_{hoje}":
            with open(f, "rb") as a, gzip.open(f"{f}.gz", "wb") as b:
                shutil.copyfileobj(a, b)
            f.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--intervalo", type=float, default=20)
    ap.add_argument("--duracao", type=float, default=0, help="0 = para sempre")
    a = ap.parse_args()
    pasta = Path(a.out)
    pasta.mkdir(parents=True, exist_ok=True)
    visto = {}
    falhas = 0
    inicio = time.time()
    while True:
        t0 = time.time()
        agora = datetime.now(timezone.utc)
        try:
            dados = pedir()
            novos = []
            rec = agora.strftime("%Y-%m-%dT%H:%M:%SZ")
            for e in dados:
                r = linha(e, rec)
                if r[2] is None or r[1] is None:
                    continue
                if visto.get(r[2]) != r[1]:
                    visto[r[2]] = r[1]
                    novos.append(r)
            hoje = agora.strftime("%Y-%m-%d")
            f = pasta / f"posicoes_{hoje}.csv"
            novo = not f.exists()
            with open(f, "a", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                if novo:
                    w.writerow(CAMPOS)
                    comprimir_antigos(pasta, hoje)
                w.writerows(novos)
            print(f"{rec} recebidos={len(dados)} novos={len(novos)}", flush=True)
            falhas = 0
        except Exception as ex:
            falhas += 1
            print(f"{agora.isoformat()} FALHA {falhas}: {ex!r}", file=sys.stderr, flush=True)
            time.sleep(min(300, 5 * 2 ** min(falhas, 6)))
        if a.duracao and time.time() - inicio >= a.duracao:
            break
        time.sleep(max(0, a.intervalo - (time.time() - t0)))


if __name__ == "__main__":
    main()
