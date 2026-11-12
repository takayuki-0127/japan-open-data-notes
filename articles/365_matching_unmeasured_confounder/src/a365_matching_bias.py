"""A365 似た相手を選んで比べる方法は、測っていない違いがあるとどこまで外れるのか
架空の顧客（クーポンを受け取りやすい人ほど、元からよく買う）で、本当の効果（+500円）が分かっている状態を作り、
単純な比べ・回帰・傾向スコアのマッチング・重み付けを比べる。乱数の種は365。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N, REPS, TAU = 365, 4000, 200, 500.0
METHODS = ["単純な比べ", "回帰で調整", "傾向スコアのマッチング", "傾向スコアの重み付け"]
COLS = [GRAY, LIGHT, BLUE, GREEN]
SRC = "架空のデータ（作成者が乱数で作成、seed 365）"


def make(rng, gamma, rho=0.0, n=N):
    """x1：過去の購入額、x2：年齢、x3：会員ランク（測っている）。u：買う気の強さ（測っていない）。
    gamma：u が「クーポンを受け取るか」と「購入額」の両方に効く強さ。rho：u と x1 の相関"""
    x1 = rng.normal(0, 1, n); x2 = rng.normal(0, 1, n); x3 = (rng.random(n) < 0.3).astype(float)
    u = rho * x1 + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n)
    logit = -0.6 + 0.8 * x1 + 0.3 * x2 + 0.7 * x3 + gamma * u
    d = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(float)
    y = 3000 + 800 * x1 + 200 * x2 + 600 * x3 + 800 * gamma * u + TAU * d + rng.normal(0, 1000, n)
    return np.column_stack([x1, x2, x3]), d, y, u


def smd(a, b): return (a.mean() - b.mean()) / np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)


def estimate(X, d, y, u):
    res = {}
    t, c = d == 1, d == 0
    res["単純な比べ"] = (y[t].mean() - y[c].mean(), None)
    # 回帰：y ~ d + x
    Z = np.column_stack([np.ones(len(y)), d, X]); beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    res["回帰で調整"] = (beta[1], None)
    # 傾向スコア（測っている3つだけで作る）
    ps = LogisticRegression(C=1e6, max_iter=200).fit(X, d).predict_proba(X)[:, 1]
    lp = np.log(ps / (1 - ps))
    # 1対1のマッチング（受け取った人ごとに、スコアがいちばん近い受け取っていない人。同じ人を何度使ってもよい。幅の制限あり）
    ci = np.where(c)[0]; order = np.argsort(lp[ci]); lc = lp[ci][order]
    ti = np.where(t)[0]; pos = np.searchsorted(lc, lp[ti]).clip(1, len(lc) - 1)
    left = np.abs(lp[ti] - lc[pos - 1]) <= np.abs(lp[ti] - lc[pos]); j = np.where(left, pos - 1, pos)
    dist = np.abs(lp[ti] - lc[j]); ok = dist <= 0.2 * lp.std()
    mt, mc = ti[ok], ci[order][j[ok]]
    diff = y[mt] - y[mc]; att = diff.mean()
    # 幅：同じ相手を何度も使う分を入れる（残りのばらつき sigma2 は回帰の残差から）
    sigma2 = np.sum((y - Z @ beta) ** 2) / (len(y) - Z.shape[1])
    k = np.bincount(mc, minlength=len(y)).astype(float)
    se = np.sqrt(sigma2 * (1 / len(mt) + np.sum(k ** 2) / len(mt) ** 2))
    bal = max(abs(smd(X[mt, k], X[mc, k])) for k in range(3))
    res["傾向スコアのマッチング"] = (att, dict(se=se, max_smd=bal, smd_u=smd(u[mt], u[mc]), matched=ok.mean()))
    # 重み付け（受け取った人に合わせる）
    w = ps / (1 - ps)
    res["傾向スコアの重み付け"] = (y[t].mean() - np.average(y[c], weights=w[c]), None)
    return res


def run(rng, gamma, rho=0.0, reps=REPS):
    est = {m: [] for m in METHODS}; extra = []
    for _ in range(reps):
        X, d, y, u = make(rng, gamma, rho)
        r = estimate(X, d, y, u)
        for m in METHODS: est[m].append(r[m][0])
        extra.append(r["傾向スコアのマッチング"][1])
    row = dict(gamma=gamma, rho=rho)
    for m in METHODS:
        e = np.array(est[m]); row[m + "_bias"] = float(e.mean() - TAU); row[m + "_sd"] = float(e.std(ddof=1))
    e = np.array(est["傾向スコアのマッチング"]); se = np.array([x["se"] for x in extra]); ms = np.array([x["max_smd"] for x in extra])
    cover = (np.abs(e - TAU) <= 1.96 * se)
    row["match_ci_covers_truth"] = float(cover.mean() * 100)
    row["match_balance_ok"] = float((ms < 0.1).mean() * 100)                         # 測った3つのバランスが取れた回
    row["match_balance_ok_but_ci_misses"] = float(((ms < 0.1) & ~cover).mean() * 100)
    row["match_smd_u"] = float(np.mean([x["smd_u"] for x in extra]))
    row["matched_share"] = float(np.mean([x["matched"] for x in extra]) * 100)
    return row


def main():
    rng = np.random.default_rng(SEED)
    X, d, y, u = make(rng, 0.5)
    pd.DataFrame({"past_purchase": X[:, 0].round(3), "age_std": X[:, 1].round(3), "member_rank": X[:, 2].astype(int),
                  "coupon": d.astype(int), "purchase_yen": y.round(0).astype(int)}).head(2000).to_csv(DATA / "example_customers.csv", index=False)
    rows = [run(rng, g) for g in [0.0, 0.25, 0.5, 1.0, 1.5]]
    main_df = pd.DataFrame(rows).round(2); main_df.to_csv(RES / "bias_by_strength.csv", index=False)
    # 測っていない要因が、測っている過去の購入額と相関している場合
    rows = [run(rng, 1.0, rho) for rho in [0.0, 0.3, 0.6, 0.9]]
    cor_df = pd.DataFrame(rows).round(2); cor_df.to_csv(RES / "bias_by_correlation.csv", index=False)
    # 測っている要因を1つ落とした場合（過去の購入額を使わない）。測っていない要因はなし
    drop, full = [], []
    for _ in range(REPS):
        X, d, y, u = make(rng, 0.0)
        full.append(estimate(X, d, y, u)["傾向スコアのマッチング"][0])
        Xd = np.column_stack([X[:, 1], X[:, 2], np.zeros(len(d))])                  # 過去の購入額の列を0にする
        drop.append(estimate(Xd, d, y, u)["傾向スコアのマッチング"][0])
    out = {"n": N, "reps": REPS, "true_effect": TAU,
           "by_strength": main_df.to_dict("records"), "by_correlation": cor_df.to_dict("records"),
           "drop_past_purchase_bias": round(float(np.mean(drop) - TAU), 1),
           "all_three_bias": round(float(np.mean(full) - TAU), 1)}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：測っていない要因の強さと偏り ---
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for m, c in zip(METHODS, COLS):
        ax.plot(main_df.gamma, main_df[m + "_bias"] + TAU, "-o", color=c, lw=1.8, ms=5, label=m)
    ax.axhline(TAU, color=INK, lw=1, ls="--"); ax.text(1.5, TAU - 60, "本当の効果 +500円", ha="right", fontsize=9.5)
    ax.set_xlabel("測っていない要因（買う気の強さ）の強さ"); ax.set_ylabel("見積もった効果（円、200回の平均）"); ax.legend(frameon=False, fontsize=9.5)
    ax.set_title("測っていない要因が強いほど、どの方法も同じだけ高く出る")
    save(fig, "a365_bias_by_strength.png", SRC + "。顧客4,000人、200回。測っている要因は過去の購入額・年齢・会員ランク")

    # --- 図2：バランスは取れているのに外れる ---
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    x = np.arange(len(main_df)); w = 0.38
    ax.bar(x - w / 2, main_df.match_balance_ok, w, color=BLUE, label="測った3つのバランスが取れた回の割合")
    ax.bar(x + w / 2, main_df.match_ci_covers_truth, w, color=ORANGE, label="95%の幅が本当の効果を含んだ回の割合")
    for xx, v in zip(x - w / 2, main_df.match_balance_ok): ax.text(xx, v + 1.5, f"{v:.0f}", ha="center", fontsize=9.5)
    for xx, v in zip(x + w / 2, main_df.match_ci_covers_truth): ax.text(xx, v + 1.5, f"{v:.0f}", ha="center", fontsize=9.5)
    ax.set_xticks(x); ax.set_xticklabels([f"強さ {g}" for g in main_df.gamma]); ax.set_ylim(0, 135); ax.set_ylabel("割合（%）")
    ax.legend(frameon=False, fontsize=9.5, loc="upper center", ncol=1); ax.set_title("マッチングのあと、測った要因はそろっていても、答えは外れている")
    save(fig, "a365_balance_vs_truth.png", SRC + "。傾向スコアのマッチング。バランス＝標準化した差が3つとも0.1未満")

    # --- 図3：測っている要因と相関していれば、どこまで戻るか ---
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    x = np.arange(len(cor_df)); w = 0.2
    for j, (m, c) in enumerate(zip(METHODS, COLS)):
        ax.bar(x + (j - 1.5) * w, cor_df[m + "_bias"], w, color=c, label=m)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"相関 {r}" for r in cor_df.rho])
    ax.set_xlabel("測っていない要因と、過去の購入額（測っている）の相関"); ax.set_ylabel("偏り（円。0なら正しい）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("測っている要因と相関していれば、その分だけ偏りは減る")
    save(fig, "a365_bias_by_correlation.png", SRC + "。測っていない要因の強さは1.0")
    print(main_df.T.to_string()); print(cor_df.T.to_string()); print(out["drop_past_purchase_bias"], out["all_three_bias"])


if __name__ == "__main__":
    main()
