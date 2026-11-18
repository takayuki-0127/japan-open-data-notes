"""図4枚（PNG）。地域は北から南の順。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5cc7", "#8a8984"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「時系列統計データ検索サイト」（都道府県別預金・現金・貸出金、国内銀行）をもとに作成者が加工して作成"
META = {"Software": None}
UNITS = ["北海道", "東北", "関東（東京を除く）", "東京", "北陸", "中部", "近畿", "中国", "四国", "九州・沖縄"]
ULAB = ["北海道", "東北", "関東\n（東京を\n除く）", "東京", "北陸", "中部", "近畿", "中国", "四国", "九州・\n沖縄"]

def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)

def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    r = pd.read_csv(R / "ldr_by_region_fy.csv", index_col=0)
    # 図1
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for c, col, lw in (("東京", C[1], 1.6), ("全国", INK, 2.2), ("全国（東京を除く）", C[0], 1.8)):
        ax.plot(r.index, r[c], color=col, lw=lw, label=c)
        ax.annotate(f"{r[c].iloc[-1]:.1f}%", (r.index[-1], r[c].iloc[-1]), xytext=(4, 0), textcoords="offset points", fontsize=9, color=col, va="center")
        ax.annotate(f"{r[c].iloc[0]:.1f}%", (r.index[0], r[c].iloc[0]), xytext=(-4, 0), textcoords="offset points", fontsize=9, color=col, va="center", ha="right")
    ax.set_xlabel("年度（4月〜翌年3月の月末残高の平均）"); ax.set_ylabel("預貸率（貸出÷預金、%）")
    ax.set_xlim(1996, 2027.5); ax.set_ylim(0, 175)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    finish(fig, ax, f"全国の預貸率は1998年度{m['national_ldr']['1998']:.0f}%から2021年度{m['national_min']['ldr']:.0f}%へ下がり、その後少し上がった")
    fig.subplots_adjust(left=0.09, right=0.95, top=0.9, bottom=0.15)
    fig.savefig(F / "fig1_national_ldr.png", dpi=150, metadata=META); plt.close(fig)

    # 図2：分解 1998→2025
    dec = pd.read_csv(R / "decomposition_by_region.csv")
    d = dec[(dec["from"] == 1998) & (dec.to == 2025)].set_index("unit").loc[UNITS]
    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    xs = np.arange(len(UNITS)); w = 0.38
    ax.bar(xs - w / 2, d.dlog_deposits_pct, w, color=C[0], label="預金の伸び（対数の差×100）")
    ax.bar(xs + w / 2, d.dlog_loans_pct, w, color=C[1], label="貸出の伸び（対数の差×100）")
    for xi, v in zip(xs, d.ldr_change_pt):
        ax.text(xi, max(d.dlog_deposits_pct.max(), 0) + 8, f"{v:+.0f}", ha="center", fontsize=9, color=INK)
    ax.text(-0.6, d.dlog_deposits_pct.max() + 18, "預貸率の変化（ポイント）", fontsize=8.5, color=INK2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(ULAB, fontsize=9); ax.set_ylim(-15, 140)
    ax.set_ylabel("1998年度→2025年度の伸び")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 0.86))
    finish(fig, ax, "どの地方でも預金が貸出より速く伸びた（1998→2025年度、北から南の順）")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.19)
    fig.savefig(F / "fig2_decomposition_1998_2025.png", dpi=150, metadata=META); plt.close(fig)

    # 図3：2022→2025
    d = dec[(dec["from"] == 2022)].set_index("unit").loc[UNITS + ["全国"]]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    xs = np.arange(len(d))
    cols = [C[2] if v > 0 else C[6] for v in d.ldr_change_pt]
    ax.bar(xs, d.ldr_change_pt, 0.6, color=cols)
    for xi, v, a0, a1 in zip(xs, d.ldr_change_pt, d.ldr_from, d.ldr_to):
        ax.text(xi, v + (0.25 if v > 0 else -0.25), f"{v:+.1f}\n({a0:.0f}→{a1:.0f}%)", ha="center", va="bottom" if v > 0 else "top", fontsize=8)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(ULAB + ["全国"], fontsize=9); ax.set_ylim(-4, 7.5)
    ax.set_ylabel("預貸率の変化（ポイント）")
    finish(fig, ax, f"2022→2025年度は、10の地域のうち{m['n_units_up_2022_2025']}つで預貸率が上がった")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.19)
    fig.savefig(F / "fig3_change_2022_2025.png", dpi=150, metadata=META); plt.close(fig)

    # 図4：預金の増加の中身
    t = pd.read_csv(R / "requestion_deposit_parts.csv")
    t = t[t["from"] == 1998]
    parts = ["個人預金", "法人などの預金（一般預金−個人預金）", "公金預金", "金融機関預金", "その他（政府関係預り金など）"]
    pv = t.pivot(index="unit", columns="part", values="share_of_deposit_increase").loc[UNITS + ["全国"], parts] * 100
    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    xs = np.arange(len(pv)); bottom_pos = np.zeros(len(pv)); bottom_neg = np.zeros(len(pv))
    for k, col in zip(parts, (C[2], C[0], C[3], C[5], C[6])):
        v = pv[k].values
        b = np.where(v >= 0, bottom_pos, bottom_neg)
        ax.bar(xs, v, 0.62, bottom=b, color=col, label=k)
        bottom_pos = bottom_pos + np.where(v >= 0, v, 0); bottom_neg = bottom_neg + np.where(v < 0, v, 0)
    for xi, v in zip(xs, pv["個人預金"].values):
        ax.text(xi, v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(ULAB + ["全国"], fontsize=9); ax.set_ylim(-10, 135)
    ax.set_ylabel("預金の増加に占める割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
    finish(fig, ax, "預金の増加の6〜8割は個人預金。東京だけは法人などの預金が半分近い（1998→2025年度）")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.19)
    fig.savefig(F / "fig4_deposit_parts.png", dpi=150, metadata=META); plt.close(fig)

if __name__ == "__main__":
    main()
