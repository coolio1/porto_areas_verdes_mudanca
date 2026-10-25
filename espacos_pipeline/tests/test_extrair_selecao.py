import openpyxl
from espacos_pipeline.extrair_selecao import ler_selecao


def _lista_final(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lista Final"
    ws.append(["ID", "Mapa", "Pág.", "Nome", "Freguesia", "Concelho", "GPERITOS", "GEMP", "GONG", "GVOL", "GMUN", "LISTA FINAL", None])
    ws.append([1546, 17, 7, "Gruta da Lomba", "Espinho - Guetim", "Espinho", "x", None, "x", None, "x", "P", 1])
    ws.append([1865, 108, 13, "Bicha", "Espinho - Silvalde", "Espinho", None, None, "x", "X", None, None, None])
    ws.append([1711, 46, 99, "Quinta da Bouça", "Cedofeita", "Porto", "x", None, None, None, None, None, None])
    p = tmp_path / "SeleccaoEV.xlsx"
    wb.save(p)
    return p


def _livro(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Espacos"
    ws.append(["Mapa", "Nome", "Freguesia_principal", "Concelho", "Lista_final", "Responsavel", "Tipologia_predominante", "Voluntario_(incompleto", "Área_(ha)"])
    ws.append([17, "Gruta da Lomba", "GUETIM", "Espinho", "Sim", None, "Espaço verde", None, 105.3])
    ws.append([46, "Quinta da Bouça", "CEDOFEITA", "Porto", "Sim", None, "Quinta", None, 3.4])
    p = tmp_path / "livro.xlsx"
    wb.save(p)
    return p


def test_selecao_junta_lista_de_abril_e_lista_do_livro(tmp_path):
    r = {e["nome"]: e for e in ler_selecao(_lista_final(tmp_path), _livro(tmp_path))}
    assert r["Gruta da Lomba"]["selecao"] == "2009-04"
    assert r["Quinta da Bouça"]["selecao"] == "posterior"
    assert r["Bicha"]["selecao"] is None


def test_resultado_nao_contem_colunas_de_grupos_nem_ordem(tmp_path):
    proibidas = {"GPERITOS", "GEMP", "GONG", "GVOL", "GMUN", "ordem", "posicao"}
    for e in ler_selecao(_lista_final(tmp_path), _livro(tmp_path)):
        assert not proibidas & set(e)


def test_area_do_livro_acompanha_o_espaco_seleccionado(tmp_path):
    r = {e["nome"]: e for e in ler_selecao(_lista_final(tmp_path), _livro(tmp_path))}
    assert r["Gruta da Lomba"]["area_livro_ha"] == 105.3
