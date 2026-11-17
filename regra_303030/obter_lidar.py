"""Fase 0 do 3-30-300: descarrega folhas LiDAR (MDS/MDT 50 cm) do Centro de Dados da DGT (CC BY 4.0).

Uso:
  python obter_lidar.py --teste                 uma folha MDS sobre o Porto (verificar formato antes das 214)
  python obter_lidar.py --colecao MDS-50cm      todas as folhas da colecção que cruzam o concelho (pede sim ao utilizador!)

Destino: PV_LIDAR_DADOS (por omissão %LOCALAPPDATA%\\PortoVerde\\regra\\lidar). Idempotente: não repete
ficheiros completos (tamanho = file:size do catálogo); grava em .part e renomeia no fim.
Credenciais: DGT_USER/DGT_PASS no .env global (ver dgt_sessao.py).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dgt_sessao import BASE, sessao  # noqa: E402

DESTINO = Path(os.environ.get("PV_LIDAR_DADOS", Path(os.environ["LOCALAPPDATA"]) / "PortoVerde" / "regra" / "lidar"))
BBOX_PORTO = [-8.68, 41.14, -8.55, 41.19]


def procurar(s, colecao, limite):
    r = s.post(f"{BASE}/dgt-be/v1/search", json={"collections": [colecao], "bbox": BBOX_PORTO, "limit": limite}, timeout=60)
    r.raise_for_status()
    return r.json()["features"]


def descarregar(s, item, destino=DESTINO):
    destino.mkdir(parents=True, exist_ok=True)
    href = item["assets"]["data"]["href"]
    esperado = int(item["properties"]["file:size"])
    nome = item["id"] + ".tif"  # o href não traz extensão; são GeoTIFF (verificado)
    f = destino / nome
    if f.exists() and f.stat().st_size == esperado:
        print("já existe:", nome)
        return f
    parcial = f.with_name(nome + ".part")
    with s.get(href, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(parcial, "wb") as out:
            for bloco in r.iter_content(1 << 20):
                out.write(bloco)
    if parcial.stat().st_size != esperado:
        raise SystemExit(f"{nome}: tamanho {parcial.stat().st_size} ≠ catálogo {esperado}; ficheiro parcial mantido")
    parcial.replace(f)
    print("ok:", nome, round(esperado / 1e6, 1), "MB ->", f)
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--colecao")
    a = ap.parse_args()
    s = sessao()
    if a.teste:
        descarregar(s, procurar(s, "MDS-50cm", 1)[0])
    elif a.colecao:
        for it in procurar(s, a.colecao, 500):
            descarregar(s, it)
    else:
        ap.error("--teste ou --colecao")
