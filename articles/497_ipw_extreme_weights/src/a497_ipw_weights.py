"""A497 重みで偏りを直す方法は、重みが極端なときどれだけ振れるのか（架空の観察データ、seed 497）"""
import json
import numpy as np
import pandas as pd
from common import plt, save, DATA, RES, BLUE, ORANGE, GRAY, GREEN, INK

SRC = "架空の観察データ（作成者が乱数で作成、seed 497）"
rng = np.random.default_rng(497)
REPS, N, TAU = 2000, 1000, 1.0


def make(n, a):
    """x：売上に効く条件。案内を受ける確率 p は x が大きいほど高い（a が大きいほど偏る）"""
    x = rng.standard_normal(n)
    p = 1 / (1 + np.exp(-(a * x - 0.5)))
    t = rng.random(n) < p
    y = 2.0 + 1.5 * x + TAU * t + rng.standard_normal(n)
    return x, p, t, y


def fit_ps(x, t):
    """ロジスティック回帰で案内を受ける確率を推定（ニュートン法）"""
    X = np.column_stack([np.ones_like(x), x]); b = np.zeros(2)
    for _ in range(25):
        q = 1 / (1 + np.exp(-X @ b)); W = q * (1 - q)
        b = b + np.linalg.solve(X.T @ (X * W[:, None]) + 1e-9 * np.eye(2), X.T @ (t - q))
    return 1 / (1 + np.exp(-X @ b))


def estimators(x, t, y, e):
    w1, w0 = 1 / e, 1 / (1 - e)
    out = {"そのまま比べる": y[t].mean() - y[~t].mean()}
    out["重み（そのまま）"] = (t * y * w1).mean() - ((~t) * y * w0).mean()
    out["重み（合計1に直す）"] = np.sum(t * y * w1) / np.sum(t * w1) - np.sum((~t) * y * w0) / np.sum((~t) * w0)
    # 重みを切る：確率を [0.05, 0.95] に収めてから、合計1に直す
    ec = np.clip(e, 0.05, 0.95); v1, v0 = 1 / ec, 1 / (1 - ec)
    out["確率を0.05〜0.95で切る"] = np.sum(t * y * v1) / np.sum(t * v1) - np.sum((~t) * y * v0) / np.sum((~t) * v0)
    # 重みの上位1%を、99%点の値に置き換える
    ww = np.where(t, w1, w0); cap = np.quantile(ww, 0.99); ww = np.minimum(ww, cap)
    out["重みの上位1%を丸める"] = np.sum(t * y * ww) / np.sum(t * ww) - np.sum((~t) * y * ww) / np.sum((~t) * ww)
    # 確率が0.1〜0.9の人だけで比べる（比べる相手が変わる）
    keep = (e > 0.1) & (e < 0.9)
    k1, k0 = 1 / e[keep], 1 / (1 - e[keep]); tk, yk = t[keep], y[keep]
    out["0.1〜0.9の人だけ"] = np.sum(tk * yk * k1) / np.sum(tk * k1) - np.sum((~tk) * yk * k0) / np.sum((~tk) * k0)
    return out


rows, wstat = [], []
for a in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
    est = {k: [] for k in ("そのまま比べる", "重み（そのまま）", "重み（合計1に直す）", "確率を0.05〜0.95で切る", "重みの上位1%を丸める", "0.1〜0.9の人だけ")}
    mx, ess, top, ext = [], [], [], []
    for r in range(REPS):
        x, p, t, y = make(N, a)
        e = fit_ps(x, t)
        for k, v in estimators(x, t, y, e).items():
            est[k].append(v)
        ww = np.where(t, 1 / e, 1 / (1 - e))
        mx.append(ww.max()); ess.append(ww.sum() ** 2 / (ww ** 2).sum() / N)
        top.append(np.sort(ww)[-10:].sum() / ww.sum()); ext.append((ww > 20).mean())
    for k, v in est.items():
        v = np.array(v)
        rows.append(dict(a=a, method=k, bias=v.mean() - TAU, sd=v.std(), rmse=np.sqrt(np.mean((v - TAU) ** 2)),
                         p05=np.quantile(v, 0.05), p95=np.quantile(v, 0.95)))
    wstat.append(dict(a=a, max_weight_median=np.median(mx), max_weight_p95=np.quantile(mx, 0.95),
                      ess_share_median=np.median(ess), top10_share_median=np.median(top), share_weight_over20_mean=np.mean(ext)))
    if a == 2.5:
        keep_est = {k: np.array(v) for k, v in est.items()}
