"""Regra MUST (2026-11-22): todo o caso leva foto de antes e de depois; `sem_par` lista os que faltam."""
from casos_pipeline.validar import sem_par


def _caso(pasta, slug, papeis):
    fotos = "".join(f"  - {{papel: {p}}}\n" for p in papeis)
    (pasta / f"{slug}.md").write_text(f"---\nslug: {slug}\nfotos:\n{fotos}---\ncorpo\n", encoding="utf-8")


def test_sem_par_lista_casos_sem_antes_ou_depois(tmp_path):
    d = tmp_path / "_casos"
    d.mkdir()
    _caso(d, "a", ["antes"])
    _caso(d, "b", ["antes", "depois"])
    _caso(d, "c", ["outra"])
    assert sem_par(tmp_path) == {"a": ["depois"], "c": ["antes", "depois"]}
