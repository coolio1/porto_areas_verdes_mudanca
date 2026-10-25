import pymupdf
import pytest
from espacos_pipeline.extrair_pdf import classificar_cor, extrair_pdf, parse_indice

VERDE, AZUL, AMARELO, SALMAO = (0.8, 1, 0.8), (0.8, 1, 1), (1, 1, 0.6), (1, 0.8, 0.6)


def _pdf(tmp_path, paginas):
    """paginas: lista de listas de (texto, y, cor_fundo|None)."""
    doc = pymupdf.open()
    for linhas in paginas:
        pg = doc.new_page()
        for texto, y, cor in linhas:
            if cor:
                pg.draw_rect(pymupdf.Rect(40, y - 12, 550, y + 6), color=None, fill=cor)
            pg.insert_text((50, y), texto, fontsize=10)
    p = tmp_path / "t.pdf"
    doc.save(p)
    return p


@pytest.mark.parametrize("cor,camada", [
    (VERDE, "oficial"), (AZUL, "campo_aberto"), (AMARELO, "cidadaos"), (SALMAO, "ultima_hora"),
    ((1, 1, 1), "2006-2008"), (None, "2006-2008"), ((0.3, 0.3, 0.9), "desconhecida"),
])
def test_classificar_cor(cor, camada):
    assert classificar_cor(cor) == camada


def _ficha_pag(id_, nome):
    return [(nome, 60, None), ("ENQUADRAMENTO NA CAMPANHA", 90, None), ("Código", 110, None), (f"ID {id_}", 125, None),
            (f"Nome do espaço {nome}", 140, None), ("Texto de 2007.", 170, None),
            ("Observação da câmara em 2014.", 200, VERDE), ("Nota da Campo Aberto.", 230, AZUL)]


def test_ficha_e_segmentada_por_id_com_camadas(tmp_path):
    p = _pdf(tmp_path, [_ficha_pag(1443, "Parque Exemplo")])
    r = extrair_pdf(p)
    f = r[1]
    assert f["id"] == 1443 and f["titulo"] == "Parque Exemplo" and f["pagina_inicio"] == 1
    camadas = {b["camada"]: b["texto"] for b in f["blocos"]}
    assert "Texto de 2007." in camadas["2006-2008"]
    assert camadas["oficial"].startswith("Observação da câmara")
    assert camadas["campo_aberto"].startswith("Nota da Campo Aberto")


def test_pagina_de_continuacao_pertence_a_mesma_ficha(tmp_path):
    p = _pdf(tmp_path, [_ficha_pag(1443, "A"), [("continuação", 60, AMARELO)], _ficha_pag(1444, "B")])
    r = extrair_pdf(p)
    assert r[1]["paginas"] == [1, 2] and r[3]["paginas"] == [3] and r[3]["id"] == 1444
    assert any(b["camada"] == "cidadaos" for b in r[1]["blocos"])


def test_pagina_separadora_do_indice_nao_entra_em_nenhuma_ficha(tmp_path):
    p = _pdf(tmp_path, [_ficha_pag(1443, "A"), [("ADVERTÊNCIAS importantes", 60, None)]])
    r = extrair_pdf(p, paginas_separadoras={2})
    assert r[1]["paginas"] == [1]


def test_parse_indice_marca_seleccionados_e_concelho():
    texto = (
        "Índice\nPorto\n196\nParque Oriental ........ 198\nQuinta da Bouça ........ 203\n"
        "OUTROS ESPAÇOS NÃO SELECIONADOS ........ 227\nPinhal de Aldoar ........ 228\n"
        "Gondomar\n250\nQuinta X ........ 252\n"
    )
    ind = parse_indice(texto)
    por_nome = {e["nome"]: e for e in ind["fichas"]}
    assert por_nome["Parque Oriental"] == {"nome": "Parque Oriental", "pagina": 198, "concelho": "Porto", "seleccionado": True}
    assert por_nome["Pinhal de Aldoar"]["seleccionado"] is False
    assert por_nome["Quinta X"]["concelho"] == "Gondomar" and por_nome["Quinta X"]["seleccionado"] is True
    assert ind["separadoras"] == {196, 227, 250}


def test_mesmo_id_em_dois_concelhos_gera_duas_fichas(tmp_path):
    p = _pdf(tmp_path, [_ficha_pag(1931, "Quinta"), _ficha_pag(1931, "Quinta")])
    assert sorted(extrair_pdf(p)) == [1, 2]
