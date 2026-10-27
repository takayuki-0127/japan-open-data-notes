import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()
C1, C2, C3, C4, GR = "#1f5fa8", "#d1495b", "#3a8f5c", "#e09f3e", "#888888"

lfs = pd.read_csv(DATA / "lfs_monthly.csv", index_col=0, parse_dates=True)
steps = pd.read_csv(RES / "lfs_steps.csv")
mk = pd.read_csv(DATA / "maikin_monthly.csv", index_col=0, parse_dates=True)

# 1. 15歳以上人口の「いつもとの違い」と切替え月
d = lfs["pop15"].diff()
base = (d.shift(12) + d.shift(-12) + d.shift(24) + d.shift(-24)) / 4
e = (d - base)
sd = steps.query("var=='pop15'")["noise_sd"].iloc[0]
fig, ax = plt.subplots(figsize=(10, 4.6))
ee = e.copy(); ee[ee.index.year == 2011] = np.nan
ax.plot(ee.index, ee.values, color=GR, lw=0.7)
ax.axhspan(-2 * sd, 2 * sd, color="#dde6f2", alpha=0.7, label="±2標準偏差（いつもの揺れ）")
sw = steps.query("var=='pop15'")
for _, r in sw.iterrows():
    t = pd.Timestamp(r["month"] + "-01")
    col = C2 if r["kind"] == "切替え" else C4
    ax.scatter([t], [r["step"]], color=col, s=36, zorder=5)
    if r["month"] in ("1987-01", "1997-01", "2007-01"):
        lab = f"{r['month'][:4]}年{int(r['month'][5:])}月\n推定{r['step']:+.0f}（公表{r['official']:+.0f}）" if not np.isnan(r["official"]) else r["month"]
        ax.annotate(lab, (t, r["step"]), xytext=(6, 8 if r["step"] >= 0 else -26), textcoords="offset points", fontsize=8.5, color=col)
ax.scatter([], [], color=C2, s=36, label="ベンチマーク人口の切替え月")
ax.scatter([], [], color=C4, s=36, label="接続用数値の境目（2005・2010・2015年10月）")
ax.set_ylabel("万人")
ax.set_title("15歳以上人口の月々の変化から、いつもの変化を引いた値（労働力調査、2011年は除く）")
ax.legend(loc="lower left", fontsize=8.5, frameon=False)
ax.text(pd.Timestamp("2010-06-01"), 25, "2012・2017・2022年1月の切替え\n（公表+69万・+35万・+26万）は\n長期系列では接続済みで、段差は見えない", fontsize=8.5, color=C2)
ax.set_ylim(-35, 42)
fig.tight_layout(); fig.savefig(FIG / "f66_lfs_jumps.png"); plt.close(fig)

# 2. 推定した段差と公表のギャップ
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
for ax, v, nm in zip(axes, ["pop15", "emp"], ["15歳以上人口", "就業者"]):
    s = steps.query("var==@v and kind=='切替え'")
    x = np.arange(len(s)); sdv = s["noise_sd"].iloc[0]
    ax.bar(x - 0.2, s["official"], width=0.4, color=C1, label="公表のギャップ（統計局）")
    ax.bar(x + 0.2, s["step"], width=0.4, color=C2, label="データから推定した段差")
    ax.errorbar(x + 0.2, s["step"], yerr=2 * sdv, fmt="none", ecolor="#555", capsize=2, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([m[:4] for m in s["month"]], fontsize=9)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title(f"{nm}（万人、ひげは±2標準偏差）", fontsize=10.5)
for i in (6, 7, 8):
    axes[0].annotate("接続済み", (i, 2), ha="center", fontsize=7.5, color=GR, xytext=(0, -14), textcoords="offset points")
axes[0].legend(fontsize=8.5, frameon=False, loc="upper left")
fig.suptitle("ベンチマーク人口の切替え月の段差：公表値とデータからの推定", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f66_gap_compare.png"); plt.close(fig)

# 3. 接続のしかたと切替え年の増減（就業者）
ct = pd.read_csv(RES / "connect_switch_years.csv", index_col=0)
nc = pd.read_csv(RES / "connected_counterfactual.csv")
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [5, 3]})
ax = axes[0]; x = np.arange(len(ct))
for j, (k, lab, col) in enumerate([("raw", "そのまま（段差を含む）", GR), ("parallel", "平行移動で接続", C1), ("ratio", "比率で接続", C3), ("triangle", "三角修正（5年に配る）", C4)]):
    ax.bar(x + (j - 1.5) * 0.2, ct[k], width=0.2, color=col, label=lab)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in ct.index]); ax.axhline(0, color="k", lw=0.6)
