"""Sessão autenticada no Centro de Dados da DGT (cdd.dgterritorio.gov.pt), por script.

O site usa Keycloak (OIDC, código + PKCE) e uma sessão por cookie no servidor da DGT. Replica-se o que o
browser faz: abre /auth/login, segue o redireccionamento para o formulário, submete utilizador e
palavra-passe e volta ao /auth/callback, que cria o cookie.

Credenciais: DGT_USER e DGT_PASS no .env global (C:\\Users\\quent\\OneDrive\\Claude\\.env); nunca no código,
nunca impressas.
"""
import html
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
BASE = "https://cdd.dgterritorio.gov.pt"


def sessao() -> requests.Session:
    load_dotenv(RAIZ.parent / ".env")             # global: OneDrive\Claude\.env (chaves partilhadas)
    load_dotenv(RAIZ / ".env", override=True)     # local, se existir, sobrepõe
    user, senha = os.environ.get("DGT_USER"), os.environ.get("DGT_PASS")
    if not user or not senha:
        raise SystemExit("faltam DGT_USER / DGT_PASS no .env")
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) PortoVerde-research"
    r = s.get(f"{BASE}/auth/login", timeout=60)  # segue até ao formulário do Keycloak
    r.raise_for_status()
    m = re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', r.text) or re.search(r'<form[^>]+action="([^"]+)"', r.text)
    if not m:
        raise SystemExit("formulário de login não encontrado (o Keycloak mudou?)")
    r2 = s.post(html.unescape(m.group(1)), data={"username": user, "password": senha, "credentialId": ""}, timeout=60, allow_redirects=True)
    if "kc-form-login" in r2.text or "Invalid username or password" in r2.text:
        raise SystemExit("início de sessão recusado (utilizador/palavra-passe, conta por activar ou captcha)")
    return s


if __name__ == "__main__":
    s = sessao()
    print("início de sessão: ok; cookies:", sorted({c.name for c in s.cookies}))
    r = s.post(f"{BASE}/dgt-be/v1/search", json={"collections": ["MDS-50cm"], "bbox": [-8.68, 41.14, -8.55, 41.19], "limit": 1}, timeout=60)
    f = r.json()["features"][0]
    print("pesquisa:", r.status_code, f["id"], round(f["properties"]["file:size"] / 1e6, 1), "MB")
    a = f["assets"]["data"]["href"]
    h = s.head(a, allow_redirects=False, timeout=60)
    print("ficheiro: HEAD", h.status_code, h.headers.get("content-type"), h.headers.get("content-length"),
          "-> redireccionamento para", (h.headers.get("location") or "")[:40].split("?")[0] if h.is_redirect else "-")
