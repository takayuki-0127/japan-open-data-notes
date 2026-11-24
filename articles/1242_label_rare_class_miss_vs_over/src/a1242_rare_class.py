"""1242 珍しい分類を付けるとき、付け手は見逃しと付けすぎのどちらに寄るのか？（架空のデータ）

架空の問い合わせ文20,000件。そのうち「返品の相談」（珍しい分類）は本当は3%と作成者が置く。
文ごとに「返品の相談らしさ」を置き、付け手はそれを少しぶれて読み、自分の線を超えたら「返品の相談」と付ける。
線の置き方を3つ変えて、見逃し（本当は返品の相談なのに付けなかった）と付けすぎ（本当は違うのに付けた）を数える。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1242
SRC = "架空の問い合わせ文と付け手（作成者が乱数で作成、seed 1242）"
N = 20000
PI = 0.03       # 珍しい分類の本当の割合
D = 2.5         # 珍しい分類の文の「らしさ」の中心（ほかの文は0）
SA = 0.5        # 付け手の読みのぶれ
REPS = 200

LINE_NAMES = {"half": "①2つの分類を同じ重みで見る線", "min_err": "②まちがいの数がいちばん少ない線",
              "match": "③付けた割合が本当の割合と合う線"}


def Phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def lines(pi, d, sa):
    s = math.sqrt(1 + sa ** 2)
    t_half = d / 2
    t_min = d / 2 + s ** 2 * math.log((1 - pi) / pi) / d
    lo, hi = -10.0, 20.0                       # 付けた割合 = pi になる線（二分法）
    for _ in range(200):
        mid = (lo + hi) / 2
        share = pi * (1 - Phi((mid - d) / s)) + (1 - pi) * (1 - Phi(mid / s))
        lo, hi = (mid, hi) if share > pi else (lo, mid)
    return {"half": t_half, "min_err": t_min, "match": (lo + hi) / 2}, s


def formula(t, pi, d, s, n=N):
    miss = Phi((t - d) / s)
    over = 1 - Phi(t / s)
    return {"miss_rate": miss, "over_rate": over, "misses": n * pi * miss, "overs": n * (1 - pi) * over,
            "labeled_share": pi * (1 - miss) + (1 - pi) * over, "accuracy": 1 - pi * miss - (1 - pi) * over}


def simulate(rng, pi, d, sa, ts, reps, n=N):
    """reps 回、文 n 件を作り、1人の付け手が各線で付けた結果を数える"""
    out = {k: [] for k in ts}
    for _ in range(reps):
        y_true = rng.random(n) < pi
        x = rng.normal(0, 1, n) + d * y_true
        obs = x + rng.normal(0, sa, n)
        for k, t in ts.items():
            lab = obs > t
            out[k].append((int((y_true & ~lab).sum()), int((~y_true & lab).sum()), int(y_true.sum()),
                           int(lab.sum()), int((y_true & lab).sum())))
    return {k: np.array(v) for k, v in out.items()}


def r(x, k=4):
    return round(float(x), k) + 0.0


def summarize(arr, n=N):
    miss, over, ntrue, nlab, tp = arr.T.astype(float)
    return {"misses": r(miss.mean(), 2), "overs": r(over.mean(), 2), "true_count": r(ntrue.mean(), 2),
            "labeled_count": r(nlab.mean(), 2), "labeled_share_pct": r(nlab.mean() / n * 100, 3),
            "labeled_over_true": r(nlab.mean() / ntrue.mean()),
            "miss_rate_pct": r(miss.sum() / ntrue.sum() * 100, 2),
            "wrong_among_labeled_pct": r(over.sum() / nlab.sum() * 100, 2),
            "accuracy_pct": r(100 - (miss + over).mean() / n * 100, 3),
            "overs_per_miss": r(over.mean() / miss.mean()),
            "share_rounds_overs_gt_misses": r((over > miss).mean())}


def main():
    rng = np.random.default_rng(SEED)
    ts, s = lines(PI, D, SA)
    sim = simulate(rng, PI, D, SA, ts, REPS)
    base = {}
    for k, t in ts.items():
        f = formula(t, PI, D, s)
        base[k] = {"name": LINE_NAMES[k], "line": r(t), **summarize(sim[k]),
                   "formula": {"misses": r(f["misses"], 2), "overs": r(f["overs"], 2),
                               "labeled_share_pct": r(f["labeled_share"] * 100, 3),
                               "accuracy_pct": r(f["accuracy"] * 100, 3)}}
    pd.DataFrame([{"line": k, **{kk: vv for kk, vv in v.items() if kk not in ("formula", "name")}}
                  for k, v in base.items()]).to_csv(RES / "base_lines.csv", index=False)

    # 2) 確かめ：本当の割合 × らしさの差（9通り）× 3つの線
    grid = []
    gi = 0
    for pi in [0.01, 0.03, 0.10]:
        for d in [1.5, 2.5, 3.5]:
            gi += 1
            tsg, sg = lines(pi, d, SA)
            sg_sim = simulate(np.random.default_rng(SEED * 100 + gi), pi, d, SA, tsg, 60)
            for k, t in tsg.items():
                sm = summarize(sg_sim[k])
                f = formula(t, pi, d, sg)
                grid.append({"true_share": pi, "d": d, "line": k, "misses": sm["misses"], "overs": sm["overs"],
                             "overs_per_miss": sm["overs_per_miss"], "miss_rate_pct": sm["miss_rate_pct"],
                             "labeled_over_true": sm["labeled_over_true"], "accuracy_pct": sm["accuracy_pct"],
                             "formula_overs_per_miss": r(f["overs"] / f["misses"]),
                             "formula_labeled_over_true": r(f["labeled_share"] / pi)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # 3) 見本の件（本当の分類が分かっている件）を、でたらめに選んで確かめると、向きは見分けられるか
    chk_rows = []
    check_rng = np.random.default_rng(SEED + 7)
    y_true = check_rng.random(N) < PI
    x = check_rng.normal(0, 1, N) + D * y_true
    obs = x + check_rng.normal(0, SA, N)
    for k in ["half", "min_err", "match"]:
        lab = obs > ts[k]
        miss_i = (y_true & ~lab).astype(int)
        over_i = (~y_true & lab).astype(int)
        true_dir = np.sign(over_i.sum() - miss_i.sum())
        for n_chk in [100, 300, 1000, 3000]:
            idx = np.array([check_rng.choice(N, n_chk, replace=False) for _ in range(3000)])
            m_s, o_s = miss_i[idx].sum(1), over_i[idx].sum(1)
            dirs = np.sign(o_s - m_s)
            chk_rows.append({"line": k, "n_check": n_chk, "true_overs_minus_misses": int(over_i.sum() - miss_i.sum()),
                             "rare_in_check_mean": r(y_true[idx].sum(1).mean(), 2),
                             "share_no_rare_in_check": r((y_true[idx].sum(1) == 0).mean()),
                             "correct_direction": r((dirs == true_dir).mean()), "tie": r((dirs == 0).mean()),
                             "reversed": r((dirs == -true_dir).mean())})
    chk = pd.DataFrame(chk_rows)
    chk.to_csv(RES / "check_sample.csv", index=False)

    # data：例の1回（基本）の文ごとの判定
    pd.DataFrame({"item": np.arange(1, N + 1), "true_rare": y_true.astype(int), "seen_score": np.round(obs, 4),
                  "label_half": (obs > ts["half"]).astype(int), "label_min_err": (obs > ts["min_err"]).astype(int),
                  "label_match": (obs > ts["match"]).astype(int)}).to_csv(DATA / "example_items.csv", index=False)

    g = grid
    out = {"setting": {"N": N, "true_share": PI, "d": D, "reader_noise": SA, "reps": REPS, "seen_sd": r(s)},
           "base": base,
           "grid_summary": {
               k: {"overs_per_miss_range": [r(g[g.line == k].overs_per_miss.min()), r(g[g.line == k].overs_per_miss.max())],
                   "labeled_over_true_range": [r(g[g.line == k].labeled_over_true.min()), r(g[g.line == k].labeled_over_true.max())],
                   "n_overs_gt_misses": int((g[g.line == k].overs > g[g.line == k].misses).sum()),
                   "miss_rate_pct_range": [r(g[g.line == k].miss_rate_pct.min(), 2), r(g[g.line == k].miss_rate_pct.max(), 2)],
                   "max_rel_diff_formula": r((g[g.line == k].overs_per_miss / g[g.line == k].formula_overs_per_miss - 1).abs().max())}
               for k in ts},
           "check_sample": chk.to_dict("records")}
    json.dump(out, open(RES / "a1242_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：線ごとの見逃しと付けすぎ（基本、20,000件あたり）
    keys = ["half", "match", "min_err"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    yy = np.arange(len(keys))
    h = 0.38
    mv = [base[k]["misses"] for k in keys]
    ov = [base[k]["overs"] for k in keys]
    ax.barh(yy - h / 2, mv, h, color=BLUE, label="見逃し（本当は返品の相談なのに付けなかった）")
    ax.barh(yy + h / 2, ov, h, color=ORANGE, label="付けすぎ（本当は違うのに付けた）")
    for i in range(len(keys)):
        ax.text(mv[i] + 30, i - h / 2, f"{mv[i]:,.2f}件", va="center", fontsize=8.5)
        ax.text(ov[i] + 30, i + h / 2, f"{ov[i]:,.2f}件", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels([LINE_NAMES[k] for k in keys], fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, max(ov + mv) * 1.25)
    ax.set_xlabel(f"文20,000件あたりの件数（本当の返品の相談は{base['half']['true_count']:,.2f}件、{REPS}回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("同じ付け手の読みでも、線の置き方で見逃しと付けすぎの多い方が入れかわる")
    save(fig, "a1242_lines.png", SRC)

    # 図2：付けた件数÷本当の件数（9通り×3つの線）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    combos = [(pi, d) for pi in [0.01, 0.03, 0.10] for d in [1.5, 2.5, 3.5]]
    xx = np.arange(len(combos))
    for k, c, mk in [("half", ORANGE, "o"), ("match", GREEN, "s"), ("min_err", BLUE, "D")]:
        vals = [g[(g.true_share == pi) & (g.d == d) & (g.line == k)].labeled_over_true.iloc[0] for pi, d in combos]
        ax.plot(xx, vals, marker=mk, color=c, lw=0, ms=7, label=LINE_NAMES[k])
    ax.axhline(1, color=INK, lw=1, ls="--")
    ax.set_yscale("log")
    tk = [0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30]
    ax.set_yticks(tk); ax.set_yticklabels([f"{v:g}倍" for v in tk]); ax.minorticks_off()
    ax.set_xticks(xx); ax.set_xticklabels([f"{int(pi * 100)}%\n差{d}" for pi, d in combos], fontsize=8.5)
    ax.set_xlabel("本当の割合と、らしさの差（大きいほど見分けやすい）")
    ax.set_ylabel("付けた件数÷本当の件数（対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("①は9通りすべてで多すぎ、②は9通りすべてで少なすぎ")
    save(fig, "a1242_grid.png", SRC)

    # 図3：見本の件をでたらめに選んで確かめたとき、多い方を正しく言い当てた割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xx = np.arange(4)
    w = 0.36
    for j, (k, c) in enumerate([("half", ORANGE), ("min_err", BLUE)]):
        v = chk[chk.line == k].correct_direction.values * 100
        ax.bar(xx + (j - 0.5) * w, v, w, color=c, label=LINE_NAMES[k])
        for i, vv in enumerate(v):
            ax.text(xx[i] + (j - 0.5) * w, vv + 1.5, f"{vv:.2f}", ha="center", fontsize=8)
    ax.set_xticks(xx); ax.set_xticklabels([f"{n:,}件" for n in [100, 300, 1000, 3000]])
    ax.set_ylim(0, 122); ax.set_yticks(range(0, 101, 20))
    ax.set_xlabel("でたらめに選んだ見本の件数（各3,000回）")
    ax.set_ylabel("多い方を正しく言い当てた割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)
    ax.set_title("②では、見本100件だと多い方を言い当てたのは75.20%")
    save(fig, "a1242_check.png", SRC)

    print(json.dumps({k: out[k] for k in ["base", "grid_summary"]}, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    print(grid.to_string()); print(chk.to_string())


if __name__ == "__main__":
    main()
