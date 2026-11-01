"""Repete a descarga dos PDFs pendentes de Estudos (docs/50espacos/estudos_por_descarregar.md).

Tarefa diaria de 2026-11-02 a 2026-11-06. Directo (3 tentativas com espera) e depois Wayback Machine.
Um PDF so conta se acabar em %%EOF e o tamanho nao for multiplo exacto de 1 MiB (truncagem do Wayback).
Guarda em docs/50espacos/estudos_descargas/ (gitignored) e marca [x] na lista. Exit 0 se correu; 3 sem rede.
"""

import datetime
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
LISTA = os.path.join(AQUI, "estudos_por_descarregar.md")
DEST = os.path.join(AQUI, "estudos_descargas")
LOG = r"C:\Users\quent\OneDrive\Claude\Workflows\Tarefas\logs\retry_estudos.log"
FIM = datetime.date(2026, 11, 6)
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
    "Accept": "application/pdf,*/*",
}
CTX = ssl.create_default_context()


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    linha = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), m)
    open(LOG, "a", encoding="utf-8").write(linha + "\n")
    print(linha, flush=True)


def baixa(url, destino):
    tmp = destino + ".part"
    with (
        urllib.request.urlopen(
            urllib.request.Request(url, headers=H), timeout=120, context=CTX
        ) as r,
        open(tmp, "wb") as f,
    ):
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    n = os.path.getsize(tmp)
    with open(tmp, "rb") as f:
        ini = f.read(5)
        f.seek(max(0, n - 2048))
        fim = f.read()
    if ini != b"%PDF-" or b"%%EOF" not in fim or n % (1 << 20) == 0:
        os.remove(tmp)
        raise ValueError("PDF invalido ou truncado (%d bytes)" % n)
    os.replace(tmp, destino)
    return n


def main():
    if datetime.date.today() > FIM:
        log("Fora do periodo (ate %s): nada a fazer" % FIM)
        return 0
    try:
        urllib.request.urlopen(
            urllib.request.Request("https://web.archive.org/", headers=H),
            timeout=30,
            context=CTX,
        )
    except Exception as e:
        log("ERRO: sem rede (%s)" % str(e)[:60])
        return 3
    linhas = open(LISTA, encoding="utf-8").read().split("\n")
    os.makedirs(DEST, exist_ok=True)
    feitos = pend = 0
    for i, l in enumerate(linhas):
        m = re.match(r"- \[ \] .*? — (https?://\S+)\s*$", l)
        if not m:
            continue
        url = m.group(1)
        nome = (
            urllib.parse.unquote(
                urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
            )
            or "doc.pdf"
        )
        nome = re.sub(r"[^\w.\- ()]", "_", nome)
        if not nome.lower().endswith(".pdf"):
            nome += ".pdf"
        destino = os.path.join(DEST, nome)
        ok = False
        for via, u in (
            ("directo", url),
            ("wayback", "https://web.archive.org/web/2id_/" + url),
        ):
            for espera in (0, 30, 90):
                time.sleep(espera)
                try:
                    n = baixa(u, destino)
                    log("OK %s (%s, %.1f MB)" % (nome, via, n / 1e6))
                    ok = True
                    break
                except Exception as e:
                    err = str(e)[:70]
                    if "404" in err:
                        break
            if ok:
                break
        if ok:
            linhas[i] = l.replace("- [ ]", "- [x]", 1)
            feitos += 1
        else:
            log("FALHOU %s: %s" % (nome, err))
            pend += 1
        time.sleep(5)
    open(LISTA, "w", encoding="utf-8", newline="").write("\n".join(linhas))
    log("Fim: %d obtidos, %d por obter" % (feitos, pend))
    return 0


if __name__ == "__main__":
    sys.exit(main())
