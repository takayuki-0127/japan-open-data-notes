"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「公共施設状況調経年比較表」「住民基本台帳に基づく人口、人口動態及び世帯数調査」をもとに作成者が加工して作成"
META = {"Software": None}
ORDER = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.19)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
bs = pd.read_csv(R / "by_size.csv")
ch = pd.read_csv(R / "change_2019_2024.csv")
dec = pd.read_csv(R / "requestion_decomposition.csv")
mm = pd.read_csv(R / "rate_by_municipality.csv", dtype={"code": str})
b = bs[bs.year == 2024].set_index("size").reindex(ORDER)
x = np.arange(len(ORDER))

# 図1：方式別の積み上げ（人口に対する%）
fig, ax = plt.subplots(figsize=(9, 5.4))
parts = [("sewer_pct", "下水道", C[0]), ("rural_pct", "農業集落排水など", C[2]), ("plant_pct", "コミュニティ・プラント", C[4]), ("johkaso_pct", "合併処理浄化槽", C[3])]
bot = np.zeros(len(ORDER))
for k, lab, c in parts:
    ax.bar(x, b[k].values, 0.62, bottom=bot, color=c, label=lab)
    bot += b[k].values
for i, v in enumerate(b.rate_weighted.values):
    ax.text(i, v + 1.2, f"{v:.1f}%", ha="center", va="bottom", fontsize=10, color=INK)
nat = m["national_rate"]["2024"]
ax.axhline(nat, color=INK2, lw=1, ls="--")
ax.text(-0.45, nat + 1.2, f"全国 {nat:.1f}%", ha="left", va="bottom", fontsize=9, color=INK2)
ax.set_xticks(x, ORDER); ax.set_ylim(0, 112); ax.set_ylabel("人口に対する割合（%）")
ax.legend(loc="upper left", frameon=False, ncol=4, fontsize=9, bbox_to_anchor=(0, 1.04))
s0 = b.loc["5千人未満"]
finish(fig, ax, f"汚水処理の普及率（2024年度末）：5千人未満 {s0.rate_weighted:.1f}%、うち下水道は {s0.sewer_pct:.1f}%")
save(fig, "fig1_rate_by_type.png")

# 図2：団体ごとの普及率のばらつき（箱ひげ＋点）
fig, ax = plt.subplots(figsize=(9, 5.4))
d24 = mm[mm.year == 2024]
rng = np.random.default_rng(0)
for i, s in enumerate(ORDER):
    v = d24[d24["size"] == s].rate.clip(upper=110).values
    ax.scatter(i + rng.uniform(-0.22, 0.22, len(v)), v, s=6, color=C[0], alpha=0.35, lw=0)
ax.boxplot([d24[d24["size"] == s].rate.clip(upper=110).values for s in ORDER], positions=x, widths=0.5, showfliers=False,
           medianprops={"color": C[1], "lw": 2}, boxprops={"color": INK2}, whiskerprops={"color": INK2}, capprops={"color": INK2})
ax.set_xticks(x, [f"{s}\n80%未満は\n{int(b.loc[s, 'n_below80'])}/{int(b.loc[s, 'n'])}団体" for s in ORDER], fontsize=9.5); ax.set_ylim(0, 112); ax.set_ylabel("団体ごとの普及率（%、110%で頭打ちにして表示）")
finish(fig, ax, f"団体ごとのばらつき（2024年度末）：中央値は 5千人未満 {s0.rate_median:.1f}%、30万人以上 {b.loc['30万人以上', 'rate_median']:.1f}%")
save(fig, "fig2_rate_spread.png")

# 図3：2019→2024年度の変化を「処理人口の増減」と「人口の減少」に分ける
fig, ax = plt.subplots(figsize=(9, 5.4))
dd = dec.set_index("size").reindex(ORDER)
wd = 0.27
ax.bar(x - wd, dd.served_effect_pt, wd, color=C[1], label="処理人口の増減の分")
ax.bar(x, dd.pop_effect_pt, wd, color=C[0], label="人口が減った分")
ax.bar(x + wd, dd.change_pt, wd, color=INK2, label="普及率の変化（2つの和）")
for i, v in enumerate(dd.change_pt):
    ax.text(i + wd, v + 0.25, f"{v:+.1f}", ha="center", va="bottom", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, ORDER); ax.set_ylabel("2019→2024年度の変化（ポイント）")
ax.set_ylim(min(dd.served_effect_pt.min(), 0) - 1.2, dd.pop_effect_pt.max() + 1.8)
ax.legend(loc="upper right", frameon=False, fontsize=9)
q = m["requestion"]["small"]
finish(fig, ax, f"5千人未満の +{q['change_pt']:.1f}pt は、人口が減った分 +{q['pop_effect_pt']:.1f}pt と処理人口の減少 {q['served_effect_pt']:.1f}pt の和")
save(fig, "fig3_change_decomposition.png")

# 図4：届いていない人の数（人口規模別）
fig, ax = plt.subplots(figsize=(9, 5.4))
un = m["unserved_by_size_2024"]; sh = m["unserved_share_by_size_2024"]
v = np.array([un[s] for s in ORDER]) / 1e4
ax.bar(x, v, 0.62, color=[C[1] if s == max(un, key=un.get) else C[0] for s in ORDER])
for i, s in enumerate(ORDER):
    ax.text(i, v[i] + 4, f"{v[i]:.0f}万人\n（{sh[s]:.1f}%）", ha="center", va="bottom", fontsize=9.5, color=INK)
ax.set_xticks(x, ORDER); ax.set_ylim(0, v.max() * 1.22); ax.set_ylabel("汚水処理人口に入らない人（万人）")
top = max(un, key=un.get)
finish(fig, ax, f"届いていない約{m['unserved_2024'] / 1e4:.0f}万人のうち {sh[top]:.0f}% は {top} の市町村に住む（2024年度末）")
save(fig, "fig4_unserved_people.png")