df = pd.DataFrame(rows); ws = pd.DataFrame(wstat)
df.to_csv(RES / "estimates_by_overlap.csv", index=False, float_format="%.4f")
ws.to_csv(RES / "weights_by_overlap.csv", index=False, float_format="%.4f")
pd.DataFrame(keep_est).to_csv(RES / "estimates_a25_2000runs.csv", index=False, float_format="%.4f")

x, p, t, y = make(N, 2.5)
pd.DataFrame({"x": x, "p_true": p, "t": t.astype(int), "y": y}).to_csv(DATA / "example_a25.csv", index=False, float_format="%.4f")

# --- 図1：偏りの強さ a ごとの RMSE
fig, ax = plt.subplots(figsize=(10, 4.4))
cols = {"そのまま比べる": GRAY, "重み（そのまま）": ORANGE, "重み（合計1に直す）": BLUE,
        "確率を0.05〜0.95で切る": GREEN, "重みの上位1%を丸める": INK, "0.1〜0.9の人だけ": "#9b59b6"}
for k, c in cols.items():
    s = df[df.method == k]; ax.plot(s.a, s.rmse, "o-", color=c, label=k)
ax.set_yscale("log"); ax.set_xlabel("偏りの強さ a（大きいほど、案内を受ける人が条件のよい人に偏る）")
ax.set_ylabel("効果の推定の誤差（RMSE、本当は1.0）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.01, 1))
ax.set_title("偏りが強いほど、そのままの重みは大きく振れる")
save(fig, "a497_rmse_by_overlap.png", "出典：" + SRC)

# --- 図2：a=2.5 の2,000回の推定の散らばり
fig, ax = plt.subplots(figsize=(8, 4.4))
names = list(cols)
ax.boxplot([keep_est[k] for k in names], orientation="horizontal", tick_labels=names, showfliers=False, whis=(5, 95))
ax.axvline(TAU, color=ORANGE, ls="--"); ax.set_xlabel("効果の推定（本当は1.0、箱は25〜75%、ひげは5〜95%）")
ax.set_title("偏りの強さ a=2.5 のとき、2,000回の推定")
save(fig, "a497_box_a25.png", "出典：" + SRC)

# --- 図3：重みの極端さ
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(ws.a, ws.max_weight_median, "o-", color=ORANGE, label="中央値"); ax[0].plot(ws.a, ws.max_weight_p95, "s--", color=ORANGE, alpha=0.6, label="95%点")
ax[0].set_yscale("log"); ax[0].set_title("いちばん大きい重み（1,000人中）"); ax[0].set_xlabel("偏りの強さ a"); ax[0].legend(frameon=False)
ax[1].plot(ws.a, ws.top10_share_median * 100, "o-", color=BLUE, label="上位10人の重みの割合")
ax[1].plot(ws.a, ws.ess_share_median * 100, "s-", color=GREEN, label="実質の人数（%）")
ax[1].set_title("重みの偏り（中央値、%）"); ax[1].set_xlabel("偏りの強さ a"); ax[1].legend(frameon=False)
save(fig, "a497_weight_extremes.png", "出典：" + SRC)

g = lambda a, m: df[(df.a == a) & (df.method == m)].iloc[0].to_dict()
main = {"weights": ws.to_dict("records"), "a1": {m: g(1.0, m) for m in cols}, "a25": {m: g(2.5, m) for m in cols},
        "a3": {m: g(3.0, m) for m in cols}}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(df.round(3).to_string()); print(ws.round(3).to_string())
