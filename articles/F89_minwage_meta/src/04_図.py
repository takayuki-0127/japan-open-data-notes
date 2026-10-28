"""図：フォレストプロット、仕様の組み合わせ、推定値と標準誤差、F01/F17 の扱いと1本ずつ外す、失業率、研究の本数と検出力。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, COL, REF_BAND

FIG.mkdir(exist_ok=True)
S = json.load(open(RES / "summary.json"))
est = pd.read_csv(RES / "estimates_common_unit.csv")
spec = pd.read_csv(RES / "spec_combinations.csv")
loo = pd.read_csv(RES / "leave_one_out.csv")
dep = pd.read_csv(RES / "dependence_f01_f17.csv")
curve = pd.read_csv(RES / "power_vs_studies.csv")
LAB = {"F01": "F01 県パネル（固定効果）", "F15": "F15 県境の隣接市町村", "F17": "F17 DML（機械学習で調整）"}


def band(ax, vertical=True):
    if vertical:
        ax.axvspan(*REF_BAND, color="#f2c14e", alpha=0.25, lw=0, label="海外でよく報告される範囲（0〜−0.3）")
        ax.axvline(0, color="gray", lw=0.8)


def forest(ax, inp, m, xlim, unit):
    rows = []
    for r in inp:
        rows.append((LAB[r["study"]], r["est"], r["est"] - 1.96 * r["se"], r["est"] + 1.96 * r["se"], COL[r["study"]], r["study"]))
    n = len(rows)
    w = m["weights_fe"]
    for i, (lab, e, lo, hi, c, s) in enumerate(rows):
        y = n - i + 1
        ax.plot([max(lo, xlim[0]), min(hi, xlim[1])], [y, y], color=c, lw=2)
        ax.plot(e, y, "s", color=c, ms=5 + 14 * np.sqrt(w[i]))
        if lo < xlim[0]: ax.annotate("", xy=(xlim[0], y), xytext=(xlim[0] + 0.05 * (xlim[1] - xlim[0]), y), arrowprops=dict(arrowstyle="->", color=c))
        if hi > xlim[1]: ax.annotate("", xy=(xlim[1], y), xytext=(xlim[1] - 0.05 * (xlim[1] - xlim[0]), y), arrowprops=dict(arrowstyle="->", color=c))
        ax.text(xlim[1], y, f"  {e:+.2f} [{lo:+.2f}, {hi:+.2f}]  重み{w[i]*100:.0f}%", va="center", fontsize=8.5)
    for y, key, lab in [(1, "fe", "固定効果"), (0, "re_dl", "ランダム効果（HKSJ）")]:
        mu = m[key]
        lo, hi = (m["fe_lo"], m["fe_hi"]) if key == "fe" else (m["re_dl_hk_lo"], m["re_dl_hk_hi"])
        ax.fill([max(lo, xlim[0]), mu, min(hi, xlim[1]), mu], [y, y + 0.25, y, y - 0.25], color=COL["pool"])
        ax.text(xlim[1], y, f"  {mu:+.2f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8.5)
    ax.set_yticks([n - i + 1 for i in range(n)] + [1, 0])
    ax.set_yticklabels([r[0] for r in rows] + ["統合：固定効果", "統合：ランダム効果（HKSJ）"])
    ax.set_xlim(*xlim); ax.set_ylim(-0.8, n + 1.8)
    ax.set_xlabel(unit)


# 図1 フォレストプロット（雇用）
fig, ax = plt.subplots(figsize=(10, 4.2))
band(ax)
forest(ax, S["emp_main_inputs"], S["emp_main"], (-1.2, 1.2), "雇用の弾力性（最低賃金1%上昇あたりの就業の変化率、%）")
ax.legend(loc="upper left", fontsize=8, frameon=False)
ax.set_title(f"3本の記事の主な推定をまとめると：固定効果 {S['emp_main']['fe']:+.2f}（95%区間 {S['emp_main']['fe_lo']:+.2f}〜{S['emp_main']['fe_hi']:+.2f}）、I²={S['emp_main']['I2']*100:.0f}%", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig1_forest_emp.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図2 仕様の組み合わせ（180通り）
fig, ax = plt.subplots(figsize=(10, 4.2))
x = np.arange(len(spec))
ax.axhspan(*REF_BAND, color="#f2c14e", alpha=0.25, lw=0, label="海外でよく報告される範囲")
ax.fill_between(x, spec.fe_lo, spec.fe_hi, color="#9ecae1", alpha=0.6, lw=0, label="固定効果の95%区間")
ax.plot(x, spec.fe, color="#08519c", lw=1.5, label="統合した推定値（固定効果）")
ax.axhline(0, color="gray", lw=0.8)
sc = S["spec_curve"]
ax.set_xlabel("推定値の選び方の組み合わせ（F01 6通り × F15 6通り × F17 5通り = 180通り、統合値の小さい順）")
ax.set_ylabel("雇用の弾力性")
ax.set_title(f"どの推定値を選ぶかで、統合値は {sc['fe_min']:+.2f}〜{sc['fe_max']:+.2f}。区間が0をまたがないのは{sc['share_fe_ci_below0']*100:.0f}%の組み合わせ（すべてマイナス側）", fontsize=10.5)
ax.legend(fontsize=8, frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig2_spec_curve.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図3 推定値と標準誤差（漏斗図の形）
fig, ax = plt.subplots(figsize=(8.5, 5))
e = est[est.outcome == "emp"]
sev = np.linspace(0.001, 2.3, 100)
fe = S["emp_main"]["fe"]
ax.fill_betweenx(sev, fe - 1.96 * sev, fe + 1.96 * sev, color="#eeeeee", label="統合値±1.96×標準誤差（漏斗）")
ax.axvspan(*REF_BAND, color="#f2c14e", alpha=0.25, lw=0)
for s in ["F01", "F15", "F17"]:
    d = e[e.study == s]
    ax.scatter(d.est, d.se, color=COL[s], s=np.where(d.main, 90, 30), edgecolor="k", lw=np.where(d.main, 1, 0), label=LAB[s] + "（大きい点＝主な推定）", zorder=3)
ax.axhline(0.3 / 2.8, color="k", ls="--", lw=0.8)
ax.text(4.9, 0.3 / 2.8 + 0.03, "弾力性0.3を80%の確率で見つけられる精度", va="top", fontsize=8, ha="right")
ax.axvline(fe, color=COL["pool"], lw=1)
ax.invert_yaxis(); ax.set_xlim(-1.5, 5); ax.set_ylim(2.3, 0)
ax.set_xlabel("雇用の弾力性"); ax.set_ylabel("標準誤差（上ほど精度が高い）")
eg = S["egger_all_specs"]
ax.set_title(f"精度の低い推定ほどプラス側に散らばる（Egger の切片 {eg['intercept']:+.2f}、ただし仕様違いで独立でない参考値）", fontsize=10)
ax.legend(fontsize=7.5, frameon=False, loc="center right")
fig.tight_layout(); fig.savefig(FIG / "fig3_funnel.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図4 1本ずつ外す・F01とF17の重なりの扱い
fig, ax = plt.subplots(figsize=(10, 4))
rows = [("すべて（3本）", S["emp_main"]["fe"], S["emp_main"]["fe_lo"], S["emp_main"]["fe_hi"])]
rows += [(f"{r.dropped} を外す", r.fe, r.lo, r.hi) for r in loo.itertuples()]
rows += [(f"F01とF17を1本に（相関ρ={r.rho:.1f}）", r.fe, r.lo, r.hi) for r in dep.itertuples() if r.rho > 0]
ax.axvspan(*REF_BAND, color="#f2c14e", alpha=0.25, lw=0); ax.axvline(0, color="gray", lw=0.8)
for i, (lab, m, lo, hi) in enumerate(rows):
    y = len(rows) - i
    ax.plot([lo, hi], [y, y], color="#555", lw=2); ax.plot(m, y, "o", color="#222")
    ax.text(0.62, y, f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8.5)
ax.set_yticks([len(rows) - i for i in range(len(rows))]); ax.set_yticklabels([r[0] for r in rows])
ax.set_xlim(-0.6, 0.95); ax.set_xlabel("統合した雇用の弾力性（固定効果）")
ax.set_title("記事の入れ方・重なりの扱いを変えても、統合値は −0.10〜0.00、区間は0をまたぐ", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig4_loo_dependence.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図5 失業率
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.axvline(0, color="gray", lw=0.8)
forest(ax, S["unemp_inputs"], S["unemp_main"], (-1.5, 2.0), "失業率の変化（最低賃金10%上昇あたり、%ポイント）")
ax.set_title(f"失業率：統合 {S['unemp_main']['fe']:+.2f}%pt（95%区間 {S['unemp_main']['fe_lo']:+.2f}〜{S['unemp_main']['fe_hi']:+.2f}）。2本だけでランダム効果の区間は非常に広い", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig5_forest_unemp.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図6 研究の本数と検出力
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for th, c in [(0.1, "#d62728"), (0.3, "#1f77b4")]:
    d = curve[curve.target == th]
    ax.plot(d.extra_studies, d.power, color=c, lw=2, label=f"本当の弾力性が −{th}")
ax.axhline(0.8, color="k", ls="--", lw=0.8); ax.text(40, 0.81, "検出力80%", ha="right", fontsize=8)
ax.set_xlabel("F01 と同じ精度の独立な研究を、あと何本足すか"); ax.set_ylabel("統合したときに見つけられる確率")
ax.set_ylim(0, 1.02); ax.legend(frameon=False, loc="lower right")
p1 = S["power_fe"]["-0.1"]; p3 = S["power_fe"]["-0.3"]
ax.set_title(f"今の3本で見つけられる確率：−0.3 なら{p3*100:.0f}%、−0.1 なら{p1*100:.0f}%（−0.1 を80%にするには F01 並みの研究があと約10本）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig6_power_studies.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print(sorted(p.name for p in FIG.glob("*.png")))
