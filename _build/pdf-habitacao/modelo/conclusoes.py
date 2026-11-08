"""Página «Conclusões»: tese, quatro números, cinco choques, veredicto por medida, pacote."""

import re

TESE = (
    "A habitação terá encarecido porque vários aumentos da procura "
    "coincidiram com uma oferta que não acompanhou; o peso de cada um não foi medido. "
    "Os estudos apontam para um pacote, "
    "não para uma medida isolada."
)

NUMEROS = [
    (
        "+145 %",
        "preços das casas em Portugal, 2008–2025",
        "terra",
    ),
    (
        "+69 %",
        "rendimento disponível total das famílias (depois de impostos) em Portugal, 2008–2025; ambos nominais, sem descontar a inflação",
        "ceu",
    ),
    (
        "+10,2 %",
        "renda mediana por m² dos novos contratos de arrendamento em Portugal, 2.º trimestre de 2026, face a um ano antes",
        "terra",
    ),
    (
        "3 a 6 %",
        "de descida dos preços em 2022 se, desde 2012, se tivesse construído ao ritmo dos anos 2000 ou ao dobro (modelo sobre o passado)",
        "folha",
    ),
]

CHOQUES = [
    (
        "Famílias mais pequenas",
        "> 70 %",
        "do aumento do número de famílias em Portugal, 1981–2011, explicado por serem mais pequenas",
    ),
    (
        "Imigração",
        "+849 mil",
        "residentes estrangeiros em Portugal, 2021–2025 (população total: +825 mil; medidas diferentes, que não se somam)",
    ),
    (
        "Alojamento local (AL)",
        "> 19 000",
        "registos (não casas) em Lisboa, 2019 (≈ 900 em 2012): casas ou quartos arrendados a turistas",
    ),
    (
        "Compradores não residentes",
        "5,0 %",
        "das transacções de casas em Portugal, 8,3 % do valor (2025)",
    ),
    (
        "Garantia pública a jovens",
        "26,8 %",
        "do valor dos novos empréstimos para compra de casa em Portugal (2025)",
    ),
]

# (selo, classe, medida, efeito medido, onde / força da evidência)
MEDIDAS = [
    (
        "Funciona",
        "ok",
        "Regular e fiscalizar o alojamento local",
        "preços de venda cerca de 8 % abaixo dos de zonas semelhantes sem a medida, só nos bairros abrangidos (Lisboa, suspensão de 2018)",
        "Rendas (estudos não comparáveis): Berlim até +2,4 % por anúncio comercial a mais; Los Angeles cerca de −2 % ao restringir o AL; Sydney +2,7–3,6 %. Certeza moderada",
    ),
    (
        "Funciona, pouco",
        "ok",
        "Construir mais",
        "baixa os preços, mas só 3 a 6 % (simulação); rendas dos T3 17 a 26 % mais baixas (Auckland)",
        "Rendas: estudos internacionais; preços: simulação portuguesa. Certeza moderada a alta na direcção, baixa na dimensão",
    ),
    (
        "Sem medição",
        "dep",
        "Habitação a custo controlado em grande escala",
        "habitação com custos e rendas ou preços limitados, pública ou de entidades sem fins lucrativos",
        "Só há descrição, sem medição (Viena); nenhum estudo isolou o efeito nas rendas, nem lá nem em Portugal. Certeza baixa",
    ),
    (
        "Depende",
        "dep",
        "Menos imposto na compra de casa, mais no imposto anual",
        "recomendação da Organização para a Cooperação e Desenvolvimento Económico (OCDE): o Imposto Municipal sobre as Transmissões Onerosas de Imóveis (IMT) trava mais a mudança de casa do que o Imposto Municipal sobre Imóveis (IMI), o imposto anual",
        "Estudos no Reino Unido e no Canadá que isolam o efeito dos impostos sobre a compra; pouco estudada em Portugal. Certeza moderada",
    ),
    (
        "Efeitos adversos",
        "nao",
        "Apoios a quem compra casa",
        "isenção do IMT a jovens até 35 anos: preços pedidos nos anúncios cerca de 3,2 % acima do que se estima que teriam sido sem a isenção, 12 meses depois de a medida ser anunciada (Maio de 2024); <em>Help to Buy</em> (crédito público britânico): fez subir os preços em Londres cerca de 7,9 % mais do que fora de Londres",
        "Quando não se constroem mais casas, o apoio a quem compra vai parar ao preço (diferente de trocar imposto na compra por imposto anual). Certeza moderada",
    ),
    (
        "Efeitos adversos",
        "nao",
        "Tectos de renda de primeira geração (limite rígido à renda)",
        "protegem quem tem contrato; reduzem as mudanças de casa e podem reduzir a oferta; efeito global incerto",
        "92 estudos (36 países), dos dois tipos. Certeza moderada a alta; nos de 2.ª geração (Portugal), moderada",
    ),
    (
        "Limitado",
        "peq",
        "Impostos sobre compradores estrangeiros",
        "preços cerca de 5 % mais baixos em Vancouver e 7 a 9 % em Toronto, sem melhoria detectada nas rendas",
        "Colúmbia Britânica e Ontário (Canadá). Efeito limitado: sem melhoria nas rendas e pouco peso em Portugal, onde os não residentes (por residência fiscal, não nacionalidade) são 5,0 % das transacções (2025). Certeza baixa (só vimos o resumo dos estudos)",
    ),
]

