from espacos_pipeline.extrair_webnode import extrair_webnode, area_em_ha

HTML = """
<p><font class="wsw-40"><b>Parque Exemplo</b></font></p>
<p><font>Coordenadas&nbsp; &nbsp;WGS84: 41,16; 8,57&nbsp; &nbsp;Localização&nbsp; &nbsp;freguesia de Campanhã&nbsp; &nbsp;Espaço proposto por Maria Exemplo&nbsp; &nbsp;Área aproximada 80ha</font></p>
<p><font class="wsw-06">Texto de 2019.</font></p>
<p><font class="wsw-06">Mais texto.</font></p>
<p><font>OUTROS ESPAÇOS PROPOSTOS, NÃO SELECIONADOS</font></p>
<p><font class="wsw-40"><b>Quinta Sem Coordenadas</b></font></p>
<p><font>Coordenadas&nbsp; &nbsp;WGS84: 41,17; -8,66&nbsp; &nbsp;Localização&nbsp; &nbsp; Espaço proposto por Outra Pessoa &nbsp; Área aproximada 2000m2</font></p>
<p><font>Sem mais.</font></p>
<p><font class="wsw-40"><b>Pinhal Sem Linha</b></font></p>
<p><font>Texto sem linha de coordenadas.</font></p>
"""


def test_extrai_campos_da_linha_de_coordenadas():
    e = extrair_webnode(HTML)[0]
    assert e["titulo"] == "Parque Exemplo"
    assert e["freguesia"] == "Campanhã"
    assert e["proposto_por"] == "Maria Exemplo"
    assert e["area_ha"] == 80.0
    assert e["texto"] == "Texto de 2019.\nMais texto."


def test_longitude_sem_sinal_e_corrigida_e_assinalada():
    e = extrair_webnode(HTML)[0]
    assert (e["lat"], e["lon"]) == (41.16, -8.57)
    assert e["lon_sinal_corrigido"] is True


def test_seleccionados_ate_ao_marcador():
    a, b = extrair_webnode(HTML)[:2]
    assert a["seleccionado"] is True and b["seleccionado"] is False


def test_area_em_m2_converte_para_hectares():
    assert area_em_ha("2000m2") == 0.2
    assert area_em_ha("3,4ha") == 3.4


def test_titulo_sem_linha_de_coordenadas_nao_e_espaco():
    assert [e["titulo"] for e in extrair_webnode(HTML)] == ["Parque Exemplo", "Quinta Sem Coordenadas"]


def test_area_composta_fica_so_em_texto():
    html = ('<p><font class="wsw-40"><b>Ribeira</b></font></p><p><font>Coordenadas WGS84: 41,16; -8,65 Localização freguesias de A e B '
            'Espaço proposto por X Área aproximada 3ha (A) + 5ha (B)</font></p>')
    e = extrair_webnode(html)[0]
    assert e["area_ha"] is None and e["area_texto"] == "3ha (A) + 5ha (B)"
