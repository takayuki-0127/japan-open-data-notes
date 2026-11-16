"""図の共通設定（各記事の src/ に写して使う）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "x"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cc7", "#7a7a75"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def save(fig, path, src_line, note=None):
    txt = (note + "\n" if note else "") + src_line
    fig.text(0.01, 0.012, txt, fontsize=7.8, color=INK2, va="bottom")
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def style(ax, ygrid=True):
    if ygrid:
        ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
