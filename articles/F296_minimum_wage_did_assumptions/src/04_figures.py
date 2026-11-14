"""図3枚。"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import FIG, RES

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
A = json.loads((RES / "a_main.json").read_text(encoding="utf-8"))["design_a"]
Bm = json.loads((RES / "b_main.json").read_text(encoding="utf-8"))

# 図1：設計Aのイベントスタディと、検定が半分しか見つけない直線のずれ
es = pd.read_csv(RES / "a_event_study.csv").query("y == 'emp_rate'")
s50 = A["pretest_power"]["slope_50"]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.axhline(0, color="gray", lw=0.8)
ax.axvline(2015.5, color="gray", lw=0.8, ls=":")
ax.errorbar(es.year, es.beta, yerr=[es.beta - es.lo95, es.hi95 - es.beta], fmt="o", color="#1f5f8b", capsize=3,
            label="係数と95%区間（基準2015年）")
yrs = np.arange(2008, 2020)
ax.plot(yrs, s50 * (yrs - 2015), color="#c0504d", ls="--",
        label=f"1年 {s50:.3f}%pt で開いていくずれ（事前の検定が見つけるのは50%）")
ax.set_xlabel("年")
ax.set_ylabel("就業率の差（%pt、bite の高い県 − 低い県）")
ax.set_title(f"設計A：事前の検定は通る（p={A['pretrend_p_emp']:.2f}）が、推定値と同じくらいのずれは半分しか見つからない", fontsize=10)
ax.legend(fontsize=8.5, loc="lower right")
fig.tight_layout()
fig.savefig(FIG / "fig1_event_study_pretest_power.png", dpi=150)
plt.close(fig)

# 図2：平行トレンドが崩れたときの感度
rm = pd.read_csv(RES / "a_sensitivity_rm.csv")
lin = A["linear_extrapolation"]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.fill_between(rm.Mbar, rm.lo, rm.hi, color="#1f5f8b", alpha=0.25, label="処置後4年の平均の区間（相対的な大きさ M̄）")
ax.axhline(0, color="gray", lw=0.8)
ax.axhline(-0.5, color="#c0504d", lw=1, ls="--", label="−0.5%pt（「0.5%pt以上下がった」の線）")
ax.errorbar([-0.12], [lin["theta"]], yerr=[[lin["theta"] - lin["lo95"]], [lin["hi95"] - lin["theta"]]], fmt="s", color="#7f6000",
            capsize=3, label="処置前の傾きを延ばした場合")
bd = A["rm"]["breakdown_lo_below_-0.5"]
ax.axvline(bd, color="#c0504d", lw=0.8, ls=":")
ax.text(bd + 0.03, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] > 0 else 1, f"M̄={bd:.2f} で −0.5 を否定できなくなる", fontsize=8.5, color="#c0504d")
ax.set_xlabel("M̄（処置後の1年あたりのずれ ÷ 処置前の1年あたりの最大の動き）")
ax.set_ylabel("就業率の差（%pt）")
ax.set_title("設計A：平行トレンドがどれだけ崩れると結論が変わるか（簡略版）", fontsize=10)
ax.legend(fontsize=8.5, loc="lower left")
fig.tight_layout()
fig.savefig(FIG / "fig2_sensitivity.png", dpi=150)
plt.close(fig)

# 図3：設計B（ずれて始まる）：相対年ごとの差と、推定の方法の比較
ev = pd.read_csv(RES / "b_cs_event.csv").query("y == 'emp_rate' and 比較 == 'never'")
cs = pd.read_csv(RES / "b_callaway_santanna.csv").query("y == 'emp_rate'")
sa = pd.read_csv(RES / "b_sun_abraham.csv").query("y == 'emp_rate'").iloc[0]
tw = Bm["twfe"]["emp_rate"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axes[0]
ax.axhline(0, color="gray", lw=0.8)
ax.axvline(-0.5, color="gray", lw=0.8, ls=":")
ax.errorbar(ev.e, ev.att, yerr=1.96 * ev.se, fmt="o", color="#1f5f8b", capsize=3)
ax.set_xlabel("処置が始まった年からの年数（−1 以前は1年前との差）")
ax.set_ylabel("就業率の差（%pt）")
ax.set_title("Callaway–Sant'Anna 型（比較＝期間内に始まらない38県）", fontsize=9.5)
ax = axes[1]
rows = [("TWFE", tw["b"], tw["b"] - 1.96 * tw["se"], tw["b"] + 1.96 * tw["se"])]
for _, rr in cs.iterrows():
    rows.append((f"CS（{'期間内なし' if rr['比較'] == 'never' else 'まだ処置なし'}）", rr.ATT, rr.lo95, rr.hi95))
rows.append(("Sun–Abraham", sa.ATT, sa.lo95, sa.hi95))
for i, (lab, b, lo, hi) in enumerate(rows):
    ax.errorbar([b], [i], xerr=[[b - lo], [hi - b]], fmt="o", color="#1f5f8b" if i else "#7f6000", capsize=3)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([x[0] for x in rows], fontsize=9)
ax.axvline(0, color="gray", lw=0.8)
ax.invert_yaxis()
ax.set_xlabel("就業率の差（%pt）")
ax.set_title(f"推定の方法の比較（処置された県 {Bm['treated_units']}）", fontsize=9.5)
fig.suptitle("設計B：上げ幅の大きかった県。処置の前の年にすでに下がっている", fontsize=10.5)
fig.tight_layout()
fig.savefig(FIG / "fig3_staggered_estimators.png", dpi=150)
plt.close(fig)
print("ok")
