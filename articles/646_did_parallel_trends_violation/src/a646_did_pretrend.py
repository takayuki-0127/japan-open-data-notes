"""646 差の差で、前の期間の傾きが少し違うと、効果の推定はどれだけずれ、事前の確認で何%見抜けるのか

架空のパネル（施策あり40店・なし40店、施策前8期・後4期）。結果＝店の固有の水準＋期の共通の動き＋ノイズ（標準偏差1）。
施策ありの店だけ、1期あたり δ だけ余分に伸びる（δ=0・0.02・0.05・0.1・0.15）。本当の効果は施策後に+0.5。
  D1 ふつうの差の差（施策前後の平均の差の差）
  D2 傾きを入れた差の差（施策前の差の傾きを延ばして引く）
  事前の確認：店ごとの施策前8期の傾きを、2つの群で t 検定（p<0.05 なら「傾きが違う」）
各1,000回。事前の確認を通った回だけで見た偏りも数える。数字は置いた δ・件数・期間で決まる。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のパネルデータ（作成者が乱数で作成、seed 646）"
rng = np.random.default_rng(646)
NT, NC, PRE, POST, EFF, REPS = 40, 40, 8, 4, 0.5, 1000
t = np.arange(PRE + POST); tpre = t[:PRE]; post = t >= PRE
DELTAS = [0.0, 0.02, 0.05, 0.1, 0.15]


def draw(delta):
    common = rng.normal(0, 0.5, PRE + POST)
    yT = rng.normal(0, 1, (NT, 1)) + common + delta * t + EFF * post + rng.normal(0, 1, (NT, PRE + POST))
    yC = rng.normal(0, 1, (NC, 1)) + common + rng.normal(0, 1, (NC, PRE + POST))
    return yT, yC


def estimate(yT, yC):
    d = yT.mean(0) - yC.mean(0)                           # 期ごとの群の差
    d1 = d[post].mean() - d[~post].mean()
    b, a = np.polyfit(tpre, d[:PRE], 1)                   # 施策前の差の傾き
    d2 = (d[post] - (a + b * t[post])).mean()
    sT = np.polyfit(tpre, yT[:, :PRE].T, 1)[0]; sC = np.polyfit(tpre, yC[:, :PRE].T, 1)[0]
    p = stats.ttest_ind(sT, sC).pvalue
    return d1, d2, p


rows = []
for delta in DELTAS:
    for r in range(REPS):
        d1, d2, p = estimate(*draw(delta))
        rows.append({"delta": delta, "rep": r, "did": d1, "did_trend": d2, "pretest_p": p})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
# 理論上の偏り：δ × (後の期の平均 − 前の期の平均)
theory = {d: d * (t[post].mean() - t[~post].mean()) for d in DELTAS}


def summ(g):
    ok = g.pretest_p >= 0.05
    return pd.Series({"bias_did": g.did.mean() - EFF, "sd_did": g.did.std(), "bias_trend": g.did_trend.mean() - EFF,
                      "sd_trend": g.did_trend.std(), "detect_pct": (~ok).mean() * 100,
                      "bias_did_if_pass": g.did[ok].mean() - EFF, "reject_eff0_did": np.nan,
                      "rmse_did": np.sqrt(((g.did - EFF) ** 2).mean()), "rmse_trend": np.sqrt(((g.did_trend - EFF) ** 2).mean())})


S = D.groupby("delta").apply(summ).drop(columns="reject_eff0_did")
S["theory_bias"] = [theory[d] for d in S.index]
S = S.round(4); S.to_csv(RES / "summary.csv")
out = {"treated": NT, "control": NC, "pre": PRE, "post": POST, "effect": EFF, "reps": REPS,
       "summary": S.reset_index().to_dict(orient="records")}
json.dump(out, open(RES / "a646_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例の1回（δ=0.05）の群ごとの平均
yT, yC = draw(0.05)
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(t + 1, yT.mean(0), marker="o", color=ORANGE, label="施策ありの40店の平均")
ax.plot(t + 1, yC.mean(0), marker="s", color=BLUE, label="施策なしの40店の平均")
ax.axvline(PRE + 0.5, color=GRAY, ls="--", lw=1); ax.text(PRE + 0.6, ax.get_ylim()[1] * 0.95, "施策の開始", fontsize=9, color=GRAY)
ax.set_xticks(t + 1); ax.set_xlabel("期"); ax.set_ylabel("結果の平均"); ax.legend(frameon=False, fontsize=9)
ax.set_title("例（傾きの差 δ=0.05/期）：目で見ても、施策前の傾きの差はほとんど分からない")
save(fig, "a646_example.png", SRC)

# 図2：偏りと見抜ける割合
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"wspace": 0.3})
x = [str(d) for d in DELTAS]
ax[0].plot(x, S.bias_did, marker="o", color=ORANGE, label="ふつうの差の差")
ax[0].plot(x, S.bias_did_if_pass, marker="^", color=INK, ls=":", label="事前の確認を通った回だけ")
ax[0].plot(x, S.bias_trend, marker="s", color=GREEN, label="傾きを入れた差の差")
ax[0].axhline(0, color=GRAY, lw=0.8); ax[0].set_xlabel("施策前の傾きの差 δ（1期あたり）"); ax[0].set_ylabel("推定の偏り（本当の効果0.5）")
ax[0].legend(frameon=False, fontsize=8.5); ax[0].set_title("偏り", fontsize=11)
ax[1].bar(x, S.detect_pct, color=BLUE)
for i, v in enumerate(S.detect_pct):
    ax[1].text(i, v, f"{v:.0f}%", ha="center", va="bottom", fontsize=9)
ax[1].set_ylim(0, 110); ax[1].set_xlabel("施策前の傾きの差 δ（1期あたり）"); ax[1].set_title("事前の確認で「傾きが違う」と出た割合", fontsize=11)
save(fig, "a646_bias_detect.png", SRC, y=-0.06)

# 図3：ばらつき（ふつう vs 傾きを入れる）
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(x, S.rmse_did, marker="o", color=ORANGE, label="ふつうの差の差")
ax.plot(x, S.rmse_trend, marker="s", color=GREEN, label="傾きを入れた差の差")
for i, (a, b) in enumerate(zip(S.rmse_did, S.rmse_trend)):
    ax.text(i, a, f" {a:.3f}", fontsize=8, color=ORANGE, va="bottom"); ax.text(i, b, f" {b:.3f}", fontsize=8, color=GREEN, va="top")
ax.set_xlabel("施策前の傾きの差 δ（1期あたり）"); ax.set_ylabel("誤差（RMSE）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("傾きを入れると偏りは消えるが、傾きの差がないときはばらつきが大きい")
save(fig, "a646_rmse.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
