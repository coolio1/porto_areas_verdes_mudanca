from espacos_pipeline.reconciliar import norm_concelho, reconciliar, escrever_md


def _ficha(id_, titulo, concelho="Porto", freguesia="Campanhã", **kw):
    return {"n_ficha": id_, "titulo": titulo, "concelho": concelho, "freguesia": freguesia, **kw}


def _pdf(pagina, id_, titulo, concelho="Porto", seleccionado=False):
    return {"id": id_, "titulo": titulo, "pagina_inicio": pagina, "concelho": concelho, "seleccionado": seleccionado}


def _fontes(**kw):
    base = {"zip": {}, "projecto": {}, "pdf": {}, "webnode": [], "selecao": []}
    base.update(kw)
    return base


def _registo_de(r, titulo_parcial):
    return next(x for x in r.registos if any(titulo_parcial.lower() in t.lower() for t in x["titulo"].values()))


def test_norm_concelho_junta_variantes():
    assert norm_concelho("gaia") == norm_concelho("Vila Nova de Gaia") == "vila-nova-de-gaia"
    assert norm_concelho("vila_conde") == "vila-do-conde"
    assert norm_concelho("Gondomar (1) e Porto (2)") == "gondomar"
    assert norm_concelho("PORTO") == "porto"


def test_ficha_so_no_zip_aparece_no_relatorio():
    r = reconciliar(_fontes(zip={"a": _ficha(1, "Parque Alfa")}, projecto={"b": _ficha(2, "Jardim Beta Totalmente Distinto")}))
    assert {tuple(x["fontes"]) for x in r.registos} == {("zip",), ("projecto",)}
    assert len(r.so_numa_fonte) == 2


def test_nomes_com_gralhas_mas_mesmo_espaco_ficam_juntos():
    r = reconciliar(_fontes(
        zip={"x": _ficha(1443, "Parque Oriental")},
        projecto={"y": _ficha(1443, "parque oriental ")},
        pdf={"5": _pdf(5, 1443, "Parque Oriental", seleccionado=True)},
    ))
    assert len(r.registos) == 1 and set(r.registos[0]["fontes"]) == {"zip", "projecto", "pdf"}


def test_id_diferente_mas_nome_igual_liga_e_regista_divergencia_de_id():
    r = reconciliar(_fontes(
        zip={"x": _ficha(1593, "Quinta agrícola perto da Prelada")},
        selecao=[{"id": 1864, "nome": "Quinta agrícola perto da Prelada", "concelho": "Porto", "selecao": "2009-04"}],
    ))
    assert len(r.registos) == 1
    assert any(d["campo"] == "id" for d in r.divergencias)


def test_webnode_liga_por_nome_parecido_mesmo_com_palavras_trocadas():
    r = reconciliar(_fontes(
        pdf={"1": _pdf(1, 1756, "Monte Crasto Villa")},
        webnode=[{"titulo": "Villa Monte Crasto", "slug": "villa-monte-crasto", "seleccionado": False, "lat": 41.16, "lon": -8.68}],
    ))
    assert len(r.registos) == 1 and "webnode" in r.registos[0]["fontes"]


def test_mesmo_id_em_dois_concelhos_gera_dois_registos():
    r = reconciliar(_fontes(
        pdf={"1": _pdf(1, 1931, "Quinta Cunha-Lima", "Gondomar"), "2": _pdf(2, 1931, "Quinta Cunha-Lima", "Porto")},
        zip={"x": _ficha(1931, "Quinta Cunha-Lima", "Porto")},
    ))
    assert len(r.registos) == 2
    assert [x for x in r.registos if "zip" in x["fontes"]][0]["concelho"]["pdf"] == "porto"


def test_divergencia_de_freguesia_e_coordenadas_e_registada_e_nao_resolvida():
    r = reconciliar(_fontes(
        zip={"x": _ficha(1931, "Antiga Quinta", freguesia="Campanhã", lat=41.16, lon=-8.58)},
        webnode=[{"titulo": "Antiga Quinta", "slug": "antiga-quinta", "seleccionado": False, "freguesia": "Aldoar", "lat": 41.17, "lon": -8.67}],
    ))
    assert {"freguesia", "coordenadas"} <= {d["campo"] for d in r.divergencias}
    assert _registo_de(r, "Antiga")["freguesia"] == {"zip": "Campanhã", "webnode": "Aldoar"}