# um ícone linear por medida (viewBox 24), na mesma ordem de MEDIDAS
ICONOS = [
    '<path d="M2.5 11.5 9.5 5l7 6.5V19h-14z"/><circle cx="19" cy="7.5" r="2.2"/><path d="M19 9.7V19M19 14h2.5M19 17h2"/>',
    '<path d="M4 11 12 4l8 7v9H4z"/><path d="M12 12v5M9.5 14.5h5"/>',
    '<path d="M5 20V6.5L12 4l7 2.5V20z"/><path d="M8.5 9.5h2M13.5 9.5h2M8.5 13h2M13.5 13h2M10.5 20v-3.5h3V20"/>',
    '<path d="M4 11 12 4l8 7v9H4z"/><circle cx="12" cy="14.5" r="3"/><path d="M12 13.2v2.6"/>',
    '<path d="M4 14l8-6 8 6v6H4z"/><path d="M12 2v4.5M9.8 4.2 12 2l2.2 2.2"/>',
    '<path d="M3 6.5h18"/><path d="M5 12l7-5 7 5v8H5z"/><path d="M7.5 2.5v3M6 4l1.5 1.5L9 4M16.5 2.5v3M15 4l1.5 1.5L18 4"/>',
    '<circle cx="8.5" cy="5.5" r="2"/><path d="M8.5 8v6.5M5.5 11h6M8.5 14.5l-2 5M8.5 14.5l2 5"/><path d="M14.5 13h5.5v6h-5.5zM16 13v-1.6h2.5V13"/>',
]

PASSOS = [
    (
        "Já",
        "Parar de piorar: criar o registo de casas vagas; não alargar apoios à compra; não criar novos tectos rígidos de renda; fazer cumprir as zonas de contenção do AL.",
    ),
    (
        "Em um a três anos",
        "Mais oferta: licenças a prazo certo, com pareceres e protecção ambiental; solo público urbanizado; imigrantes como mão-de-obra; IMI agravado aplicado de forma sistemática aos devolutos.",
    ),
    (
        "Em três a dez anos",
        "Construir um sector de habitação a custo controlado, com operadores sem fins lucrativos.",
    ),
    (
        "Em paralelo",
        "Menos imposto na compra (IMT) e mais no imposto anual (IMI); avaliar as medidas comparando com o que teria acontecido sem elas.",
    ),
]

TERRITORIO = (
    "Em 2021, Lisboa e Porto tinham 29 600 casas vagas (sem ocupante no Censo) fora do mercado e em bom estado "
    "(21 801 em Lisboa; 7 799 no Porto); mobilizá-las é complemento: poucos milhares de casas de uma só vez, "
    "por cálculo ilustrativo. A nova oferta deve ficar fora da estrutura ecológica "
    "(onde o plano municipal protege espaços verdes e linhas de água)."
)

NICHO = (
    "Renda de custo (<em>cost rental</em>), cooperativas e outras: efeitos só locais; nenhuma baixou "
    "os preços de uma cidade; algumas sem avaliação."
)

