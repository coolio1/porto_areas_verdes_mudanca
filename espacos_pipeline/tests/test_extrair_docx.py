import docx
from espacos_pipeline.extrair_docx import extrair_ficha, limpar_contactos


def _ficha(tmp_path, linhas, nome="Ficha_1443_Parque Exemplo_NQ.docx"):
    d = docx.Document()
    t = d.add_table(rows=0, cols=3)
    for celulas in linhas:
        r = t.add_row().cells
        for i, v in enumerate(celulas):
            r[i].text = v
    p = tmp_path / nome
    d.save(p)
    return p


LINHAS = [
    ["Parque Exemplo", "Parque Exemplo", "Parque Exemplo"],
    ["1. Dados pessoais", "1. Dados pessoais", ""],
    ["Espaço proposto por", "Maria Exemplo", "Maria Exemplo"],
    ["2. Elementos de localização", "2. Elementos de localização", "2. Elementos de localização"],
    ["Código", "ID 1443", "ID 1443"],
    ["Nome do espaço", "Parque Exemplo", "Parque Exemplo"],
    ["Freguesias", "Campanhã", "Campanhã"],
    ["Concelho", "Porto", "Porto"],
    ["Outras referências", "Coordenadas geográficas WGS84: 41,16; -8,57.", "Coordenadas geográficas WGS84: 41,16; -8,57."],
    ["3. Critérios de avaliação e selecção", "", ""],
    ["Área aproximada", "80 ha", "80 ha"],
    ["Descrição do espaço", "Importância ecológica", "Corre um rio. Contacto: 912345678 ou a@b.pt."],
    ["Descrição do espaço", "Ameaças à preservação", "Uma alameda dividiu o parque."],
]


def test_extrair_ficha_devolve_titulo_id_e_campos(tmp_path):
    f = extrair_ficha(_ficha(tmp_path, LINHAS))
    assert f["titulo"] == "Parque Exemplo"
    assert f["n_ficha"] == 1443
    assert f["concelho"] == "Porto"
    assert f["freguesia"] == "Campanhã"
    assert f["area_texto"] == "80 ha"
    assert f["descricao"]["Importância ecológica"].startswith("Corre um rio")
    assert f["descricao"]["Ameaças à preservação"] == "Uma alameda dividiu o parque."


def test_coordenadas_wgs84_sao_lidas_com_virgula_decimal(tmp_path):
    f = extrair_ficha(_ficha(tmp_path, LINHAS))
    assert (f["lat"], f["lon"]) == (41.16, -8.57)


def test_contactos_sao_removidos_e_contados(tmp_path):
    f = extrair_ficha(_ficha(tmp_path, LINHAS))
    texto = " ".join(f["descricao"].values())
    assert "@" not in texto and "912345678" not in texto
    assert f["contactos_removidos"] == 2


def test_proposto_por_fica_a_parte_do_texto(tmp_path):
    f = extrair_ficha(_ficha(tmp_path, LINHAS))
    assert f["proposto_por"] == "Maria Exemplo"
    assert "Maria Exemplo" not in " ".join(f["descricao"].values())


def test_limpar_contactos_conta_telefones_e_emails():
    txt, n = limpar_contactos("Ligue 22 000 00 00 ou 912 345 678; escreva a x@y.pt")
    assert n == 3 and "@" not in txt and "912" not in txt


def test_extrair_pasta_ignora_paginas_antigas_e_temporarios(tmp_path):
    from espacos_pipeline.extrair_docx import extrair_pasta
    _ficha(tmp_path, LINHAS)
    antigo = tmp_path / "anexos" / "pagina_antiga"
    antigo.mkdir(parents=True)
    _ficha(antigo, LINHAS, nome="velho.docx")
    _ficha(tmp_path, LINHAS, nome="~$temporario.docx")
    r = extrair_pasta(tmp_path, lambda p: "porto")
    assert list(r) == ["parque-exemplo"]