ax.set_ylabel("年平均の前年からの増減（万人）"); ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.set_title("接続されていない切替え年（1982〜2002年）", fontsize=10.5)
ax = axes[1]; x = np.arange(len(nc))
ax.bar(x - 0.2, nc["connected_change"], width=0.4, color=C1, label="今の長期系列（接続済み）")
ax.bar(x + 0.2, nc["if_not_connected"], width=0.4, color=GR, label="接続しなかった場合")
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in nc["year"]]); ax.axhline(0, color="k", lw=0.6)
ax.legend(fontsize=8, frameon=False, loc="upper left"); ax.set_title("接続済みの切替え年（2012〜2022年）", fontsize=10.5)
fig.suptitle("就業者の年平均の増減：切替えの段差をどう扱うかで変わる", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f66_connect.png"); plt.close(fig)

# 4. 毎勤：2024年のベンチマーク更新
x = mk["2023-01":"2025-12"]
fig, ax = plt.subplots(figsize=(10, 4.3))
ax.plot(x.index, x["pub_cash_total"], color=C1, marker="o", ms=3, label="公表の前年同月比")
ax.plot(x.index, x["idxyoy_cash_total"], color=C2, marker="o", ms=3, label="公表の指数から計算した前年同月比")
ax.fill_between(x.index, x["pub_cash_total"], x["idxyoy_cash_total"], color=C2, alpha=0.15)
ax.axvspan(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"), color="#f3eadf", alpha=0.6)
ax.set_ylim(0.4, 5.9)
ax.text(pd.Timestamp("2024-02-01"), 5.3, "2024年1月分でベンチマーク更新\n→ この1年だけ2つがずれる", fontsize=9, color="#7a5a2a")
ax.set_ylabel("%"); ax.legend(fontsize=9, frameon=False, loc="upper left")
ax.set_title("毎月勤労統計の現金給与総額：公表の前年同月比と、指数から計算した前年同月比", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f66_maikin_bench.png"); plt.close(fig)

# 5. 毎勤：本系列と共通事業所
x = mk["2018-01":]
kd = pd.read_csv(RES / "maikin_vs_kyotsu.csv")
fig, axes = plt.subplots(2, 1, figsize=(10, 6.2), gridspec_kw={"height_ratios": [3, 2]}, sharex=False)
ax = axes[0]
ax.plot(x.index, x["pub_scheduled"], color=C1, lw=1.4, label="本系列（公表の前年同月比）")
ax.plot(x.index, x["kyo_scheduled"], color=C3, lw=1.4, label="共通事業所の前年同月比（参考値）")
ax.axhline(0, color="k", lw=0.5); ax.set_ylabel("%"); ax.legend(fontsize=9, frameon=False, loc="upper left")
ax.set_title("きまって支給する給与の前年同月比：本系列と共通事業所", fontsize=11)
ax = axes[1]
s = kd[kd["item"] == "きまって支給する給与"]
ax.bar(s["year"], s["pub_minus_kyotsu"], color=[C2 if v > 0 else C1 for v in s["pub_minus_kyotsu"]])
for y, v in zip(s["year"], s["pub_minus_kyotsu"]):
    ax.text(y, v + (0.04 if v >= 0 else -0.12), f"{v:+.2f}", ha="center", fontsize=8.5)
ax.axhline(0, color="k", lw=0.6); ax.set_ylabel("本系列−共通事業所\n（ポイント）"); ax.set_ylim(-0.65, 1.35)
ax.set_title("年平均の差（2026年は1〜8月）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f66_maikin_kyotsu.png"); plt.close(fig)

# 6. 頑健性：段差の推定方法を変える（15歳以上人口）
s = steps.query("var=='pop15' and kind=='切替え'")
fig, ax = plt.subplots(figsize=(10, 4.2))
x = np.arange(len(s))
for j, (k, lab, col) in enumerate([("official", "公表のギャップ", C1), ("step", "前後2年の同じ月と比べる", C2), ("step_lag12", "前後1年", C4), ("step_lag123", "前後3年", C3), ("step_uc", "状態空間モデル＋段差ダミー", GR)]):
    ax.bar(x + (j - 2) * 0.16, s[k], width=0.16, color=col, label=lab)
ax.set_xticks(x); ax.set_xticklabels([m[:4] + "年1月" for m in s["month"]], fontsize=8.5)
ax.axhline(0, color="k", lw=0.6); ax.set_ylabel("万人")
ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
ax.set_title("15歳以上人口の切替え月の段差：推定方法を変えた比較（2012年以降は長期系列で接続済み）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f66_robust.png"); plt.close(fig)
print("ok")
