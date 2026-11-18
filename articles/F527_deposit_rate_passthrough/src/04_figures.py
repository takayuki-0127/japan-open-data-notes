"""図4枚（PNG）。日付などのメタデータは入れない。"""
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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5cc7"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「時系列統計データ検索サイト」（コールレート、預金種類別店頭表示金利の平均年利率等、定期預金の預入期間別平均金利）をもとに作成者が加工して作成"
META = {"Software": None}

def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.2, color=INK2)

def ymlab(ix):
    return [f"{s[:4]}" for s in ix]

def main():
    df = pd.read_csv(ROOT / "data" / "monthly.csv", dtype={"ym": str}).set_index("ym")
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    x = pd.to_datetime(df.index, format="%Y%m")
    # 図1：長い推移
    fig, ax = plt.subplots(figsize=(9, 5.2))
    sub = df.index >= "200301"
    ax.plot(x[sub], df.call_avg[sub], color=INK, lw=1.6, label="無担保コールレート（月平均）")
    for c, lab, col in (("td5y", "定期5年（300万円未満）", C[3]), ("td1y", "定期1年（300万円未満）", C[1]), ("ordinary", "普通預金", C[0])):
        ax.plot(x[sub], df[c][sub], color=col, lw=1.8, label=lab)
    for d, t in (("2007-10", "調査の切り替え"), ("2022-04", "調査の切り替え（月央の値に）")):
        ax.axvline(pd.Timestamp(d), color=INK2, lw=0.8, ls=":")
        ax.text(pd.Timestamp(d), 1.32, " " + t, fontsize=8, color=INK2, va="top")
    ax.set_ylabel("年利（%）"); ax.set_ylim(-0.1, 1.35)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0.0, 0.9))
    finish(fig, ax, "預金の店頭金利は、コールレートより小さく、少し遅れて動く（2003年1月〜2026年11月）")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.12)
    fig.savefig(F / "fig1_rates_over_time.png", dpi=150, metadata=META); plt.close(fig)

    # 図2：局面ごとの追随の比
    cyc = pd.read_csv(R / "cycles.csv")
    order = ["ordinary", "td3m", "td1y", "td5y", "td1y_large"]
    labs = ["普通預金", "定期3か月\n（300万円未満）", "定期1年\n（300万円未満）", "定期5年\n（300万円未満）", "定期1年\n（1千万円以上）"]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    w = 0.38; xs = np.arange(len(order))
    for k, (cy, col) in enumerate(zip(cyc.cycle.unique(), (C[5], C[0]))):
        v = [float(cyc[(cyc.cycle == cy) & (cyc.series == s)].ratio.iloc[0]) for s in order]
        dc = float(cyc[cyc.cycle == cy].call_change.iloc[0])
        b = ax.bar(xs + (k - 0.5) * w, v, w, color=col, label=f"{cy}：コール +{dc:.2f}ポイント")
        for xi, vi in zip(xs + (k - 0.5) * w, v):
            ax.text(xi, vi + 0.012, f"{vi:.2f}", ha="center", fontsize=8.5, color=INK)
    ax.axhline(1, color=INK2, lw=0.8, ls="--"); ax.text(len(order) - 0.5, 1.0, "全部映ると1.0", fontsize=8, color=INK2, ha="right", va="bottom")
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("預金金利の上げ幅 ÷ コールレートの上げ幅"); ax.set_ylim(0, 1.3)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    finish(fig, ax, "2024年からの局面は、どの預金でも映り方が2006〜08年より小さい（店頭表示金利）")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.18)
    fig.savefig(F / "fig2_passthrough_by_type.png", dpi=150, metadata=META); plt.close(fig)

    # 図3：店頭表示と新規受入（実際に受け入れた金利）
    fig, ax = plt.subplots(figsize=(9, 5.2))
    sub = df.index >= "202301"
    ax.plot(x[sub], df.call_avg[sub], color=INK, lw=1.6, label="無担保コールレート（月平均）")
    ax.plot(x[sub], df.new_td_large[sub], color=C[4], lw=1.8, label="定期・新規受入の平均（1千万円以上）")
    ax.plot(x[sub], df.new_td_small[sub], color=C[2], lw=1.8, label="定期・新規受入の平均（300万円未満）")
    ax.plot(x[sub], df.td1y_large[sub], color=C[1], lw=1.4, ls="--", label="店頭表示：定期1年（1千万円以上）")
    ax.plot(x[sub], df.ordinary[sub], color=C[0], lw=1.4, ls="--", label="店頭表示：普通預金")
    ax.set_ylabel("年利（%）")
    ax.legend(frameon=False, fontsize=8.8, loc="upper left")
    r_l = m["cycle_new"]["局面2（2024/2→2026/9）|new_td_large"]["ratio"]; r_s = m["cycle_new"]["局面2（2024/2→2026/9）|new_td_small"]["ratio"]
    finish(fig, ax, f"実際に受け入れた大口の定期は、コールとほぼ同じ幅で上がった（比 {r_l:.2f}、小口 {r_s:.2f}）")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.12)
    fig.savefig(F / "fig3_posted_vs_new.png", dpi=150, metadata=META); plt.close(fig)

    # 図4：問い直し 利上げと利下げ
    comp = pd.read_csv(R / "requestion_hike_vs_cut.csv")
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 5.0), sharey=True)
    for ax, h, t in ((axs[0], "ratio_h1_mean", "1か月後"), (axs[1], "ratio_h3_mean", "3か月後")):
        for k, (kind, col) in enumerate((("利上げ", C[0]), ("利下げ", C[1]))):
            v = [float(comp[(comp.kind == kind) & (comp.series == s)][h].iloc[0]) for s in order]
            ax.bar(xs + (k - 0.5) * w, v, w, color=col, label=f"{kind}（1か月後は{int(comp[(comp.kind == kind)].n_h1.max())}回、3か月後は{int(comp[(comp.kind == kind)].n_events.max())}回の平均）")
            for xi, vi in zip(xs + (k - 0.5) * w, v):
                ax.text(xi, vi + 0.01, f"{vi:.2f}", ha="center", fontsize=7.5, color=INK)
        ax.set_xticks(xs); ax.set_xticklabels(["普通", "定期\n3か月", "定期\n1年", "定期\n5年", "定期1年\n大口"], fontsize=8.8)
        ax.set_title(t, fontsize=10.5, color=INK2); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    axs[0].set_ylabel("預金金利の動き ÷ コールレートの動き"); axs[0].legend(frameon=False, fontsize=8.8, loc="upper left")
    fig.suptitle("下げのときは定期預金が1か月目から大きく動く。3か月後にはほぼ並ぶ", x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.012, SRC, fontsize=7.2, color=INK2)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.17, wspace=0.08)
    fig.savefig(F / "fig4_hikes_vs_cuts.png", dpi=150, metadata=META); plt.close(fig)

if __name__ == "__main__":
    main()
