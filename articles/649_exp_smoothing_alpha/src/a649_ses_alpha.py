"""649 指数平滑の α を大きくするか小さくするかで、水準が変わったときの追いつき方と平時の誤差はどう入れ替わるのか

架空の日次系列（400日）：水準＋ノイズ（標準偏差1）。200日目に水準が+3 上がる。水準そのものが毎日少し動く（ランダムウォーク、
標準偏差 0・0.2・0.5）の3通り。単純指数平滑 ℓ_t = α·y_t + (1−α)·ℓ_{t−1} で翌日を予測し、
  平時の誤差：50〜199日目の1日先の予測の二乗誤差（RMSE）
  追いつき：200日目の跳びの50%・90%を予測が取り戻すまでの日数
を α = 0.02〜0.8 で比べる。最初の200日の1日先の誤差が最小になる α（推定した α）も出す。各500回。数字は置いたノイズと動きで決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の日次系列（作成者が乱数で作成、seed 649）"
rng = np.random.default_rng(649)
T, SHIFT_AT, SHIFT, REPS = 400, 200, 3.0, 500
ALPHAS = [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8]
GRID = np.round(np.arange(0.01, 1.0, 0.01), 2)


def draw(sig_lv):
    lv = 10 + np.cumsum(rng.normal(0, sig_lv, (REPS, T)), 1) if sig_lv > 0 else np.full((REPS, T), 10.0)
    lv = lv + SHIFT * (np.arange(T) >= SHIFT_AT)
    return lv, lv + rng.normal(0, 1, (REPS, T))


def ses(y, a):
    """各系列について、t 日目までで作った翌日（t+1）の予測を返す。f[:, t] は t 日目の予測"""
    f = np.empty_like(y); l = y[:, 0].copy(); f[:, 0] = l
    for t in range(1, y.shape[1]):
        f[:, t] = l
        l = a * y[:, t] + (1 - a) * l
    return f


rows, est = [], []
for sig in [0.0, 0.2, 0.5]:
    lv, y = draw(sig)
    for a in ALPHAS:
        f = ses(y, a)
        rmse = np.sqrt(((y[:, 50:SHIFT_AT] - f[:, 50:SHIFT_AT]) ** 2).mean())
        # 追いつき：予測 − 跳びの前の水準の見込み（199日目の予測）が跳びの何割か
        gap = (f[:, SHIFT_AT:SHIFT_AT + 150] - f[:, [SHIFT_AT]]) / SHIFT
        gm = gap.mean(0)
        d50 = int(np.argmax(gm >= 0.5)) if (gm >= 0.5).any() else None
        d90 = int(np.argmax(gm >= 0.9)) if (gm >= 0.9).any() else None
        after = np.sqrt(((y[:, SHIFT_AT:SHIFT_AT + 30] - f[:, SHIFT_AT:SHIFT_AT + 30]) ** 2).mean())
        rows.append({"sig_level": sig, "alpha": a, "rmse_calm": rmse, "days_to_50": d50, "days_to_90": d90, "rmse_30days_after": after})
    # 最初の200日で α を選ぶ
    sse = np.stack([((y[:, 1:SHIFT_AT] - ses(y[:, :SHIFT_AT], a)[:, 1:]) ** 2).sum(1) for a in GRID], 1)
    ah = GRID[np.argmin(sse, 1)]
    est.append({"sig_level": sig, "alpha_hat_median": float(np.median(ah)), "alpha_hat_q10": float(np.quantile(ah, 0.1)),
                "alpha_hat_q90": float(np.quantile(ah, 0.9)), "share_min_grid": float((ah == GRID[0]).mean() * 100)})
D = pd.DataFrame(rows).round(4); D.to_csv(RES / "summary.csv", index=False)
E = pd.DataFrame(est).round(3); E.to_csv(RES / "alpha_estimated.csv", index=False)
# 理論：平時（水準が動かない）の1日先の誤差の分散 = σ²·(1 + α/(2−α))
D["rmse_calm_theory_sig0"] = np.sqrt(1 + D.alpha / (2 - D.alpha)).round(4)
D.to_csv(RES / "summary.csv", index=False)
out = {"days": T, "shift_day": SHIFT_AT, "shift": SHIFT, "noise_sd": 1.0, "reps": REPS,
       "summary": D.to_dict(orient="records"), "alpha_estimated": E.to_dict(orient="records")}
json.dump(out, open(RES / "a649_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例の1本（水準は動かない）と α=0.05・0.3 の予測
lv, y = draw(0.0)
fig, ax = plt.subplots(figsize=(9, 4))
d = np.arange(150, 300)
ax.plot(d, y[0, d], color=GRAY, lw=0.8, label="実績（例の1本）")
for a, c in [(0.05, BLUE), (0.3, ORANGE)]:
    ax.plot(d, ses(y[:1], a)[0, d], color=c, lw=2, label=f"α={a} の予測")
ax.plot(d, lv[0, d], color=INK, ls="--", lw=1, label="本当の水準")
ax.set_xlabel("日"); ax.set_ylabel("値"); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("200日目に水準が+3：α が小さいと遅れ、大きいと平時に振れる")
save(fig, "a649_example.png", SRC)

# 図2：平時の誤差と追いつく日数（水準は動かない）
s0 = D[D.sig_level == 0].set_index("alpha")
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"wspace": 0.3})
xa = [str(a) for a in ALPHAS]
ax[0].plot(xa, s0.rmse_calm, marker="o", color=BLUE)
for i, v in enumerate(s0.rmse_calm):
    ax[0].text(i, v, f"{v:.3f}", fontsize=8, ha="center", va="bottom")
ax[0].set_xlabel("α"); ax[0].set_title("平時の1日先の誤差（RMSE、ノイズの分は1）", fontsize=11)
ax[1].bar(xa, s0.days_to_90, color=ORANGE, label="90%")
ax[1].bar(xa, s0.days_to_50, color=LIGHT, label="50%")
for i, (v5, v9) in enumerate(zip(s0.days_to_50, s0.days_to_90)):
    ax[1].text(i, v9, f"{v9:.0f}日", fontsize=8, ha="center", va="bottom")
ax[1].set_xlabel("α"); ax[1].set_title("跳びの50%・90%に追いつくまでの日数", fontsize=11); ax[1].legend(frameon=False, fontsize=9)
save(fig, "a649_tradeoff.png", SRC, y=-0.06)

# 図3：水準の動きの大きさと、平時の誤差・推定した α
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"wspace": 0.3})
for sig, c in [(0.0, BLUE), (0.2, GREEN), (0.5, ORANGE)]:
    s = D[D.sig_level == sig]
    ax[0].plot([str(a) for a in s.alpha], s.rmse_calm, marker="o", color=c, label=f"水準の動き {sig}")
ax[0].set_xlabel("α"); ax[0].set_title("平時の1日先の誤差（RMSE）", fontsize=11); ax[0].legend(frameon=False, fontsize=9)
ax[1].errorbar([str(s) for s in E.sig_level], E.alpha_hat_median, yerr=[E.alpha_hat_median - E.alpha_hat_q10, E.alpha_hat_q90 - E.alpha_hat_median],
               fmt="o", color=INK, capsize=4)
for i, v in enumerate(E.alpha_hat_median):
    ax[1].text(i + 0.08, v, f"{v:.2f}", fontsize=9, va="center")
ax[1].set_xlabel("水準が毎日動く大きさ（標準偏差）"); ax[1].set_title("最初の200日で選んだ α（中央値と10〜90%点）", fontsize=11)
save(fig, "a649_by_level_noise.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
