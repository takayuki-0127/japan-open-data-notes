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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5cc7", "#8a8984"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「時系列統計データ検索サイト」（貸出先別貸出金）をもとに作成者が加工して作成"
META = {"Software": None}

def qx(idx):
    return np.array([int(q[:4]) + (int(q[-1]) - 1) / 4 + 0.125 for q in idx])

def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)

def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    last = m["last_quarter"]
    # 図1：長い推移（3勘定合算）
    lr = pd.read_csv(R / "long_shares.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for s, col, lab in (("個人", C[2], "個人"), ("製造業", C[0], "製造業"), ("不動産業", C[1], "不動産業"), ("地方公共団体", C[6], "地方公共団体")):
        v = lr[f"3acc|{s}"].dropna() * 100
        ax.plot(qx(v.index), v.values, color=col, lw=2.0 if s == "不動産業" else 1.5, label=lab)
    ax.axvline(2009.375, color=INK2, lw=0.8, ls=":"); ax.text(2009.5, 44, "業種分類の改定\n（2009年6月末）", fontsize=8, color=INK2, va="top")
    v = lr["3acc|不動産業"].dropna() * 100
    ax.annotate(f"{v.iloc[-1]:.1f}%", (qx(v.index)[-1], v.iloc[-1]), xytext=(4, 4), textcoords="offset points", fontsize=9, color=C[1])
    ax.set_ylabel("総貸出に占める割合（%）"); ax.set_ylim(0, 50)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right", ncol=4)
    finish(fig, ax, "不動産業の割合は、1970年以降でいちばん高い（国内銀行、3勘定合算）")
    fig.subplots_adjust(left=0.08, right=0.96, top=0.9, bottom=0.12)
    fig.savefig(F / "fig1_long_shares.png", dpi=150, metadata=META); plt.close(fig)

    # 図2：2013年3月末からの増加の内訳
    con = pd.read_csv(R / "contributions_bank.csv"); c = con[con["from"] == "2013Q1"]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    labs = [g.replace("（割賦返済分）", "\n（割賦返済分）").replace("・国内店名義現地貸", "\n・国内店名義現地貸") for g in c.group]
    cols = [C[0], C[1], C[1], C[1], C[5], C[6], C[6], C[2], C[2], C[6]]
    y = np.arange(len(c))[::-1]
    ax.barh(y, c.increase / 1e4, color=cols)
    for yi, inc, sh in zip(y, c.increase / 1e4, c.share_of_increase * 100):
        ax.text(inc + 0.5, yi, f"{inc:.1f}兆円（{sh:.1f}%）", va="center", fontsize=8.8, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.8)
    ax.set_xlabel("残高の増加（兆円）"); ax.set_xlim(0, 78)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_title(f"2013年3月末→{last[:4]}年9月末の増加{m['increase_2013_tn']:.0f}兆円：不動産業{m['contrib_2013_realestate']:.0f}%、個人{m['contrib_2013_individual']:.0f}%", loc="left", fontsize=12.5, color=INK, pad=12)
    fig.text(0.01, 0.012, SRC + "（国内銀行・銀行勘定。かっこは増加全体に占める割合）", fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.25, right=0.97, top=0.9, bottom=0.14)
    fig.savefig(F / "fig2_contributions.png", dpi=150, metadata=META); plt.close(fig)

    # 図3：不動産業の中の構成
    sh = pd.read_csv(R / "shares_bank.csv", index_col=0)
    lv = pd.read_csv(R / "realestate_mix_bank.csv", index_col=0)
    tot = pd.read_csv(ROOT / "data" / "loans_long.csv")
    tot = tot[(tot.account == "bank") & (tot["size"] == "all")].pivot(index="quarter", columns="sector", values="oku_yen").loc["2009Q2":]
    parts = {"個人による貸家業": tot["個人による貸家業"], "SPC（不動産の流動化などの特別目的会社）": tot["不動産流動化等を目的とするSPC"],
             "その他の不動産業": tot["不動産業"] - tot["個人による貸家業"] - tot["不動産流動化等を目的とするSPC"]}
    fig, ax = plt.subplots(figsize=(9, 5.2))
    xx = qx(tot.index)
    ax.stackplot(xx, *[v.values / 1e4 for v in parts.values()], labels=list(parts.keys()), colors=[C[3], C[4], C[1]], alpha=0.9)
    mx = m["re_mix"]
    for q, xv in (("2009Q2", 2009.5), (last, qx([last])[0] - 0.6)):
        ax.text(xv, float(tot.loc[q, "不動産業"]) / 1e4 + 2, f"貸家業 {mx[q]['不動産業：個人による貸家業']:.0f}%\nSPC {mx[q]['不動産業：SPC']:.0f}%\nその他 {mx[q]['不動産業：その他']:.0f}%", fontsize=8.5, color=INK, ha="left" if q == "2009Q2" else "right")
    ax.set_ylabel("不動産業向けの残高（兆円）"); ax.set_ylim(0, 140)
    ax.set_xticks([2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]); ax.set_xticklabels([f"{y}年" for y in range(2010, 2027, 2)])
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0.18, 1.0))
    finish(fig, ax, "不動産業の中では、個人による貸家業の割合が下がり、SPC とその他が増えた")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    fig.savefig(F / "fig3_realestate_mix.png", dpi=150, metadata=META); plt.close(fig)

    # 図4：問い直し 不動産業の増加を規模で
    rq = m["requestion"]
    fig, ax = plt.subplots(figsize=(9, 5.0))
    s = rq["sme_re_increase_tn_2013"]
    left = 0
    for k, col in (("その他", C[1]), ("SPC", C[4]), ("個人による貸家業", C[3])):
        ax.barh(2, s[k], left=left, color=col, label=f"中小企業のうち {k}")
        ax.text(left + s[k] / 2, 2, f"{s[k]:.1f}", ha="center", va="center", fontsize=9, color="white")
        left += s[k]
    ax.barh(1, rq["mid_re_increase_tn_2013"], color=C[6]); ax.barh(0, rq["large_re_increase_tn_2013"], color=C[0])
    ax.text(left + 0.8, 2, f"{left:.1f}兆円（{rq['re_increase_share_2013']['sme']:.0f}%）", va="center", fontsize=9)
    ax.text(rq["mid_re_increase_tn_2013"] + 0.8, 1, f"{rq['mid_re_increase_tn_2013']:.1f}兆円（{rq['re_increase_share_2013']['mid']:.0f}%）", va="center", fontsize=9)
    ax.text(rq["large_re_increase_tn_2013"] + 0.8, 0, f"{rq['large_re_increase_tn_2013']:.1f}兆円（{rq['re_increase_share_2013']['large']:.0f}%）", va="center", fontsize=9)
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["大企業", "中堅企業", "中小企業"])
    ax.set_xlabel("不動産業向け残高の増加（兆円、2013年3月末→2026年9月末）"); ax.set_xlim(0, 68)
    ax.legend(frameon=False, fontsize=8.8, loc="lower right")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_title("不動産業の増加の9割は「中小企業」の区分。SPC や個人による貸家業もここに入る", loc="left", fontsize=12.5, color=INK, pad=12)
    fig.text(0.01, 0.012, SRC + "（国内銀行・銀行勘定）", fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.9, bottom=0.16)
    fig.savefig(F / "fig4_realestate_by_size.png", dpi=150, metadata=META); plt.close(fig)

if __name__ == "__main__":
    main()
