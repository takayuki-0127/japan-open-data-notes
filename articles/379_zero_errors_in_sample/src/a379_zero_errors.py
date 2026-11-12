"""A379 何件調べて誤りが0件なら、「誤りは1%未満」と言えるのか
架空の伝票10万件で、抜き取って誤りが0件だったときに言えることを数える。
必要な件数（3の法則と正確な計算）、本当の誤り率ごとの「0件で通る」割合、誤りが固まっているときの抜き取り方ごとの見逃しを出す。乱数の種は379。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N = 379, 100_000
SRC = "架空のデータ（作成者が乱数で作成、seed 379）"


def n_needed_binom(p0, conf=0.95):
    """n件調べて0件なら「誤り率は p0 未満」と conf の確かさで言える、いちばん小さい n（全体が十分大きいとき）"""
    return int(np.ceil(np.log(1 - conf) / np.log(1 - p0)))


def n_needed_hyper(p0, conf=0.95, N=N):
    """全体 N 件から戻さずに抜くとき。誤りがちょうど p0×N 件あっても、0件で通る確率が 1−conf 以下になる n"""
    K = int(round(p0 * N)); lo, hi = 1, N
    while lo < hi:
        mid = (lo + hi) // 2
        if stats.hypergeom.pmf(0, N, K, mid) <= 1 - conf: hi = mid
        else: lo = mid + 1
    return lo


def upper_bound(n, k, conf=0.95):
    """n件のうち k件が誤りだったときの、誤り率の上限（片側、クロッパー・ピアソン）"""
    return 1.0 - (1 - conf) ** (1 / n) if k == 0 else stats.beta.ppf(conf, k + 1, n - k)


def main():
    rng = np.random.default_rng(SEED)
    # ---- 1. 必要な件数 ----
    rows = []
    for p0 in (0.05, 0.02, 0.01, 0.005, 0.002, 0.001):
        rows.append(dict(threshold_pct=p0 * 100, rule_of_three=int(np.ceil(3 / p0)), exact_95=n_needed_binom(p0), exact_95_finite_100k=n_needed_hyper(p0),
                         exact_99=n_needed_binom(p0, 0.99), exact_90=n_needed_binom(p0, 0.90),
                         finite_10k=n_needed_hyper(p0, N=10_000), finite_1k=n_needed_hyper(p0, N=1_000) if p0 * 1000 >= 1 else None))
    need = pd.DataFrame(rows); need.to_csv(RES / "sample_size_needed.csv", index=False)

    # ---- 2. 何件か見つかったときの上限（n=300） ----
    ub = pd.DataFrame([dict(n=n, found=k, upper95_pct=upper_bound(n, k) * 100, rule=[3.0, 4.74, 6.30, 7.75][k] / n * 100) for n in (100, 300, 600, 3000) for k in (0, 1, 2, 3)])
    ub.to_csv(RES / "upper_bound_when_found.csv", index=False)

    # ---- 3. 本当の誤り率ごとに、「0件で通る」割合（全体10万件から戻さずに抜く。シミュレーションと式） ----
    rows = []
    REPS = 20000
    for n in (100, 300, 600, 3000):
        for p in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05):
            K = int(round(p * N))
            exact = stats.hypergeom.pmf(0, N, K, n)
            sim = (rng.hypergeometric(K, N - K, n, REPS) == 0).mean()
            rows.append(dict(n=n, true_rate_pct=p * 100, pass_exact_pct=exact * 100, pass_sim_pct=sim * 100))
    oc = pd.DataFrame(rows); oc.to_csv(RES / "pass_probability.csv", index=False)

    # ---- 4. 誤りが固まっているとき：抜き取り方ごとの見逃し ----
    # 伝票10万件 = 1,000束（1束100件。担当者・日ごとの束を想定）。全体の誤り率は1%（1,000件）
    B, S = 1000, 100
    def population(share_bad_batches):
        """誤りのある束の割合。その束に、合計1,000件の誤りを均等に置く"""
        nb = max(1, int(round(B * share_bad_batches))); per = 1000 // nb
        err = np.zeros((B, S), bool)
        bad = rng.choice(B, nb, replace=False)
        for b in bad: err[b, rng.choice(S, min(per, S), replace=False)] = True
        return err
    rows = []; REPS2 = 4000; n = 300
    for share in (1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01):
        miss = dict(random=0, systematic=0, recent_block=0, three_batches=0, thirty_batches_10each=0, one_per_batch=0)
        rate = []
        for _ in range(REPS2):
            err = population(share); flat = err.ravel(); rate.append(flat.mean())
            miss["random"] += not flat[rng.choice(N, n, replace=False)].any()                       # ① 全体からでたらめに300件
            start = rng.integers(0, N // n); miss["systematic"] += not flat[start::N // n][:n].any()   # ② 一定の間隔で300件
            st = rng.integers(0, N - n); miss["recent_block"] += not flat[st:st + n].any()           # ③ 続いた300件（ある時期の分だけ）
            bs = rng.choice(B, 3, replace=False); miss["three_batches"] += not err[bs].any()         # ④ 3束を選んで全部（300件）
            bs = rng.choice(B, 30, replace=False); pick = rng.integers(0, S, (30, 10))               # ⑤ 30束から10件ずつ
            miss["thirty_batches_10each"] += not np.take_along_axis(err[bs], pick, axis=1).any()
            bs = rng.choice(B, n, replace=False); miss["one_per_batch"] += not err[bs, rng.integers(0, S, n)].any()   # ⑥ 300束から1件ずつ
        r = dict(share_bad_batches_pct=share * 100, errors_per_bad_batch=1000 // max(1, int(round(B * share))), overall_rate_pct=float(np.mean(rate) * 100))
        r.update({k: v / REPS2 * 100 for k, v in miss.items()}); rows.append(r)
    clus = pd.DataFrame(rows); clus.to_csv(RES / "clustered_errors.csv", index=False)

    # 架空の伝票の例（誤りが20束に固まっている場合）を data に置く
    err = population(0.02)
    ex = pd.DataFrame({"batch": np.repeat(np.arange(1, B + 1), S), "seq": np.tile(np.arange(1, S + 1), B), "error": err.ravel().astype(int)})
    ex.groupby("batch").error.sum().reset_index().rename(columns={"error": "errors_in_batch"}).to_csv(DATA / "example_errors_by_batch.csv", index=False)

    out = {"need": need.to_dict("records"), "upper": ub.round(3).to_dict("records"),
           "pass_n300": oc[oc.n == 300].round(2).to_dict("records"), "pass_n3000": oc[oc.n == 3000].round(2).to_dict("records"),
           "clustered": clus.round(1).to_dict("records")}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    pd.set_option("display.width", 220)
    print(need.to_string()); print(ub.round(3).to_string()); print(oc.pivot(index="true_rate_pct", columns="n", values="pass_exact_pct").round(1).to_string())
    print((oc.pass_exact_pct - oc.pass_sim_pct).abs().max()); print(clus.round(1).to_string())

    # ---------- 図 ----------
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(need)); w = 0.26
    ax.bar(x - w, need.exact_90, w, color=LIGHT, label="90%の確かさ"); ax.bar(x, need.exact_95, w, color=BLUE, label="95%の確かさ"); ax.bar(x + w, need.exact_99, w, color=ORANGE, label="99%の確かさ")
    for i, r in need.iterrows():
        ax.text(i, r.exact_95 * 1.08, f"{int(r.exact_95):,}", ha="center", fontsize=8, color=BLUE); ax.text(i + w, r.exact_99 * 1.08, f"{int(r.exact_99):,}", ha="center", fontsize=8, color=ORANGE)
    ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([f"{t:g}%未満" for t in need.threshold_pct])
    ax.set_xlabel("言いたいこと：「誤り率は○%未満」"); ax.set_ylabel("誤り0件で調べる必要のある件数（対数）"); ax.legend(fontsize=9, frameon=False)
    ax.set_title("「1%未満」と言うには、0件で299件。「0.1%未満」なら2,995件")
    save(fig, "a379_sample_size.png", SRC + "（式による計算）")

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for n, c in ((100, GRAY), (300, BLUE), (600, GREEN), (3000, ORANGE)):
        g = oc[oc.n == n]; ax.plot(g.true_rate_pct, g.pass_exact_pct, color=c, lw=2, marker="o", label=f"{n:,}件調べる")
    g = oc[oc.n == 300]
    for _, r in g.iterrows():
        if r.true_rate_pct in (0.1, 0.5, 1.0): ax.text(r.true_rate_pct * 1.08, r.pass_exact_pct + 3, f"{r.pass_exact_pct:.0f}%", color=BLUE, fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(g.true_rate_pct); ax.set_xticklabels([f"{t:g}%" for t in g.true_rate_pct])
    ax.set_xlabel("本当の誤り率"); ax.set_ylabel("誤りが1件も見つからない割合（%）"); ax.legend(fontsize=9, frameon=False)
    ax.set_title("300件で0件でも、誤り率0.5%なら5回に1回は通ってしまう")
    save(fig, "a379_pass_probability.png", SRC)

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    labs = {"random": "①全体からでたらめに300件", "one_per_batch": "⑥300束から1件ずつ", "thirty_batches_10each": "⑤30束から10件ずつ", "three_batches": "④3束を全部（300件）", "recent_block": "③続いた300件"}
    cols = {"random": BLUE, "one_per_batch": GREEN, "thirty_batches_10each": LIGHT, "three_batches": ORANGE, "recent_block": GRAY}
    xs = np.arange(len(clus))
    for k in labs: ax.plot(xs, clus[k], color=cols[k], lw=2, marker="o", label=labs[k])
    ax.set_xticks(xs); ax.set_xticklabels([f"{s:g}%の束\n（1束に{e}件）" for s, e in zip(clus.share_bad_batches_pct, clus.errors_per_bad_batch)], fontsize=8)
    ax.axhline(5, color=INK, lw=0.8, ls="--"); ax.set_ylabel("誤りを1件も見つけられない割合（%）"); ax.set_xlabel("誤りのある束の割合（全体の誤り率はどれも1%）")
    ax.legend(fontsize=8, frameon=False, loc="upper left"); ax.set_title("誤りが固まるほど、束で抜く方法は見逃す。でたらめに抜けば変わらない")
    save(fig, "a379_clustered.png", SRC)


if __name__ == "__main__":
    main()