CSS = """
.conc{page:cheia;position:relative;width:210mm;height:296.5mm;overflow:hidden;break-after:page;background:var(--papel);font-family:var(--fu)}
.conc .topo{position:relative;background:var(--verde);color:#fff;padding:9mm 15mm 0;height:80mm}
.conc .topo .im{position:absolute;right:0;top:0;width:90mm;height:56mm;object-fit:cover}
.conc .topo .veu{position:absolute;right:0;top:0;width:90mm;height:56mm;background:linear-gradient(90deg,var(--verde) 0%,rgba(27,77,32,.6) 45%,rgba(27,77,32,0) 100%)}
.conc .kick{position:relative;font:700 7.6pt var(--fu);letter-spacing:.22em;text-transform:uppercase;color:var(--musgo)}
.conc h2{position:relative;font:700 34pt/1 var(--fd);color:#fff;margin:2mm 0 2.5mm;border:none;padding:0;break-before:auto}
.conc .tese{position:relative;font:400 10.4pt/1.34 var(--fd);color:#e6f0e1;width:150mm;margin:0}
.conc .nums{position:absolute;left:15mm;right:15mm;bottom:5mm;display:grid;grid-template-columns:repeat(4,1fr);gap:3mm}
.conc .nums div{background:rgba(255,255,255,.96);border-top:3pt solid var(--cor);padding:2mm 2.6mm 2.2mm;height:25mm}
.conc .nums b{display:block;font:700 19pt/1 var(--fd);color:var(--cor);white-space:nowrap}
.conc .nums span{display:block;font:400 6.7pt/1.25 var(--fu);color:#2b322c;margin-top:1.2mm}
.conc .ceu{--cor:var(--ceu)}.conc .terra{--cor:var(--terra)}.conc .folha{--cor:var(--folha)}
.conc .sec{font:700 7.2pt var(--fu);letter-spacing:.2em;text-transform:uppercase;color:var(--folha);margin:0 0 1.6mm}
.conc .choques{padding:4mm 15mm 0}
.conc .cs{display:grid;grid-template-columns:repeat(5,1fr);gap:2.4mm}
.conc .cs div{border-left:2pt solid var(--terra);padding:0 0 0 2.2mm}
.conc .cs i{display:block;font:600 6.4pt var(--fu);font-style:normal;letter-spacing:.06em;text-transform:uppercase;color:var(--cinza)}
.conc .cs b{display:block;font:700 13pt/1.1 var(--fd);color:var(--verde);white-space:nowrap;margin:.6mm 0}
.conc .cs span{display:block;font:400 6.6pt/1.25 var(--fu);color:#2b322c}
.conc .ver{padding:4mm 15mm 0}
.conc .ln{display:grid;grid-template-columns:23mm 1fr;gap:3mm;align-items:start;padding:1.9mm 0;border-top:.5pt solid #dfe6da}
.conc .ln:first-of-type{border-top:none}
.conc .ln{grid-template-columns:13mm 1fr 23mm;align-items:center;padding:1.3mm 0}
.conc .ic{display:flex;align-items:center;justify-content:center;width:12mm;height:12mm;border-radius:50%;background:color-mix(in srgb,var(--c) 13%,white)}
.conc .ic svg{width:7.6mm;height:7.6mm;fill:none;stroke:var(--c);stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.conc .ok{--c:var(--folha)}.conc .dep{--c:var(--ceu)}.conc .nao{--c:var(--terra)}.conc .peq{--c:#6f776f}
.conc .selo{display:block;text-align:center;font:700 6.4pt var(--fu);letter-spacing:.08em;text-transform:uppercase;color:#fff;padding:1.2mm 0;border-radius:2px;white-space:nowrap}
.conc .ok .selo{background:var(--folha)}.conc .dep .selo{background:var(--ceu)}.conc .nao .selo{background:var(--terra)}.conc .peq .selo{background:#8a918a}
.conc .ln h3{font:700 9.6pt/1.15 var(--fd);color:var(--verde);margin:0;break-after:auto}
.conc .ln .ef{font:600 7.8pt/1.3 var(--fu);color:#1e2620;margin:.5mm 0 0}
.conc .ln .ev{font:400 7pt/1.3 var(--fu);color:var(--cinza);margin:.2mm 0 0}
.conc .pacote{position:absolute;left:0;right:0;bottom:0;height:82mm;background:var(--verde);color:#fff;padding:4.5mm 15mm}
.conc .pacote .k{font:700 7.2pt var(--fu);letter-spacing:.2em;text-transform:uppercase;color:var(--musgo)}
.conc .pacote h4{font:700 13pt/1.1 var(--fd);margin:1mm 0 2.6mm;color:#fff}
.conc .passos{display:grid;grid-template-columns:repeat(4,1fr);gap:2.2mm}
.conc .passo{background:#255a2a;padding:2.4mm 3mm;clip-path:polygon(0 0,calc(100% - 3.5mm) 0,100% 50%,calc(100% - 3.5mm) 100%,0 100%)}
.conc .passo:last-child{clip-path:none}
.conc .passo .h{font:700 11.5pt/1 var(--fd);color:#ffa77a}
.conc .passo .d{font:400 7.2pt/1.28 var(--fu);color:#dcead6;margin-top:1mm;padding-right:3mm}
.conc .terr{margin:2.6mm 0 0;font:400 7.4pt/1.35 var(--fu);color:#dcead6;border-top:.5pt solid #3f7344;padding-top:2mm}
.conc .terr b{color:#ffa77a}
.conc .terr.nic{margin-top:1.2mm;border-top:none;padding-top:0}
.conc .rod{position:absolute;left:15mm;right:15mm;bottom:3mm;font:400 6.6pt/1.35 var(--fu);color:#9fbf9e;display:flex;justify-content:space-between;align-items:flex-end;gap:6mm}
.conc .rod b{color:#ffa77a}
.conc .rod span:last-child{white-space:nowrap}
"""


