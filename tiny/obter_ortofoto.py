"""Obtém a ortofoto de 25 cm (DGT, 2025, CC BY 4.0) do município do Porto, por WMS.

Fonte: Direcção-Geral do Território, Ortos 2025 Portugal-Continente, camada Ortos2025-RGB
(https://geo.dgterritorio.gov.pt/wms/ortos2025). Atribuição obrigatória à DGT.

Grelha de células de 1000 m x 1000 m em EPSG:3763 (PT-TM06), cada uma pedida a 4000 x 4000 px
(0,25 m/px, a resolução nativa, sem reamostragem). Guarda em %LOCALAPPDATA%\\PortoVerdeTiny\\ortofoto\\
(fora do sync do OneDrive; ~1 GB) e um manifest.json.

Usa o curl.exe do Windows: o servidor corta as ligações TLS do Python (SSL EOF).
Idempotente (salta o que já existe) e só grava respostas HTTP 200 que sejam JPEG válido.

Uso:  python tiny/obter_ortofoto.py --teste   (só a 1.ª célula, para medir o tamanho)
      python tiny/obter_ortofoto.py           (todas as células)
      Com --irg, pede a camada Ortos2025-IRG (infravermelho) para ortofoto_irg\ (mesma grelha).
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from pyproj import Transformer

RAIZ = Path(__file__).parent
EDIFICIOS = RAIZ / "dados" / "edificios_osm.json"
IRG = "--irg" in sys.argv  # falsa cor com infravermelho (separa a vegetação sem erro)
DESTINO = Path(os.environ["LOCALAPPDATA"]) / "PortoVerdeTiny" / ("ortofoto_irg" if IRG else "ortofoto")
URL = "https://geo.dgterritorio.gov.pt/wms/ortos2025/service"
CAMADA = "Ortos2025-IRG" if IRG else "Ortos2025-RGB"
CELULA = 1000  # m
PIXEIS = 4000  # = CELULA / 0,25 m


def caixa_porto() -> tuple[int, int, int, int]:
    """Caixa do município em EPSG:3763, alinhada à grelha de 1 km."""
    d = json.loads(EDIFICIOS.read_text(encoding="utf-8"))
    lats, lons = [], []
    for e in d["elements"]:
        b = e.get("bounds")
        if b:
            lats += [b["minlat"], b["maxlat"]]
            lons += [b["minlon"], b["maxlon"]]
    t = Transformer.from_crs("EPSG:4326", "EPSG:3763", always_xy=True)
    xs, ys = [], []
    for lat in (min(lats), max(lats)):
        for lon in (min(lons), max(lons)):
            x, y = t.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    return (
        math.floor(min(xs) / CELULA) * CELULA,
        math.floor(min(ys) / CELULA) * CELULA,
        math.ceil(max(xs) / CELULA) * CELULA,
        math.ceil(max(ys) / CELULA) * CELULA,
    )


def pedir(x0: int, y0: int, destino: Path) -> int:
    """Pede uma célula; devolve o tamanho em bytes. Levanta erro se não for JPEG válido."""
    url = (
        f"{URL}?service=WMS&version=1.3.0&request=GetMap&layers={CAMADA}&styles="
        f"&crs=EPSG:3763&bbox={x0},{y0},{x0 + CELULA},{y0 + CELULA}"
        f"&width={PIXEIS}&height={PIXEIS}&format=image/jpeg"
    )
    tmp = destino.with_suffix(".tmp")
    r = subprocess.run(
        ["curl.exe", "-s", "-m", "300", "--retry", "2", "-o", str(tmp), "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    codigo = r.stdout.strip()
    if r.returncode != 0 or codigo != "200":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"({x0},{y0}) curl={r.returncode} http={codigo} {r.stderr.strip()}")
    cabeca = tmp.read_bytes()[:3]
    if cabeca != b"\xff\xd8\xff":  # o servidor devolve XML de erro com 200 por vezes
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"({x0},{y0}) resposta não é JPEG")
    tmp.replace(destino)
    return destino.stat().st_size


def main() -> int:
    teste = "--teste" in sys.argv
    x0, y0, x1, y1 = caixa_porto()
    celulas = [(x, y) for y in range(y0, y1, CELULA) for x in range(x0, x1, CELULA)]
    print(f"caixa EPSG:3763 {x0},{y0} .. {x1},{y1} | {len(celulas)} células de {CELULA} m")
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "manifest.json").write_text(
        json.dumps({"crs": "EPSG:3763", "celula_m": CELULA, "pixeis": PIXEIS,
                    "caixa": [x0, y0, x1, y1], "camada": CAMADA,
                    "fonte": "DGT Ortos 2025 25 cm, CC BY 4.0"}, indent=1),
        encoding="utf-8")
    if teste:
        celulas = celulas[len(celulas) // 2: len(celulas) // 2 + 1]  # uma célula do meio
    total = 0
    falhas = 0
    for x, y in celulas:
        f = DESTINO / f"{x}_{y}.jpg"
        if f.exists():
            total += f.stat().st_size
            continue
        try:
            total += pedir(x, y, f)
            print(f"ok {f.name} {f.stat().st_size / 1e6:.1f} MB")
        except RuntimeError as e:
            falhas += 1
            print(f"FALHOU {e}", file=sys.stderr)
    print(f"total {total / 1e6:.0f} MB | falhas {falhas} | destino {DESTINO}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
