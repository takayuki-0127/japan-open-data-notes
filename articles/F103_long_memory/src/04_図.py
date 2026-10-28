"""図を作る（5枚）"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

FIG.mkdir(exist_ok=True)
C1, C2, C3, CG = "#2b6cb0", "#dd6b20", "#2f855a", "#888888"

# ---------- 図1：自己相関の減り方（東京の電力需要の残差） ----------
ac = pd.read_csv(RES / "power_acf.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for a, logx in zip(ax, (False, True)):
    s = "暦と気温"
    a.plot(ac.lag, ac[f"data_{s}"], color=C1, lw=1.2, label="実際の残差")
    a.plot(ac.lag, ac[f"ar_{s}"], color=C2, lw=1.6, ls="--", label=f"AR({int(ac[f'ar_p_{s}'].iloc[0])}) で当てた場合")
    a.plot(ac.lag, ac[f"arfima_{s}"], color=C3, lw=1.6, label="ARFIMA(1,d,0) で当てた場合")
    a.axhline(0, color=CG, lw=0.6)
    a.set_xlabel("何日離れているか（日）")
    if logx:
        a.set_xscale("log")
        a.set_title("横軸を対数にしたもの")
    else:
        a.set_title("東京の電力需要の残差：何日前と似ているか")
        a.set_ylabel("自己相関")
    a.set_ylim(-0.1, 1)
ax[0].legend(fontsize=9)
fig.text(0.01, 0.01, "残差＝日次の需要（対数）から、気温・曜日・祝日・お盆・年末年始・GW・コロナ期・月の影響を回帰で除いたもの。2016年4月〜2026年9月。",
         fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "fig1_acf_power.png", dpi=150)
plt.close(fig)

# ---------- 図2：シミュレーション（推定法の当たり方） ----------
sm = pd.read_csv(RES / "sim_summary.csv")
sm = sm[sm.n == 3834]
cases = ["白色雑音（d=0）", "本物の長期記憶（d=0.3）", "AR(1)、φ=0.8（d=0）",
         "長期記憶＋AR（d=0.3, φ=0.5）", "水準の段差10回（d=0）"]
truth = [0, 0.3, 0, 0.3, 0]
ests = ["LW m=n^0.5", "LW m=n^0.6", "LW m=n^0.7", "LW m=n^0.8", "GPH m=n^0.6", "ARFIMA(1,d,0)", "DFA", "R/S"]
fig, ax = plt.subplots(figsize=(11, 5))
w = 0.1
cols = plt.cm.viridis(np.linspace(0, 0.9, len(ests)))
for j, e in enumerate(ests):
    sub = sm[sm.estimator == e].set_index("case").loc[cases]
    xs = np.arange(len(cases)) + (j - len(ests) / 2 + 0.5) * w
    ax.errorbar(xs, sub["mean"], yerr=[sub["mean"] - sub["q05"], sub["q95"] - sub["mean"]],
                fmt="o", ms=4, color=cols[j], label=e, capsize=0, lw=1)
for i, t in enumerate(truth):
    ax.hlines(t, i - 0.45, i + 0.45, color="red", lw=1.5, ls=":")
ax.set_xticks(range(len(cases)))
ax.set_xticklabels([c.replace("（", "\n（") for c in cases], fontsize=9)
ax.set_ylabel("推定された d（点＝平均、線＝90%の範囲）")
ax.set_title("推定法の当たり方：長さ3,834の系列を200回ずつ作って推定（赤の点線が本当の d）")
ax.legend(ncol=4, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig2_simulation.png", dpi=150)
plt.close(fig)

# ---------- 図3：電力需要の d（推定法×設定） ----------
pe = pd.concat([pd.read_csv(RES / "power_estimates.csv"), pd.read_csv(RES / "power_estimates_extra.csv")])
specs = [("東京", "暦と気温"), ("東京", "暦と気温＋年度"), ("東京", "年周期（フーリエ4組）を足す"), ("東京", "暦と気温（前半）"),
         ("東京", "暦と気温（後半）"), ("東京", "暦と気温（週平均）"),
         ("東京", "暦と気温（関西と同じ期間）"), ("関西", "暦と気温")]
labels = ["東京：本体\n2016〜2026", "東京：年度の違い\nも除く", "東京：年周期\nも除く", "東京：前半\n2016〜2021",
          "東京：後半\n2021〜2026", "東京：週平均\nにして", "東京：2024〜\n2026だけ", "関西：2024〜\n2026"]
cols_e = [("lw_0.5", "LW m=n^0.5"), ("lw_0.6", "LW m=n^0.6"), ("lw_0.7", "LW m=n^0.7"), ("lw_0.8", "LW m=n^0.8"),
          ("gph_0.6", "GPH m=n^0.6"), ("arfima_d", "ARFIMA"), ("dfa_d", "DFA"), ("rs_d", "R/S")]
fig, ax = plt.subplots(figsize=(12, 4.8))
for j, (c, lab) in enumerate(cols_e):
    ys = [pe[(pe.area == a) & (pe.spec == s)][c].iloc[0] for a, s in specs]
    xs = np.arange(len(specs)) + (j - len(cols_e) / 2 + 0.5) * 0.1
    ax.scatter(xs, ys, color=cols[j], s=22, label=lab, zorder=3)
main = pe[(pe.area == "東京") & (pe.spec == "暦と気温")].iloc[0]
ax.axhline(0, color=CG, lw=0.8)
ax.set_xticks(range(len(specs)))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("推定された d")
ax.set_title("電力需要の残差の d：東京の10年分では0.25〜0.6、2024年4月からの2年半だけでは0〜0.2")
ax.set_ylim(-0.12, 0.85)
ax.legend(ncol=4, fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "fig3_power_d.png", dpi=150)
plt.close(fig)

# ---------- 図4：物価の品目別の d（2000〜2026、消費税の月を除く） ----------
ce = pd.read_csv(RES / "cpi_estimates.csv")
m = ce[(ce.period == "2000〜2026") & ce.tax_dummy].copy()
SKIP = {"生鮮魚介（再掲）", "生鮮野菜（再掲）", "生鮮果物（再掲）", "持家の帰属家賃を除く住居", "持家の帰属家賃を除く家賃",
        "教育関係費", "教養娯楽関係費", "情報通信関係費", "シャツ・セーター類", "下着類"}
agg = ["総合", "生鮮食品を除く総合", "持家の帰属家賃を除く総合", "持家の帰属家賃及び生鮮食品を除く総合",
       "生鮮食品及びエネルギーを除く総合", "食料（酒類を除く）及びエネルギーを除く総合", "エネルギー"]
m = m[~m.name.isin(SKIP)].sort_values("lw_0.6")
fig, ax = plt.subplots(figsize=(8.5, 13))
y = np.arange(len(m))
isagg = m.name.isin(agg).values
ax.errorbar(m["lw_0.6"], y, xerr=1.96 * m["lw_0.6_se"], fmt="none", ecolor="#bbb", lw=1)
ax.scatter(m["lw_0.6"][~isagg], y[~isagg], color=C1, s=18, zorder=3, label="中分類など")
ax.scatter(m["lw_0.6"][isagg], y[isagg], color=C2, s=30, marker="D", zorder=3, label="総合・まとめた系列")
ax.scatter(m["arfima_d"], y, color=C3, s=12, marker="x", zorder=3, label="ARFIMA(1,d,0) の d")
ax.set_yticks(y)
ax.set_yticklabels(m["name"], fontsize=7.5)
ax.axvline(0, color=CG, lw=0.8)
ax.axvline(0.5, color=CG, lw=0.6, ls=":")
ax.set_xlabel("推定された d（局所Whittle、m=n^0.6、線は95%区間）")
ax.set_title("物価の前月比の「記憶の長さ」（2000年1月〜2026年9月）\n季節と消費税の月を除いたもの", fontsize=11)
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(FIG / "fig4_cpi_items_d.png", dpi=150)
plt.close(fig)

# ---------- 図5：衝撃がどれだけ残るか ----------
ir = pd.read_csv(RES / "impulse.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
g = ir[ir.series == "電力需要（東京、日）"]
g = g[g.h >= 1]
ax[0].plot(g.h, g.arfima, color=C3, lw=1.8, label=f"ARFIMA（d={g.d.iloc[0]:.2f}）：べき乗でゆっくり減る")
ax[0].plot(g.h, g.ar.clip(lower=1e-6), color=C2, lw=1.8, ls="--", label=f"AR({int(g.ar_p.iloc[0])})：指数で速く減る")
ax[0].set_xscale("log")
ax[0].set_yscale("log")
ax[0].set_ylim(1e-4, 1.2)
for h in (30, 90, 365):
    v = g.set_index("h").loc[h]
    ax[0].annotate(f"{h}日後\nARFIMA {v.arfima:.3f}\nAR {v.ar:.4f}", (h, v.arfima), fontsize=7.5,
                   xytext=(0, 18), textcoords="offset points", ha="center")
ax[0].set_xlabel("衝撃から何日後か")
ax[0].set_ylabel("1の衝撃のうち残っている量（対数）")
ax[0].set_title("電力需要の衝撃は、どれだけ後まで残るか（東京）")
ax[0].legend(fontsize=9)
ro = pd.read_csv(RES / "cpi_rolling.csv", parse_dates=["start", "end", "mid"])
for nm, c in [("総合", C1), ("生鮮食品を除く総合", C2), ("生鮮食品及びエネルギーを除く総合", C3), ("生鮮食品", CG)]:
    g = ro[ro.name == nm]
    ax[1].plot(g.end.dt.year + (g.end.dt.month - 1) / 12, g["lw_0.6"], color=c, lw=1.8, label=nm, marker="o", ms=2.5)
ax[1].fill_between([1984, 2027], -0.2, 0.2, color="#eee", zorder=0)
ax[1].set_xlabel("15年の窓の終わりの年（例：2000 は1986〜2000年の15年）")
ax[1].set_ylabel("推定された d（局所Whittle）")
ax[1].set_title("物価の前月比の d は、どの15年を見るかで大きく動く")
ax[1].legend(fontsize=8, loc="lower left")
ax[1].set_xlim(1984, 2027)
ax[1].text(1995.5, -0.185, "灰色：0の±0.2（窓1つの95%区間のおよその幅）", fontsize=7.5, color="#555")
ax[1].axhline(0, color=CG, lw=0.6)
fig.tight_layout()
fig.savefig(FIG / "fig5_impulse.png", dpi=150)
plt.close(fig)
print("図を保存しました")
