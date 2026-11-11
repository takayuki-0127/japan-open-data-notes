"""04 図：figures/ に6枚。"""
import json, pathlib, math
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",):
    try: fm.fontManager.addfont(f)
    except Exception: pass
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150})
B = pathlib.Path(__file__).resolve().parents[1]
P, R, F = B / "data" / "processed", B / "results", B / "figures"
F.mkdir(exist_ok=True)
M = json.loads((R / "main.json").read_text())
jma = pd.read_csv(P / "jma_counts.csv").set_index("year")
pay = pd.read_csv(P / "payouts_fy_real.csv").set_index("fy")
rev = pd.read_csv(R / "D_revisions.csv")
rob = pd.read_csv(R / "A_hazard_trends.csv")
defl = pd.read_csv(B / "data" / "raw" / "deflator_from_F256.csv").set_index("fy")
C1, C2, C3, C4 = "#2b6cb0", "#dd6b20", "#718096", "#38a169"
# 図1
fig, ax = plt.subplots(figsize=(9, 4.8))
y = jma["amdhour50mm"]
ax.bar(y.index, y.values, color="#a0c4e8", label="年間回数")
t = M["H1"]["trend"]; yr = np.arange(1976, 2026)
a = np.log(y.values).mean() - t["b"] * (yr - 2000).mean()
ax.plot(yr, np.exp(a + t["b"] * (yr - 2000)), color=C1, lw=2, label=f"傾き（年 +{t['pct_per_yr']:.1f}%）")
for s, e in ((1976, 1985), (2016, 2025)):
    m = y.loc[s:e].mean(); ax.hlines(m, s - 0.4, e + 0.4, color=C2, lw=2.5)
    ax.text((s + e) / 2, m + 12, f"{s}〜{e}年 平均{m:.0f}回", ha="center", color=C2)
