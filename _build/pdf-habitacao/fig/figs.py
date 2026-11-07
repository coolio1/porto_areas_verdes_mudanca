import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from pathlib import Path

OUT = Path(__file__).parent
SURF, INK, INK2, MUTE, GRID = "#fcfcfb", "#1f2a24", "#52514e", "#8a8a85", "#e4e4df"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#2e7d32"
LBLUE = "#9dbfe8"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "figure.facecolor": SURF,
        "axes.facecolor": SURF,
        "savefig.facecolor": SURF,
    }
)
FONTSRC = "Fonte: nota de investigação Porto Verde (2026), com os dados e referências do artigo completo."


def base(w=9, h=5, title="", sub="", src=FONTSRC):
    fig = plt.figure(figsize=(w, h))
    fig.text(
        0.04,
        0.955,
        title,
        fontsize=15,
        fontweight="bold",
        color=INK,
        va="top",
        ha="left",
        wrap=True,
    )
    if sub:
        fig.text(0.04, 0.885, sub, fontsize=10.5, color=INK2, va="top", ha="left")
    fig.text(0.04, 0.025, src, fontsize=7.5, color=MUTE, va="bottom", ha="left")
    return fig


def clean(ax, left=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


# 1 preços vs rendimento (índice 2024 = 100)
fig = base(
    8,
    4.8,
    "Em 2025 as casas subiram 3 vezes mais do que o rendimento",
    "Variação em 2025, em Portugal (índice, 2024 = 100)",
)
ax = fig.add_axes([0.07, 0.12, 0.70, 0.66])
clean(ax)
for y, c, l in (
    (117.6, ORANGE, "Preços das casas"),
    (105.7, BLUE, "Rendimento disponível\ndas famílias"),
):
    ax.plot([2024, 2025], [100, y], color=c, lw=3.2, solid_capstyle="round")
    ax.scatter(
        [2024, 2025], [100, y], s=70, color=c, zorder=3, edgecolor=SURF, linewidth=2
    )
    ax.text(
        2025.05,
        y,
        f"+{str(round(y - 100, 1)).replace('.', ',')} %",
        color=INK,
        fontsize=15,
        fontweight="bold",
        va="center",
    )
    ax.text(
        2025.05,
        y - (3.1 if c == BLUE else -3.1),
        l,
        color=INK2,
        fontsize=9.5,
        va="center",
    )
ax.annotate(
    "",
    xy=(2025.0, 117.6),
    xytext=(2025.0, 105.7),
    arrowprops=dict(arrowstyle="<->", color=MUTE, lw=1),
)
ax.text(
    2024.95,
    111.65,
    "11,9 pontos\npercentuais",
    ha="right",
    va="center",
    fontsize=9,
    color=INK2,
)
ax.set_xlim(2023.9, 2026.0)
ax.set_ylim(97, 121)
ax.set_xticks([2024, 2025])
ax.set_xticklabels(["2024", "2025"], fontsize=10)
ax.set_yticks([100, 110, 120])
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
save(fig, "fig1-precos-rendimento.png")

# 2 oferta
fig = base(
    10,
    4.8,
    "A oferta encolheu e construir demora muito",
    "Três sinais do lado da oferta, em Portugal",
)
ax1 = fig.add_axes([0.06, 0.12, 0.30, 0.60])
clean(ax1)
xs, vs = ["2002", "2013", "2025"], [100, 7.8, 44]
ax1.bar(xs, vs, color=[LBLUE, ORANGE, BLUE], width=0.62)
for i, (v, t) in enumerate(zip(vs, ["95,7 mil\nfogos", "−92 %", "≈ 44 %"])):
    ax1.text(i, v + 3, t, ha="center", fontsize=10, fontweight="bold", color=INK)
ax1.set_ylim(0, 128)
ax1.set_yticks([])
ax1.spines["bottom"].set_color(MUTE)
ax1.set_title(
    "Licenciamentos\n(índice, 2002 = 100)", fontsize=10, color=INK2, loc="left"
)
ax2 = fig.add_axes([0.43, 0.12, 0.23, 0.60])
clean(ax2)
ax2.bar(["até 2021", "2021–24"], [4, 14], color=[LBLUE, ORANGE], width=0.6)
for i, v in enumerate([4, 14]):
    ax2.text(
        i, v + 0.5, f"{v} mil", ha="center", fontsize=10, fontweight="bold", color=INK
    )
ax2.set_ylim(0, 17)
ax2.set_yticks([])
ax2.spines["bottom"].set_color(MUTE)
ax2.set_title(
    "Famílias a mais do que\nalojamentos, por ano", fontsize=10, color=INK2, loc="left"
)
ax3 = fig.add_axes([0.74, 0.12, 0.22, 0.60])
clean(ax3)
ax3.bar(["Lisboa", "Porto"], [545, 453], color=[BLUE, BLUE], width=0.6)
for i, v in enumerate([545, 453]):
    ax3.text(
        i, v + 15, f"{v} dias", ha="center", fontsize=10, fontweight="bold", color=INK
    )
ax3.set_ylim(0, 660)
ax3.set_yticks([])
ax3.spines["bottom"].set_color(MUTE)
ax3.set_title("Prazo médio de\nlicenciamento", fontsize=10, color=INK2, loc="left")
save(fig, "fig2-oferta.png")

# 3 cinco choques
fig = base(
    10,
    4.6,
    "Cinco empurrões na procura, e nenhum explica tudo sozinho",
    "Números-chave de cada choque (cada um com datas e âmbito próprios, ver texto)",
)
cards = [
    (
        "> 70 %",
        "do aumento do número de\nfamílias entre 1981 e 2011\nveio de agregados\nmais pequenos",
        "Famílias mais\npequenas",
    ),
    (
        "825 mil",
        "pessoas a mais entre\n2021 e 2025, quase todas\npor migração",
        "Imigração",
    ),
    (
        "19 mil",
        "alojamentos locais em\nLisboa em 2019, contra\ncerca de 900 em 2012;\n8 082 no Porto em 2019",
        "Turismo e\nalojamento local",
    ),
    (
        "8 %",
        "do valor das transacções\nem 2025 (5 % do número)\ncom compradores fiscais\nno estrangeiro",
        "Compradores\nestrangeiros",
    ),
    (
        "26,8 %",
        "do montante dos novos\nempréstimos tem\ngarantia pública",
        "Crédito com\ngarantia pública",
    ),
]
cols = [BLUE, ORANGE, GREEN, BLUE, ORANGE]
ax = fig.add_axes([0.03, 0.09, 0.94, 0.72])
ax.axis("off")
ax.set_xlim(0, 5)
ax.set_ylim(0, 1)
for i, ((n, d, h), c) in enumerate(zip(cards, cols)):
    x = i + 0.04
    ax.add_patch(
        FancyBboxPatch(
            (x, 0.03),
            0.92,
            0.94,
            boxstyle="round,pad=0,rounding_size=0.04",
            fc="#f3f4ef",
            ec=GRID,
            lw=1,
        )
    )
    ax.add_patch(plt.Rectangle((x, 0.89), 0.92, 0.08, fc=c, ec="none"))
    ax.text(
        x + 0.46,
        0.76,
        h,
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        x + 0.46,
        0.52,
        n,
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        x + 0.46,
        0.27,
        d,
        ha="center",
        va="center",
        fontsize=8,
        color=INK2,
        linespacing=1.4,
    )
save(fig, "fig3-choques-v2.png")

# 4 efeitos nos preços
fig = base(
    9,
    5,
    "O que baixa os preços e o que os sobe",
    "Efeito estimado nos preços das casas (%), em estudos de cada país: ordens de grandeza, não comparáveis ao ponto",
    src="Estudos e contextos diferentes (Lisboa, Portugal, Londres). " + FONTSRC,
)
items = [
    ("Help to Buy, Londres\n(apoio à compra sem mais construção)", 8),
    ("Isenção de imposto a jovens, Portugal\n(preços pedidos, 1 ano)", 3.2),
    ("Construir ao ritmo dos anos 2000,\nPortugal (estimativa)", -3),
    ("Duplicar o ritmo de construção,\nPortugal (estimativa)", -6),
    ("Proibição de novos registos de AL,\nLisboa 2018 (zonas abrangidas)", -8),
]
ax = fig.add_axes([0.40, 0.12, 0.55, 0.68])
clean(ax)
for i, (l, v) in enumerate(items):
    ax.barh(i, v, color=ORANGE if v > 0 else GREEN, height=0.58)
    lab = ("+" if v > 0 else "−") + str(abs(v)).replace(".", ",") + " %"
    ax.text(
        v + (0.35 if v > 0 else -0.35),
        i,
        lab,
        va="center",
        ha="left" if v > 0 else "right",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        -10.4,
        i,
        l,
        va="center",
        ha="right",
        fontsize=8.6,
        color=INK2,
        linespacing=1.3,
        clip_on=False,
    )
ax.axvline(0, color=MUTE, lw=1)
ax.set_xlim(-10.4, 10.4)
ax.set_ylim(-0.6, 4.6)
ax.set_yticks([])
ax.set_xticks([])
ax.spines["bottom"].set_visible(False)
ax.text(
    -10.2,
    -0.55,
    "◄ preços descem",
    fontsize=8.5,
    color=GREEN,
    fontweight="bold",
    va="bottom",
)
ax.text(
    10.2,
    -0.55,
    "preços sobem ►",
    fontsize=8.5,
    color=ORANGE,
    fontweight="bold",
    va="bottom",
    ha="right",
)
save(fig, "fig4-efeitos-precos.png")

# 5 habitação pública
fig = base(
    9,
    4.2,
    "Viena: ≈ 44 % do parque é social; em Portugal, < 2 %",
    "Peso do parque social ou a custo controlado no total de habitações (%)",
)
ax = fig.add_axes([0.22, 0.12, 0.72, 0.58])
clean(ax)
ax.barh(2, 1.9, color=BLUE, height=0.55)
ax.text(2.2, 2, "< 2 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.barh(1, 6.5, color=BLUE, height=0.55)
ax.text(6.8, 1, "6–7 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.barh(0, 23, color=BLUE, height=0.55)
ax.barh(0, 21.2, left=23, color=GREEN, height=0.55)
ax.text(
    11.5,
    0,
    "23 %\nmunicipal",
    va="center",
    ha="center",
    fontsize=9.5,
    color="white",
    fontweight="bold",
)
ax.text(
    33.6,
    0,
    "21,2 %\nsem fins lucrativos",
    va="center",
    ha="center",
    fontsize=9.5,
    color="white",
    fontweight="bold",
)
ax.text(44.9, 0, "≈ 44 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.set_yticks([0, 1, 2])
ax.set_yticklabels(["Viena", "Média da OCDE", "Portugal"], fontsize=10.5, color=INK)
ax.set_xlim(0, 52)
ax.set_xticks([])
save(fig, "fig5-habitacao-publica.png")

# 6 vazios
fig = base(
    10,
    4.6,
    "Há muitas casas vagas, mas poucas estão recuperáveis ou são devolutas",
    "Fogos vagos em 2021 e recorte realista para mobilização (número de alojamentos)",
    src="Devolutos com IMI agravado: Lisboa 2022, Porto 2023. «Vago» não é «devoluto». "
    + FONTSRC,
)
data = {"Lisboa": [47748, 21801, 6444], "Porto": [20270, 7799, 531]}
labs = [
    "Vagos (2021)",
    "Fora do mercado\ne em bom estado",
    "Devolutos com\nIMI agravado",
]
cs = [LBLUE, BLUE, ORANGE]
for k, (city, vals) in enumerate(data.items()):
    ax = (
        fig.add_axes(
            [
                0.20 if k == 0 else 0.20 + 0.40 * k + 0.0,
                0.12,
                0.2 if k == 0 else 0.0,
                0.6,
            ]
        )
        if False
        else None
    )
axL = fig.add_axes([0.19, 0.12, 0.26, 0.62])
axP = fig.add_axes([0.70, 0.12, 0.26, 0.62])
for ax, (city, vals), mx in (
    (axL, list(data.items())[0], 62000),
    (axP, list(data.items())[1], 26000),
):
    clean(ax)
    for i, (v, c) in enumerate(zip(vals, cs)):
        ax.barh(2 - i, v, color=c, height=0.6)
        ax.text(
            v + mx * 0.02,
            2 - i,
            f"{v:,}".replace(",", " "),
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=INK,
        )
    ax.set_xlim(0, mx)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_ylim(-0.5, 2.5)
    ax.set_title(city, fontsize=12, fontweight="bold", color=INK, loc="left")
for y, l in zip((0.62, 0.43, 0.24), labs):
    pass
axL.set_yticks([2, 1, 0])
axL.set_yticklabels(labs, fontsize=9, color=INK2)
axP.set_yticks([2, 1, 0])
axP.set_yticklabels(labs, fontsize=9, color=INK2)
save(fig, "fig6-vazios.png")

# 7 roteiro
fig = base(
    10,
    4.8,
    "Um pacote com ordem: primeiro saber e travar, depois construir",
    "Recomendações do artigo, por horizonte temporal",
)
steps = [
    (
        "Já",
        "Parar de piorar\ne saber o que há",
        [
            "Registo de fogos vagos",
            "Sem novas garantias públicas\nnem isenções à procura",
            "Sem tectos de renda\nde 1.ª geração",
            "Fiscalizar o AL",
        ],
        ORANGE,
    ),
    (
        "1 a 3 anos",
        "Desbloquear\na oferta",
        [
            "Prazos de licenciamento\npúblicos",
            "Solo público já urbanizado,\nfora da estrutura ecológica",
            "IMI agravado aplicado\naos vagos recuperáveis",
            "Imigração qualificada\ncomo política de habitação",
        ],
        BLUE,
    ),
    (
        "3 a 10 anos",
        "Construir habitação\na custo controlado",
        [
            "Operadores sem\nfins lucrativos",
            "Solo público já urbanizado",
            "Financiamento estável\nplurianual",
        ],
        GREEN,
    ),
    (
        "Em paralelo",
        "Fiscalidade e\navaliação",
        [
            "Menos imposto na compra,\nmais no recorrente",
            "Avaliar as medidas\nde 2026 antes de alargar",
        ],
        MUTE,
    ),
]
ax = fig.add_axes([0.03, 0.07, 0.94, 0.76])
ax.axis("off")
ax.set_xlim(0, 4)
ax.set_ylim(0, 1)
for i, (t, s, bl, c) in enumerate(steps):
    x = i + 0.03
    ax.add_patch(
        Polygon(
            [
                (x, 0.80),
                (x + 0.86, 0.80),
                (x + 0.97, 0.90),
                (x + 0.86, 1.0),
                (x, 1.0),
                (x + 0.11, 0.90),
            ]
            if i
            else [
                (x, 0.80),
                (x + 0.86, 0.80),
                (x + 0.97, 0.90),
                (x + 0.86, 1.0),
                (x, 1.0),
            ],
            fc=c,
            ec="none",
        )
    )
    ax.text(
        x + 0.50,
        0.90,
        t,
        ha="center",
        va="center",
        color="white",
        fontsize=12,
        fontweight="bold",
    )
    ax.text(
        x + 0.48,
        0.70,
        s,
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=INK,
        linespacing=1.3,
    )
    for j, b in enumerate(bl):
        y = 0.52 - j * 0.14
        ax.text(
            x + 0.04,
            y,
            "•  " + b.replace("\n", "\n    "),
            ha="left",
            va="center",
            fontsize=8.2,
            color=INK2,
            linespacing=1.3,
        )
save(fig, "fig7-roteiro.png")
print("ok")
