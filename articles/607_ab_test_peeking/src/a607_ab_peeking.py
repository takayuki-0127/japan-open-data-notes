"""607 A/B テストを毎日のぞいて「差あり」が出た日に止めると、効果が0でも何%で差ありになるのか

架空の A/B テスト：1日に各群500人、購入率5%、28日間（各群14,000人）。毎日の累計で2つの割合の差を z 検定する。
  F 28日目に1回だけ検定（決めた日数を守る）
  P 毎日のぞいて p<0.05 が出た日に止める（7日ごと・3日ごとにのぞく場合も）
  B O'Brien–Fleming 型の境界：k 日目は |z| > c×√(28/k)。c は効果0のときに全体で5%になるようシミュレーションで決める
効果0での偽陽性率、効果ありでの検出力、止めた日に読んだ効果の大きさを数える。各条件2万回、seed 607。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 607）"
rng = np.random.default_rng(607)
R, DAYS, NPD, P0 = 20000, 28, 500, 0.05


def sim(lift):
    a = rng.binomial(NPD, P0, (R, DAYS)).cumsum(axis=1)
    b = rng.binomial(NPD, P0 * (1 + lift), (R, DAYS)).cumsum(axis=1)
    n = NPD * np.arange(1, DAYS + 1)
    pa, pb = a / n, b / n
    pp = (a + b) / (2 * n)
    se = np.sqrt(pp * (1 - pp) * 2 / n)
    z = (pb - pa) / se
    eff = pb / pa - 1
    return z, eff


z0, e0 = sim(0.0)
k = np.arange(1, DAYS + 1)
# O'Brien–Fleming 型の境界の定数を、効果0の別のシミュレーションで決める
zc, _ = sim(0.0)
lo, hi = 1.5, 3.5
for _ in range(40):
    c = (lo + hi) / 2
    fp = (np.abs(zc) > c * np.sqrt(DAYS / k)).any(axis=1).mean()
    lo, hi = (lo, c) if fp < 0.05 else (c, hi)
C_OBF = round((lo + hi) / 2, 4)
bound_obf = C_OBF * np.sqrt(DAYS / k)
Z = 1.959964


def evaluate(z, eff, rule):
    if rule == "F":
        stop = np.abs(z[:, -1]) > Z; day = np.where(stop, DAYS, -1); est = eff[:, -1]
        return stop, day, np.where(stop, est, np.nan)
    if rule.startswith("P"):
        step = int(rule[1:]); looks = np.arange(step - 1, DAYS, step)
        hit = np.abs(z[:, looks]) > Z
    else:
        looks = np.arange(DAYS); hit = np.abs(z) > bound_obf
    any_ = hit.any(axis=1); first = np.argmax(hit, axis=1)
    d_idx = looks[first]
    day = np.where(any_, d_idx + 1, -1)
    est = np.where(any_, eff[np.arange(len(z)), d_idx], np.nan)
    return any_, day, est


rules = {"F": "28日目に1回だけ", "P7": "7日ごとにのぞく", "P3": "3日ごとにのぞく", "P1": "毎日のぞく", "B": "毎日のぞく＋O'Brien–Fleming 型の境界"}
rows = []
for lift in [0.0, 0.05, 0.10, 0.15]:
    z, eff = (z0, e0) if lift == 0 else sim(lift)
    for r in rules:
        s, d, est = evaluate(z, eff, r)
        pos = s & (np.nan_to_num(est) > 0) if lift > 0 else s
        rows.append({"lift": lift, "rule": r, "reject_pct": round(100 * s.mean(), 2),
                     "reject_right_dir_pct": round(100 * pos.mean(), 2),
                     "median_stop_day": float(np.median(d[s])) if s.any() else np.nan,
                     "mean_est_lift_pct_when_stopped": round(100 * float(np.nanmean(np.where(est > 0, est, np.nan))), 2) if s.any() else np.nan})
df = pd.DataFrame(rows); df.to_csv(RES / "summary.csv", index=False)
# 効果0、毎日のぞいたときの「差あり」の累積（何日目までに何%）
s, d, _ = evaluate(z0, e0, "P1")
cum = np.array([(np.where(s, d, 99) <= kk).mean() for kk in k]) * 100
pd.DataFrame({"day": k, "cum_false_pos_pct": cum.round(2), "obf_bound": bound_obf.round(3)}).to_csv(RES / "by_day.csv", index=False)
sF, dF, _ = evaluate(z0, e0, "F")
out = {"reps": R, "days": DAYS, "per_arm_per_day": NPD, "base_rate": P0, "obf_constant": C_OBF,
       "obf_bound_day1": round(float(bound_obf[0]), 2), "obf_bound_day28": round(float(bound_obf[-1]), 2),
       "null_false_pos_pct": {r: float(df[(df.lift == 0) & (df.rule == r)].reject_pct.iloc[0]) for r in rules},
       "power_pct": {str(l): {r: float(df[(df.lift == l) & (df.rule == r)].reject_right_dir_pct.iloc[0]) for r in rules} for l in [0.05, 0.10, 0.15]},
       "est_lift_when_stopped_pct_lift10": {r: float(df[(df.lift == 0.10) & (df.rule == r)].mean_est_lift_pct_when_stopped.iloc[0]) for r in rules},
       "median_stop_day_lift10": {r: float(df[(df.lift == 0.10) & (df.rule == r)].median_stop_day.iloc[0]) for r in rules},
       "null_daily_cum_pct_day7": round(float(cum[6]), 2), "null_daily_cum_pct_day14": round(float(cum[13]), 2)}
json.dump(out, open(RES / "a607_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：効果0での偽陽性率
fig, ax = plt.subplots(figsize=(8.5, 3.6))
rs = ["F", "P7", "P3", "P1", "B"]
v = [out["null_false_pos_pct"][r] for r in rs]
ax.barh([rules[r] for r in rs][::-1], v[::-1], color=[GREEN, LIGHT, BLUE, ORANGE, GREEN][::-1])
for i, x in enumerate(v[::-1]):
    ax.text(x, i, f" {x:.1f}%", va="center", fontsize=10)
ax.axvline(5, color=GRAY, ls=":"); ax.set_xlim(0, max(v) * 1.25)
ax.set_xlabel("効果が0なのに「差あり」で止めた割合（%）"); ax.set_title("28日間の A/B テスト：のぞく回数と偽の「差あり」")
save(fig, "a607_false_positive.png", SRC, y=-0.08)
# 図2：毎日のぞいた場合の、効果0の z の道筋の例と境界
fig, ax = plt.subplots(figsize=(8.5, 3.8))
for i in range(30):
    ax.plot(k, z0[i], color=LIGHT, lw=0.8)
ax.plot(k, np.full(DAYS, Z), color=ORANGE, lw=1.5, label="毎日 p<0.05（|z|>1.96）"); ax.plot(k, -np.full(DAYS, Z), color=ORANGE, lw=1.5)
ax.plot(k, bound_obf, color=GREEN, lw=1.5, ls="--", label="O'Brien–Fleming 型の境界"); ax.plot(k, -bound_obf, color=GREEN, lw=1.5, ls="--")
ax.set_ylim(-5, 5); ax.set_xlabel("テストの日数"); ax.set_ylabel("累計で見た z")
ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_title("効果0のテスト30本の z の動き：毎日見ると、どこかで線を越える")
save(fig, "a607_z_paths.png", SRC)
# 図3：効果10%のときの検出力と、止めた日に読んだ効果
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.55})
rs2 = ["F", "P1", "B"]
pw = [out["power_pct"]["0.1"][r] for r in rs2]; es = [out["est_lift_when_stopped_pct_lift10"][r] for r in rs2]
lab2 = ["28日目に1回", "毎日のぞく", "毎日＋境界"]
axs[0].bar(lab2, pw, color=[GREEN, ORANGE, BLUE]); axs[0].set_ylabel("%"); axs[0].set_title("本当の効果 +10% を見つけた割合")
for i, x in enumerate(pw):
    axs[0].text(i, x, f"{x:.1f}%", ha="center", va="bottom")
axs[1].bar(lab2, es, color=[GREEN, ORANGE, BLUE]); axs[1].axhline(10, color=GRAY, ls=":")
axs[1].set_ylabel("%"); axs[1].set_title("「差あり」で止めた日に読んだ効果（本当は +10%）")
for i, x in enumerate(es):
    axs[1].text(i, x, f"+{x:.1f}%", ha="center", va="bottom")
save(fig, "a607_power_and_estimate.png", SRC, y=-0.04)
print(json.dumps(out, ensure_ascii=False, indent=1))
