from espacos_pipeline.preparar_fusao import montar_dossier


def _fontes():
    return {
        "zip": {"quinta-x": {"titulo": "Quinta X", "n_ficha": "9", "descricao": "{'Importância ecológica': 'Texto 2007.'}", "proposto_por": "Ana Silva"}},
        "projecto": {},
        "pdf": {"5": {"id": 9, "titulo": "Quinta X", "blocos": [
            {"texto": "Texto 2007.", "camada": "2006-2008", "pagina": 5},
            {"texto": "Informações recolhidas junto da Câmara Municipal do Porto em 2014\nOficial.", "camada": "oficial", "pagina": 5},
            {"texto": "Contributo de cidadão.", "camada": "cidadaos", "pagina": 6}]}},
        "webnode": [{"titulo": "Quinta X", "slug": "quinta-x", "texto": "Em 2019 foi inaugurado.", "seleccionado": True}],
        "selecao": [{"id": 9, "nome": "Quinta X", "concelho": "Porto", "selecao": "2009-04"}],
    }


def test_dossier_contem_todas_as_camadas_presentes_e_datas():
    d = montar_dossier("quinta-x", _fontes())
    for esperado in ("Texto 2007.", "Oficial.", "Contributo de cidadão.", "Em 2019 foi inaugurado.", "2009-04", "2006-2008", "oficial", "cidadaos"):
        assert esperado in d


def test_dossier_nao_inclui_nomes_de_pessoas_proponentes():
    assert "Ana Silva" not in montar_dossier("quinta-x", _fontes())
