"""694 A/B テストを3日だけで止めると、曜日で効き方が違うとき、効果の推定はどれだけずれるのか

架空の A/B テスト。1日の訪問者は各案、平日4,000人・土日7,000人。もとの申込率は平日3.0%・土日2.2%。
新しい案の効き方は曜日で違う：平日は +2%（相対）、土日は +20%（相対）。
1週間を通した本当の効果（訪問者で重み付けした申込数の増え方）を基準に、
始める曜日（月〜日）と期間（3日・7日・14日）を変えて、効果の推定（相対の増え方）を2,000回ずつ数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の A/B テスト（作成者が乱数で作成、seed 694）"
rng = np.random.default_rng(694)
DAYS = ["月", "火", "水", "木", "金", "土", "日"]
VIS = np.array([4000] * 5 + [7000] * 2)
BASE = np.array([0.030] * 5 + [0.022] * 2)
LIFT = np.array([0.02] * 5 + [0.20] * 2)
REPS = 2000
true_eff = (VIS * BASE * (1 + LIFT)).sum() / (VIS * BASE).sum() - 1

rows = []
for start in range(7):
    for dur in [3, 7, 14]:
        d = (start + np.arange(dur)) % 7
        nA = VIS[d].sum(); nB = nA
        cA = rng.binomial(VIS[d][None, :], BASE[d][None, :], (REPS, dur)).sum(1)
        cB = rng.binomial(VIS[d][None, :], (BASE[d] * (1 + LIFT[d]))[None, :], (REPS, dur)).sum(1)
        est = (cB / nB) / (cA / nA) - 1
        exp_eff = (VIS[d] * BASE[d] * (1 + LIFT[d])).sum() / (VIS[d] * BASE[d]).sum() - 1
        rows.append({"start": DAYS[start], "days": dur, "mean_est": est.mean() * 100, "sd_est": est.std() * 100,
                     "p5": np.quantile(est, 0.05) * 100, "p95": np.quantile(est, 0.95) * 100, "expected": exp_eff * 100,
                     "bias": (est.mean() - true_eff) * 100, "weekend_days": int((d >= 5).sum())})
S = pd.DataFrame(rows); S.round(3).to_csv(RES / "summary.csv", index=False)
d3 = S[S.days == 3]
out = {"true_effect_pct": round(true_eff * 100, 2), "reps": REPS,
       "three_days": {r.start: {"mean": round(r.mean_est, 2), "weekend_days": r.weekend_days} for r in d3.itertuples()},
       "three_days_min": round(float(d3.mean_est.min()), 2), "three_days_max": round(float(d3.mean_est.max()), 2),
       "seven_days_range": [round(float(S[S.days == 7].mean_est.min()), 2), round(float(S[S.days == 7].mean_est.max()), 2)],
       "fourteen_days_range": [round(float(S[S.days == 14].mean_est.min()), 2), round(float(S[S.days == 14].mean_est.max()), 2)],
       "sd_by_days": {str(k): round(float(S[S.days == k].sd_est.mean()), 2) for k in [3, 7, 14]}}
json.dump(out, open(RES / "a694_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：曜日ごとの効き方と訪問者
fig, ax = plt.subplots(figsize=(8.5, 3.6)); ax2 = ax.twinx()
ax.bar(DAYS, LIFT * 100, color=[LIGHT] * 5 + [ORANGE] * 2, label="新しい案の効き方（左）")
ax2.plot(DAYS, VIS, color=INK, marker="o", label="1日の訪問者（各案、右）"); ax2.spines["right"].set_visible(True)
ax.set_ylabel("申込率の増え方（相対、%）"); ax2.set_ylabel("訪問者（人）"); ax2.set_ylim(0, 8000)
ax.set_title(f"平日は +2%、土日は +20%。1週間を通した本当の効果は +{true_eff*100:.1f}%")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper left")
save(fig, "a694_weekday_effect.png", SRC)

# 図2：始める曜日と期間ごとの推定
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(7); w = 0.27
for k, (dur, c) in enumerate([(3, ORANGE), (7, BLUE), (14, GREEN)]):
    s = S[S.days == dur]
    ax.bar(x + (k - 1) * w, s.mean_est, w, color=c, label=f"{dur}日で止める")
    ax.errorbar(x + (k - 1) * w, s.mean_est, yerr=[s.mean_est - s.p5, s.p95 - s.mean_est], fmt="none", ecolor=INK, lw=0.8, capsize=2)
ax.axhline(true_eff * 100, color=INK, ls="--", lw=0.8); ax.text(6.4, true_eff * 100, f" 本当 {true_eff*100:.1f}%", fontsize=8.5, va="bottom")
ax.set_xticks(x); ax.set_xticklabels([f"{d}曜に開始" for d in DAYS], fontsize=9); ax.set_ylabel("効果の推定（平均、線は90%の範囲）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("3日で止めると、土日を含むかどうかで推定の平均が6倍以上違う")
save(fig, "a694_by_start.png", SRC)

# 図3：3日で止めたときの推定と、含んだ土日の日数
fig, ax = plt.subplots(figsize=(8, 3.6))
for r in d3.itertuples():
    ax.scatter(r.weekend_days, r.mean_est, color=ORANGE, s=40, zorder=3); ax.text(r.weekend_days + 0.05, r.mean_est, f"{r.start}曜開始", fontsize=8.5, va="center")
ax.axhline(true_eff * 100, color=INK, ls="--", lw=0.8)
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["土日を含まない", "1日含む", "2日含む"]); ax.set_ylabel("効果の推定（3日、平均 %）")
ax.set_title("3日のテストは、どの曜日を含んだかでほぼ決まる")
save(fig, "a694_three_days.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
