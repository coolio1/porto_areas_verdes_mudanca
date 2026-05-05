#!/usr/bin/env python3
"""Verifica que HTMLs com Leaflet têm inicialização do mapa (L.map)."""

import sys

errors = []
for f in sys.argv[1:]:
    try:
        content = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        continue
    if "leaflet" in content.lower():
        if "L.map(" not in content and "new L.Map(" not in content:
            errors.append(f)

if errors:
    print("ERRO: HTMLs com Leaflet sem inicialização L.map():")
    for f in errors:
        print(f"  {f}")
    sys.exit(1)