def test_seleccionado_diferente_entre_fontes_e_divergencia():
    r = reconciliar(_fontes(
        pdf={"3": _pdf(3, 7, "Quinta Real", seleccionado=True)},
        selecao=[{"id": 7, "nome": "Quinta Real", "concelho": "Porto", "selecao": None}],
    ))
    assert any(d["campo"] == "seleccionado" for d in r.divergencias)


def test_webnode_sem_correspondencia_fica_listado():
    r = reconciliar(_fontes(
        zip={"x": _ficha(1, "Parque Alfa")},
        webnode=[{"titulo": "Coisa Totalmente Diferente", "slug": "coisa-totalmente-diferente", "seleccionado": False}],
    ))
    assert [w["titulo"] for w in r.webnode_sem_id] == ["Coisa Totalmente Diferente"]


def test_escrever_md_lista_divergencias(tmp_path):
    r = reconciliar(_fontes(zip={"x": _ficha(1, "Parque Alfa")}, projecto={"y": _ficha(1, "Parque Alfa", freguesia="Outra")}))
    p = tmp_path / "r.md"
    escrever_md(r, p)
    assert "freguesia" in p.read_text(encoding="utf-8")


def test_espaco_em_dois_concelhos_com_mesmo_id_e_nome_e_um_so_registo():
    r = reconciliar(_fontes(
        zip={"x": _ficha(1730, "Rio Ferreira", "Valongo")},
        pdf={"9": _pdf(9, 1730, "Rio Ferreira", "Gondomar", seleccionado=True)},
    ))
    assert len(r.registos) == 1
    assert any(d["campo"] == "concelho" for d in r.divergencias)


def test_resolver_prevalece_o_que_2_fontes_concordam():
    from espacos_pipeline.reconciliar import resolver
    r = reconciliar(_fontes(
        zip={"x": _ficha(1931, "Antiga Quinta", freguesia="Campanhã", lat=41.16, lon=-8.58)},
        projecto={"y": _ficha(1931, "Antiga Quinta", freguesia="Campanhã", lat=41.16, lon=-8.58)},
        webnode=[{"titulo": "Antiga Quinta", "slug": "antiga-quinta", "seleccionado": False, "freguesia": "Aldoar", "lat": 41.17, "lon": -8.67}],
    ))
    reg = resolver(r)[0]
    assert reg["resolvido"]["freguesia"] == "Campanhã"
    assert reg["resolvido"]["coordenadas"] == [41.16, -8.58]
    assert {d["campo"] for d in reg["decisoes"]} == {"freguesia", "coordenadas"}
    assert all(d["regra"] == "2+ fontes" for d in reg["decisoes"])


def test_resolver_empate_prefere_fonte_nao_webnode_e_marca_pendente():
    from espacos_pipeline.reconciliar import resolver
    r = reconciliar(_fontes(
        zip={"x": _ficha(1, "Quinta Beta", freguesia="Campanhã")},
        webnode=[{"titulo": "Quinta Beta", "slug": "quinta-beta", "seleccionado": False, "freguesia": "Aldoar"}],
    ))
    reg = resolver(r)[0]
    assert reg["resolvido"]["freguesia"] == "Campanhã"
    assert reg["decisoes"][0]["regra"] == "empate: fonte não-Webnode"


def test_resolver_webnode_acrescenta_quando_ninguem_mais_tem():
    from espacos_pipeline.reconciliar import resolver
    r = reconciliar(_fontes(
        zip={"x": _ficha(1, "Quinta Beta", freguesia="Campanhã")},
        webnode=[{"titulo": "Quinta Beta", "slug": "quinta-beta", "seleccionado": False, "lat": 41.16, "lon": -8.6}],
    ))
    reg = resolver(r)[0]
    assert reg["resolvido"]["coordenadas"] == [41.16, -8.6]
    assert reg["decisoes"] == []
