#!/usr/bin/env python3
"""
patch_nav.py — garante que todas as páginas HTML têm a nav canónica de nav.py.

Uso manual:    python patch_nav.py
Pre-commit:    python patch_nav.py --check   (sai com erro se houver divergência)
Instalar hook: python patch_nav.py --install
"""

import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from nav import get_nav, get_jekyll_nav, get_footer_logo

# (ficheiro relativo à raiz, canonical_path, depth)
TARGETS = [
    ("mapa/mapa.html",                                 "mapa/mapa.html",                                1),
    ("ndvi_historico/ndvi_historico.html",             "ndvi_historico/ndvi_historico.html",            1),
    ("interiores/interiores_quarteiroes.html",         "interiores/interiores_quarteiroes.html",        1),
    ("acessibilidade/acessibilidade_verde.html",       "acessibilidade/acessibilidade_verde.html",      1),
    ("acessibilidade/conversao_verde.html",            "acessibilidade/conversao_verde.html",           1),
    ("atropelamentos/dashboard_atropelamentos.html",   "atropelamentos/dashboard_atropelamentos.html",  1),
    ("1947/orto_1947.html",                            "1947/orto_1947.html",                           1),
]

NAV_RE    = re.compile(r'<div id="nav"[^>]*>.*?</div>', re.DOTALL)
FOOTER_RE = re.compile(r'<div id="footer-logo"[^>]*>.*?</div>', re.DOTALL)

CHECK_ONLY = "--check" in sys.argv
INSTALL    = "--install" in sys.argv

if INSTALL:
    hook_path = os.path.join(ROOT, ".git", "hooks", "pre-commit")
    hook_body = f'#!/bin/sh\npython "{os.path.join(ROOT, "patch_nav.py")}"\n'
    with open(hook_path, "w") as f:
        f.write(hook_body)
    # chmod +x em Unix/Git Bash
    try:
        os.chmod(hook_path, 0o755)
    except Exception:
        pass
    print(f"[ok] pre-commit hook instalado em {hook_path}")
    sys.exit(0)

errors = 0
patched = []

for rel_path, canonical, depth in TARGETS:
    full_path = os.path.join(ROOT, rel_path)
    if not os.path.exists(full_path):
        continue

    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    new_content = content
    changed = False

    # --- nav ---
    expected_nav = get_nav(canonical, depth)
    if expected_nav not in new_content:
        if not NAV_RE.search(new_content):
            print(f"AVISO: <div id=\"nav\"> não encontrada em {rel_path}", file=sys.stderr)
            errors += 1
            continue
        if CHECK_ONLY:
            print(f"[divergência nav] {rel_path}", file=sys.stderr)
            errors += 1
            continue
        new_content = NAV_RE.sub(expected_nav, new_content, count=1)
        changed = True

    # --- footer-logo ---
    expected_footer = get_footer_logo(depth)
    if expected_footer not in new_content:
        if CHECK_ONLY:
            print(f"[divergência footer-logo] {rel_path}", file=sys.stderr)
            errors += 1
            continue
        if FOOTER_RE.search(new_content):
            new_content = FOOTER_RE.sub(expected_footer, new_content, count=1)
        else:
            new_content = new_content.replace('</body>', expected_footer + '\n</body>', 1)
        changed = True

    if changed:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        patched.append(rel_path)
        os.system(f'git -C "{ROOT}" add "{full_path}"')

# Regenerar _includes/nav.html para Jekyll
includes_dir = os.path.join(ROOT, "_includes")
os.makedirs(includes_dir, exist_ok=True)
jekyll_nav_path = os.path.join(includes_dir, "nav.html")
expected_jekyll = get_jekyll_nav() + "\n"

current_jekyll = ""
if os.path.exists(jekyll_nav_path):
    with open(jekyll_nav_path, encoding="utf-8") as f:
        current_jekyll = f.read()

if current_jekyll != expected_jekyll:
    if CHECK_ONLY:
        print("[divergência] _includes/nav.html", file=sys.stderr)
        errors += 1
    else:
        with open(jekyll_nav_path, "w", encoding="utf-8") as f:
            f.write(expected_jekyll)
        os.system(f'git -C "{ROOT}" add "{jekyll_nav_path}"')
        patched.append("_includes/nav.html")

for p in patched:
    print(f"[patch] {p}")

if not patched and not errors:
    print("[ok] todas as páginas têm a nav canónica")

sys.exit(errors)
