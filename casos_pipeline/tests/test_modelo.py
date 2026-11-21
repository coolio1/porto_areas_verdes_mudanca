"""Leitura e normalização dos casos (`_casos/<slug>.md`)."""
from casos_pipeline.modelo import excerto_em_texto, ler_caso, listar_casos, normalizar


def test_normalizar_aspas_e_travessoes():
    assert normalizar("«A  Casa» – velha") == normalizar('"a casa" - velha')


def test_excerto_em_texto_ignora_tipografia_e_espacos():
    texto = "O Município disse que “a árvore  será\nabatida” — sem mais."
    assert excerto_em_texto('"a árvore será abatida"', texto)


def test_excerto_inventado_falha():
    assert not excerto_em_texto("a árvore foi salva", "A árvore será abatida.")


def test_ler_caso_separa_front_matter_e_corpo(tmp_path):
    f = tmp_path / "casa-x.md"
    f.write_text("---\ntitulo: Casa X\ntipo: demolicao\n---\nDescrição do caso.\n", encoding="utf-8")
    c = ler_caso(f)
    assert c["titulo"] == "Casa X" and c["tipo"] == "demolicao"
    assert c["corpo"] == "Descrição do caso." and c["slug"] == "casa-x"


def test_listar_casos_ignora_rascunhos(tmp_path):
    (tmp_path / "_casos").mkdir()
    (tmp_path / "_casos" / "a.md").write_text("---\ntitulo: A\n---\nx\n", encoding="utf-8")
    r = tmp_path / "docs" / "horrores" / "rascunhos"
    r.mkdir(parents=True)
    (r / "b.md").write_text("---\ntitulo: B\n---\nx\n", encoding="utf-8")
    assert [c["slug"] for c in listar_casos(tmp_path)] == ["a"]