def _nb(t):
    nb = chr(160)
    t = re.sub(
        r"(\d) (%|€|mil\b|milhões\b|M€|dias\b|anos\b|meses\b|fogos\b)",
        r"\1" + nb + r"\2",
        t,
    )
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", nb, t)
    t = re.sub(r"(?<=[+−>≈]) (?=\d)", nb, t)
    t = re.sub(r"(a) (−\d)", r"\1" + nb + r"\2", t)
    return t


def html(img="img/hero.png"):
    nums = "".join(
        f'<div class="{c}"><b>{n}</b><span>{d}</span></div>' for n, d, c in NUMEROS
    )
    chq = "".join(
        f"<div><i>{a}</i><b>{n}</b><span>{d}</span></div>" for a, n, d in CHOQUES
    )
    ver = "".join(
        f'<div class="ln {c}"><span class="ic"><svg viewBox="0 0 24 24">{ICONOS[k]}</svg></span>'
        f'<div><h3>{m}</h3><p class="ef">{e}</p><p class="ev">{v}</p></div>'
        f'<span class="selo">{s}</span></div>'
        for k, (s, c, m, e, v) in enumerate(MEDIDAS)
    )
    pas = "".join(
        f'<div class="passo"><div class="h">{h}</div><div class="d">{d}</div></div>'
        for h, d in PASSOS
    )
    out = f"""<div class="conc">
<div class="topo"><img class="im" src="{img}"><div class="veu"></div>
 <div class="kick">Síntese deste artigo</div><h2>Conclusões</h2>
 <p class="tese">{TESE}</p>
 <div class="nums">{nums}</div></div>
<div class="choques"><p class="sec">Cinco choques na procura (aumentos súbitos e fortes do número de pessoas ou do dinheiro à procura de casa)</p><div class="cs">{chq}</div></div>
<div class="ver"><p class="sec">O que dizem os estudos sobre cada medida <span style="text-transform:none;letter-spacing:0;font-weight:400">(selo: o que os estudos mostram; certeza: solidez e coerência dos estudos)</span></p>{ver}</div>
<div class="pacote"><div class="k">O que os estudos sugerem</div><h4>Um pacote em três etapas, mais medidas em paralelo</h4>
 <div class="passos">{pas}</div>
 <p class="terr"><b>Casas vazias e espaços verdes.</b> {TERRITORIO}</p>
 <p class="terr nic"><b>Ideias menos conhecidas.</b> {NICHO}</p>
 <div class="rod"><span><b>Leia por zona, não por cidade:</b> as médias escondem diferenças entre bairros; os efeitos valem para as zonas estudadas.<br>Certeza global: moderada quanto à direcção dos efeitos, baixa quanto à sua dimensão em Portugal.</span><span>Porto Verde · portoverde.pt</span></div></div>
</div>"""
    return _nb(out)
