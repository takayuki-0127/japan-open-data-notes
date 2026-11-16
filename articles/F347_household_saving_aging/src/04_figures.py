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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：内閣府「国民経済計算」、総務省「家計調査」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))

# ---- 図1：国民経済計算の家計貯蓄率 ------------------------------------------------------
s = pd.read_csv(R / "sna_series.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.plot(s.index, s.saving_rate_pct, color=C[0], lw=2.2, marker="o", ms=3.5)
for y in [1994, 2000, 2005, 2015, 2020, 2024]:
    v = s.loc[y, "saving_rate_pct"]
    ax.text(y, v + 0.7, f"{v:.1f}", ha="center", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("家計貯蓄率（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"家計貯蓄率は1994年の{main['sna_saving_rate_pct']['1994']:.1f}%から2024年の{main['sna_saving_rate_pct']['2024']:.1f}%に（2020年は一時的に上昇）", loc="left", fontsize=11.5)
ax.set_ylim(-2.5, 14)
fig.text(0.01, 0.01, "注：国民経済計算（2024年度年次推計）、家計（個人企業を含む）、暦年。貯蓄率＝貯蓄（純）÷（可処分所得（純）＋年金受給権の変動調整）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_sna_saving_rate.png")

# ---- 図2：家計調査（勤労者の黒字率と割合） ------------------------------------------------
k = pd.read_csv(R / "kakei_series.csv", index_col=0)
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
axes[0].plot(k.index, k.worker_surplus_rate_pct, color=C[1], lw=2.2, marker="o", ms=3.5)
axes[0].set_title("勤労者世帯の黒字率（%）", loc="left", fontsize=11)
axes[1].plot(k.index, k.worker_share_pct, color=C[2], lw=2.2, marker="o", ms=3.5)
axes[1].set_title("二人以上の世帯のうち勤労者世帯の割合（%、集計世帯数の比）", loc="left", fontsize=10.5)
for ax, col in zip(axes, ["worker_surplus_rate_pct", "worker_share_pct"]):
    for y in [2000, 2015, 2025]:
        ax.text(y, k.loc[y, col] + 0.6, f"{k.loc[y, col]:.1f}", ha="center", fontsize=9, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylim(20, 42); axes[1].set_ylim(45, 62)
fig.suptitle("働いている世帯の黒字率は上がった。働いている世帯の割合は2015年まで下がり、その後少し戻った", x=0.01, ha="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：家計調査、二人以上の世帯、2000〜2025年。黒字率＝（可処分所得 − 消費支出）÷ 可処分所得。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.15, wspace=0.25)
save(fig, "fig2_worker_rate_and_share.png")

# ---- 図3：構成の効果と、勤労者の黒字率の効果 -----------------------------------------------
fig, ax = plt.subplots(figsize=(8.6, 4.6))
labs = ["構成の変化だけ\n（勤労者の割合 59.2%→53.9%）", "勤労者世帯の黒字率の上昇だけ\n（27.9%→35.0%）", "（参考）国民経済計算の\n貯蓄率の変化（2000→2024年）"]
vals = [main["counterfactual_main_change_pt"], main["rate_effect_worker_2000_to_2025_pt"], main["sna_change_2000_2024_pt"]]
cols = [C[2], C[1], INK2]
y = np.arange(3)[::-1]
ax.barh(y, vals, color=cols, height=0.55)
for yi, v in zip(y, vals):
    ax.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.1f}ポイント", va="center", ha="left" if v >= 0 else "right", fontsize=10, color=INK)
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(y, labs, fontsize=9.5)
ax.set_xlim(-11, 8)
ax.set_xlabel("貯蓄率（黒字率）の変化（ポイント）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"家計調査の世帯では、構成の変化（{main['counterfactual_main_change_pt']:+.1f}）より\n勤労者の黒字率の上昇（{main['rate_effect_worker_2000_to_2025_pt']:+.1f}）が大きい", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：上2本は家計調査の二人以上の世帯（勤労者と、それ以外を無職世帯の値で代表）で、2025年の所得と黒字率を固定したおおまかな試算。国民経済計算とは定義が違う。\n" + SRC,
         fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.3, right=0.97, top=0.86, bottom=0.18)
save(fig, "fig3_composition_vs_rate.png")

# ---- 図4：問い直し（可処分所得の項目） ------------------------------------------------------
q = req["1994_2024"]
items = list(q["components_tyen"].items())
items.sort(key=lambda kv: kv[1])
fig, ax = plt.subplots(figsize=(8.8, 5.2))
y = np.arange(len(items))
ax.barh(y, [v for _, v in items], color=[C[0] if v >= 0 else C[1] for _, v in items], height=0.6)
for yi, (n, v) in zip(y, items):
    ax.text(v + (0.6 if v >= 0 else -0.6), yi, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=9.5, color=INK)
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(y, [n.replace("（純）", "") for n, _ in items], fontsize=9.5)
ax.set_xlim(-45, 62)
ax.set_xlabel("可処分所得への寄与（兆円、1994→2024年）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"可処分所得は+{q['d_disposable_income_tyen']:.1f}兆円、消費は+{q['d_consumption_tyen']:.1f}兆円（1994→2024年）\n社会負担の増加は社会給付の増加とほぼ見合い、利子・自営の所得の減少が伸びを抑えた", loc="left", fontsize=11)
fig.text(0.01, 0.01, "注：国民経済計算、家計（個人企業を含む）、暦年。支払の項目は増えると可処分所得を減らす向きに表示。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.27, right=0.97, top=0.88, bottom=0.14)
save(fig, "fig4_income_components.png")
print("figures done")
