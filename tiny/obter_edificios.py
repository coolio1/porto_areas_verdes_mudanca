"""Obtém os edifícios do município do Porto (OSM, via Overpass) para tiny/dados/edificios_osm.json.

Fonte: OpenStreetMap contributors, ODbL. O OSM é a autoridade da geometria dos edifícios:
em discrepância com a ortofoto, vale o OSM.

Só grava se a resposta for 200 e tiver o mínimo esperado de elementos (nunca cacheia falhas).
Idempotente: se o ficheiro existir, não volta a descarregar (`--refazer` substitui-o, atómico).
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).parent / "dados" / "edificios_osm.json"
MINIMO = 40000  # a contagem de 2026-11-09 foi 43 588
URL = "https://overpass-api.de/api/interpreter"
QUERY = (
    '[out:json][timeout:180];'
    'area["boundary"="administrative"]["name"="Porto"]["admin_level"="7"]->.a;'
    '(way["building"](area.a);relation["building"](area.a););'
    'out geom;'  # "out geom tags" tira os membros das relações (edifícios com pátio)
)


def obter() -> dict:
    corpo = urllib.parse.urlencode({"data": QUERY}).encode()
    pedido = urllib.request.Request(
        URL, data=corpo, headers={"User-Agent": "porto-verde-tiny/0.1", "Accept": "*/*"}
    )
    for tentativa in range(1, 4):
        try:
            with urllib.request.urlopen(pedido, timeout=240) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return json.loads(r.read())
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError) as e:
            print(f"tentativa {tentativa}/3 falhou: {e!r}", file=sys.stderr)
            if tentativa == 3:
                raise
            time.sleep(20 * tentativa)


def main() -> int:
    if DESTINO.exists() and "--refazer" not in sys.argv:
        print(f"já existe: {DESTINO} (usar --refazer para substituir)")
        return 0
    dados = obter()
    elementos = dados.get("elements", [])
    n = len(elementos)
    if n < MINIMO:
        print(f"resposta incompleta: {n} elementos (< {MINIMO}); nada gravado", file=sys.stderr)
        return 1
    sem_membros = sum(1 for e in elementos if e["type"] == "relation" and not e.get("members"))
    if sem_membros:
        print(f"{sem_membros} relações sem membros; nada gravado", file=sys.stderr)
        return 1
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    tmp = DESTINO.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DESTINO)
    print(f"gravado: {DESTINO} | {n} elementos | {DESTINO.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