ax.set_title("1時間に50mm以上の雨の年間回数（アメダス1,300地点あたり）"); ax.set_ylabel("回"); ax.legend(loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig(F / "f284_1_heavy_rain_count.png"); plt.close(fig)
# 図2
lab = {"amdhour50mm": "1時間50mm", "amdhour80mm": "1時間80mm", "amdhour100mm": "1時間100mm", "amd3hour100mm": "3時間100mm",
       "amd3hour150mm": "3時間150mm", "amdday200mm": "日200mm", "amdday300mm": "日300mm"}
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(len(rob))
ax.errorbar(rob["pois_pct"], x, xerr=[rob["pois_pct"] - rob["pois_lo"], rob["pois_hi"] - rob["pois_pct"]], fmt="o", color=C1, capsize=4, label="準ポアソン（95%区間）")
ax.plot(rob["ols_pct"], x + 0.2, "s", color=C2, label="対数の直線")
ax.axvline(0, color="k", lw=0.8); ax.set_yticks(x); ax.set_yticklabels([lab[s] for s in rob["series"]]); ax.invert_yaxis()
ax.set_xlabel("1年あたりの増え方（%）"); ax.set_title("しきい値を変えても、大雨の回数は年1〜2%ずつ増えている"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
fig.tight_layout(); fig.savefig(F / "f284_2_trend_by_threshold.png"); plt.close(fig)
# 図3：料率の累計 vs 大雨10年平均 vs 修理費（2012年=100）
fig, ax = plt.subplots(figsize=(9, 4.8))
idx = 100.0; xs = [2012.0]; ys = [100.0]
for _, r in rev.iterrows():
    d = pd.Timestamp(r["filing_date"]); fy = d.year + (d.month - 1) / 12
    xs += [fy, fy]; ys += [idx, idx * r["mult"]]; idx *= r["mult"]
xs.append(2025.5); ys.append(idx)
ax.plot(xs, ys, color=C2, lw=2.5, label=f"参考純率の累計（5回、+{M['H2']['cum_pct']:.0f}%）")
roll = jma["amdhour50mm"].rolling(10).mean()
r12 = roll.loc[2012]
ax.plot(roll.loc[2012:].index, 100 * roll.loc[2012:] / r12, color=C1, lw=2, label="1時間50mm以上の回数（直前10年平均）")
dh = defl["defl_house"]; ax.plot(dh.loc[2012:2025].index, 100 * dh.loc[2012:2025] / dh.loc[2012], color=C4, lw=2, ls="--", label="修理費（建設工事費デフレーター 住宅総合）")
for _, r in rev.iterrows():
    d = pd.Timestamp(r["filing_date"]); ax.annotate(f"+{r['avg_change_pct']}%", (d.year + (d.month - 1) / 12, 92), ha="center", color=C2, fontsize=9)
ax.set_ylim(88, 150); ax.set_ylabel("2012年＝100"); ax.set_title("料率は大雨の回数の伸びより大きく上がった（料率は届出の時点、ほかはデータの年）", fontsize=10.5); ax.legend(frameon=False, loc="upper left", fontsize=9.5)
fig.tight_layout(); fig.savefig(F / "f284_3_rate_vs_hazard_cost.png"); plt.close(fig)
# 図4：年度の支払保険金（火災保険、実質）と大雨回数
fig, ax = plt.subplots(figsize=(9, 4.8))
bot = np.zeros(len(pay))
for col, c in (("台風", C2), ("大雨", C1), ("その他（雪・ひょう・突風・低気圧）", C3)):
    ax.bar(pay.index, pay[col], bottom=bot, color=c, label=col); bot += pay[col].values
ax.set_ylabel("支払保険金（億円、2025年度の修理費で換算）"); ax.set_ylim(0, 19000)
ax2 = ax.twinx(); ax2.plot(jma.loc[2012:2025].index, jma.loc[2012:2025, "amdhour50mm"], "o-", color="k", lw=1.2, label="1時間50mm以上の回数（右）")
ax2.set_ylabel("回"); ax2.set_ylim(0, 700); ax2.spines["top"].set_visible(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right", fontsize=9)
ax.set_title(f"支払保険金は台風の年で決まり、大雨の回数とは弱くしか連動しない（順位相関 {M['H3']['spearman_total_50mm']:.2f}）")
fig.tight_layout(); fig.savefig(F / "f284_4_payouts_vs_rain.png"); plt.close(fig)
# 図5：遅れ L とずれ
fig, ax = plt.subplots(figsize=(8.5, 4.6))
L = np.linspace(0, 12, 100)
for s, c in (("amdhour50mm", C1), ("amdhour100mm", C2), ("amdday300mm", C3)):
    g = math.log(1 + rob.set_index("series").loc[s, "pois_pct"] / 100)
    ax.plot(L, 100 * (np.exp(g * L) - 1), color=c, lw=2, label=f"{lab[s]}（年 +{rob.set_index('series').loc[s, 'pois_pct']:.1f}%）")
ax.axhline(M["H4"]["mean_rev_pct"], color="k", ls="--", lw=1); ax.text(0.2, M["H4"]["mean_rev_pct"] + 0.4, f"1回の改定の平均 +{M['H4']['mean_rev_pct']:.1f}%", fontsize=9.5)
for k, v in M["H4"]["lags"].items():
    ax.axvline(v["L"], color="#cbd5e0", lw=1)
ax.text(M["H4"]["lags"]["main(gap+1+2.5)"]["L"] + 0.1, 15.5, "基準の遅れ\n約4年", fontsize=9)
ax.text(M["H4"]["lags"]["long_window(+5: 10年平均の真ん中)"]["L"] + 0.1, 15.5, "10年平均の\n真ん中から\n約9年", fontsize=9)
ax.set_xlabel("基データの終わりから、料率が使われる真ん中までの年数"); ax.set_ylabel("取り込まれていない分（%）"); ax.set_ylim(0, 22)
ax.set_title("大雨の増え方だけなら、遅れによるずれは数%"); ax.legend(frameon=False, loc="upper left", fontsize=9.5)
fig.tight_layout(); fig.savefig(F / "f284_5_lag_gap.png"); plt.close(fig)
# 図6：問い直し（対数で分けた割合）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
d = M["reask"]["decomp"]; keys = ["amdhour50mm", "amdday200mm", "amd3hour100mm"]
yy = np.arange(len(keys)); left = np.zeros(len(keys))
for part, c, nm in (("hazard_share", C1, "大雨の回数"), ("repair_share", C4, "修理費"), ("other_share", C3, "その他（残り）")):
    v = np.array([100 * d[k][part] for k in keys])
    ax.barh(yy, v, left=np.where(v < 0, 0, left) if part == "other_share" else left, color=c, label=nm)
    left = left + np.where(v > 0, v, 0)
for i, k in enumerate(keys):
    ax.text(109, i, f"残り {100*d[k]['other_share']:+.0f}%", va="center", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels([lab[k] + "で測る" for k in keys]); ax.invert_yaxis(); ax.set_xlim(-10, 128)
ax.set_xlabel(f"料率の累計 +{M['H2']['cum_pct']:.0f}% のうちの割合（対数で分けた、%）"); ax.set_title("問い直し：料率の累計を機械的に分けた割合（単位の違いに注意）"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=9)
fig.tight_layout(); fig.savefig(F / "f284_6_decomposition.png"); plt.close(fig)
print(sorted(p.name for p in F.glob("*.png")))
