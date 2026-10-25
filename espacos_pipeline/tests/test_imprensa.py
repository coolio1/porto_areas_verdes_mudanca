from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def test_cada_pdf_tem_entrada_com_ficheiro_existente():
    entradas = yaml.safe_load((RAIZ / "_data" / "imprensa.yml").read_text(encoding="utf-8"))
    assert entradas and all((RAIZ / "50espacos" / "imprensa" / e["ficheiro"]).exists() for e in entradas)
    assert {e["ficheiro"] for e in entradas} == {p.name for p in (RAIZ / "50espacos" / "imprensa").glob("*.pdf")}
