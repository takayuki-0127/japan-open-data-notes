"""04 図：figures/ に5枚"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C = ["#3b6ea5", "#d1603d", "#4a9a6a", "#8a63a8", "#c9a227", "#5a5a5a", "#2a9d8f", "#b5485d"]


def fig1(t):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    sel = [("total", "調査産業計"), ("mining", "鉱業"), ("forestry", "林業"), ("constr_spec", "建設業（職別・設備工事業）"),
           ("transport", "運輸業"), ("manuf", "製造業"), ("service", "サービス業（一部）"), ("trade", "卸売・小売業")]
    for i, (k, lab) in enumerate(sel):
        g = t[(t.ind == k) & (t["size"] == "100+") & (t.old_scope == 0) & (t.fr > 0)].sort_values("year")
        ax.plot(g.year, g.fr, marker="o" if k == "total" else None, ms=3, lw=2.6 if k == "total" else 1.6, color=C[i], label=lab)
    ax.set_yscale("log"); ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
    for y in (1992, 2004, 2008):
        ax.axvline(y, color="#bbb", lw=0.8, ls=":")
    ax.text(2004.3, 75, "産業分類・調査範囲の\n変更（1992・2004・2008年）", fontsize=8.5, color="#777")
    ax.set_xlabel("年"); ax.set_ylabel("度数率（100万延べ実労働時間あたりの死傷者数、対数目盛）")
    ax.set_title("事業所規模100人以上の度数率：1990年ごろまで大きく下がり、その後は横ばいか上向き")
    ax.legend(ncol=2, fontsize=9, frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(F / "f188_1_long_run_frequency.png", dpi=150); plt.close(fig)


def fig2(a):
    a = a[(a["size"] == "100+") & (a.measure == "度数率") & a.period.isin(["1965-1990", "1990-2010", "2010-2024"])]
    order = ["調査産業計", "鉱業", "建設業（職別・設備工事業）", "建設業（総合工事業）", "製造業", "運輸業", "電気・ガス・水道業", "サービス業（一部）", "林業（農業，林業）", "卸売・小売業"]
    fig, ax = plt.subplots(figsize=(9, 5.8))
    for j, (per, col) in enumerate(zip(["1965-1990", "1990-2010", "2010-2024"], [C[0], C[4], C[1]])):
        for i, ind in enumerate(order):
            r = a[(a.ind_ja == ind) & (a.period == per)]
            if r.empty:
                continue
            r = r.iloc[0]; y = i + (j - 1) * 0.25
            ax.errorbar(r.pct, y, xerr=[[r.pct - r.lo], [r.hi - r.pct]], fmt="o", color=col, ms=5, capsize=2, label=per if i == 0 or (ind == "建設業（総合工事業）" and j == 0) else None)
    h, l = ax.get_legend_handles_labels(); u = dict(zip(l, h)); ax.legend(u.values(), [k.replace("-", "〜") + "年" for k in u.keys()], frameon=False, loc="lower right")
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.invert_yaxis()
    ax.set_xlabel("度数率の年あたり変化率（%、95%区間）"); ax.set_title("期間ごとの変化：2010年以降はほぼすべての産業で上向き（規模100人以上）")
    fig.tight_layout(); fig.savefig(F / "f188_2_change_by_period.png", dpi=150); plt.close(fig)


def fig3(b, sen):
    full = b[b.period == "2012-2025"].sort_values("pct"); pre = b[b.period == "2012-2019"].set_index("ind_ja")
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.4), gridspec_kw={"width_ratios": [1.15, 1]})
    for i, r in enumerate(full.itertuples()):
        ax[0].errorbar(r.pct, i, xerr=[[r.pct - r.lo], [r.hi - r.pct]], fmt="o", color=C[1] if r.pct > 0 else C[0], capsize=2)
        if r.ind_ja in pre.index:
            ax[0].plot(pre.loc[r.ind_ja, "pct"], i, marker="|", ms=12, color="#555")
    ax[0].axvline(0, color="#444", lw=0.8); ax[0].set_yticks(range(len(full))); ax[0].set_yticklabels(full.ind_ja)
    ax[0].set_xlabel("年千人率の年あたり変化率（%、2012〜2025年）\n縦線はコロナ前（2012〜2019年）")
    ax[0].set_title("労働者あたり：減ったのは建設・製造・金融")
    for i, (k, col) in enumerate([("建設業", C[0]), ("製造業", C[2]), ("保健衛生業", C[1]), ("商業", C[4]), ("接客娯楽業", C[3]), ("全産業", "#333")]):
        ax[1].plot(sen.year, sen[k] / sen[k].iloc[0] * 100, color=col, lw=2.4 if k == "全産業" else 1.7, label=k)
    ax[1].axhline(100, color="#999", lw=0.7); ax[1].set_ylabel("年千人率（2012年＝100）"); ax[1].set_xlabel("年")
    ax[1].set_title("増えたのは保健衛生・商業・接客娯楽"); ax[1].legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(F / "f188_3_per_worker_trend.png", dpi=150); plt.close(fig)


def fig4(d, s):
    x = d[(d.y0 == 2012) & (d.y1 == 2025) & (d.forestry_share == 0) & (d.weights == "mid")].copy()
    x["tot"] = x.mix + x.within; x = x.sort_values("tot")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    y = np.arange(len(x))
    ax.barh(y - 0.2, x.within, 0.38, color=C[1], label="産業の中の率の変化")
    ax.barh(y + 0.2, x.mix, 0.38, color=C[0], label="産業の構成（雇用者の割合）の変化")
    ax.set_yticks(y); ax.set_yticklabels(x.ind_ja); ax.axvline(0, color="#444", lw=0.8)
    ax.set_xlabel("全産業の年千人率の変化への寄与（ポイント、2012→2025年）")
    ax.set_title(f"全産業は {s['R0']:.1f}→{s['R1']:.1f}：率の上昇（+{s['within']:.2f}）を構成の変化（{s['mix']:.2f}）が打ち消した")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(F / "f188_4_shift_share.png", dpi=150); plt.close(fig)


def fig5(dd):
    inds = ["全産業", "製造業", "建設業", "運輸業", "卸売・小売業", "林業"]
    dens = ["労働者数（年千人率・休業4日以上）", "労働時間（度数率・規模100+人）", "労働時間（度数率・規模30-99人）"]
    labs = ["労働者あたり（年千人率・全規模・休業4日以上）", "労働時間あたり（度数率・100人以上）", "労働時間あたり（度数率・30〜99人）"]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for j, (dn, lb, col) in enumerate(zip(dens, labs, [C[0], C[1], C[4]])):
        for i, ind in enumerate(inds):
            r = dd[(dd.ind == ind) & (dd.denom == dn)]
            if r.empty:
                continue
            r = r.iloc[0]; yy = i + (j - 1) * 0.25
            ax.errorbar(r.pct, yy, xerr=[[r.pct - r.lo], [r.hi - r.pct]], fmt="o", color=col, capsize=2, label=lb if i == 0 else None)
    ax.axvline(0, color="#444", lw=0.8); ax.set_yticks(range(len(inds))); ax.set_yticklabels(inds); ax.invert_yaxis()
    ax.set_xlabel("年あたり変化率（%、2012〜2024年、95%区間）")
    ax.set_title("分母と統計を替えると向きが変わる：労働者あたりは横ばい、時間あたりは上向き")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    fig.set_size_inches(9, 6.2); fig.tight_layout(); fig.savefig(F / "f188_5_denominator.png", dpi=150); plt.close(fig)


def main():
    t = pd.read_csv(D / "tidy_dosu.csv"); sen = pd.read_csv(D / "sennin_rate.csv")
    a = pd.read_csv(R / "a_trend_by_period.csv"); b = pd.read_csv(R / "b_poisson_by_industry.csv")
    d = pd.read_csv(R / "c_shift_share_detail.csv"); s = pd.read_csv(R / "c_shift_share_summary.csv")
    s = s[(s.y0 == 2012) & (s.y1 == 2025) & (s.forestry_share == 0) & (s.weights == "mid")].iloc[0]
    dd = pd.read_csv(R / "d_denominator.csv")
    fig1(t); fig2(a); fig3(b, sen); fig4(d, s); fig5(dd)
    print("figs ok")


if __name__ == "__main__":
    main()
