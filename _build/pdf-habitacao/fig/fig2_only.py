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
ax2.bar(["2011–21", "2021–24"], [34, 49], color=[LBLUE, ORANGE], width=0.6)
for i, v in enumerate([34, 49]):
    ax2.text(
        i, v + 1.5, f"{v} %", ha="center", fontsize=10, fontweight="bold", color=INK
    )
ax2.set_ylim(0, 60)
ax2.set_yticks([])
ax2.spines["bottom"].set_color(MUTE)
ax2.set_title(
    "Municípios onde as famílias\ncresceram mais que os alojamentos", fontsize=10, color=INK2, loc="left"
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
