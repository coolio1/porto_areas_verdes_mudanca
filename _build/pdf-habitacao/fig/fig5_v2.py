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


# 5 habitação pública (versão 2: Viena em duas barras)
fig = base(
    9,
    4.6,
    "Portugal: menos de 2 %. Viena: 23 % a 44 %",
    "Peso do parque social ou a custo controlado no total de habitações (%)",
)
ax = fig.add_axes([0.25, 0.12, 0.70, 0.58])
clean(ax)
ax.barh(3, 1.9, color=BLUE, height=0.55)
ax.text(2.2, 3, "< 2 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.barh(2, 6.5, color=BLUE, height=0.55)
ax.text(6.8, 2, "6–7 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.barh(1, 23, color=BLUE, height=0.55)
ax.text(11.5, 1, "23 %", va="center", ha="center", fontsize=11, color="white", fontweight="bold")
ax.barh(0, 23, color=BLUE, height=0.55)
ax.barh(0, 21.2, left=23, color=GREEN, height=0.55)
ax.text(11.5, 0, "23 %\nmunicipal", va="center", ha="center", fontsize=9.5, color="white", fontweight="bold")
ax.text(33.6, 0, "21,2 %\nsem fins lucrativos", va="center", ha="center", fontsize=9.5, color="white", fontweight="bold")
ax.text(44.9, 0, "≈ 44 %", va="center", fontsize=12, fontweight="bold", color=INK)
ax.text(23.4, 1, "só habitação municipal", va="center", fontsize=9.5, color=INK2)
ax.set_yticks([0, 1, 2, 3])
ax.set_yticklabels(["Viena (municipal\n+ sem fins lucrativos)", "Viena (municipal)", "Média da OCDE", "Portugal"], fontsize=10, color=INK)
ax.set_xlim(0, 52)
ax.set_xticks([])
save(fig, "fig5-habitacao-publica.png")
