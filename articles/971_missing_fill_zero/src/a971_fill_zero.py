"""971 空欄を0で埋めると、平均と割合はどうなるのか？（架空のデータ）

架空のカフェの会員アンケート（回答3,000人）。「この1か月に、店の物販（豆・グッズ）に使った金額」の欄に空欄がある。
本当に使った金額は作成者が全員分置く（使った人は45%、使った人の金額は対数正規分布で中央値1,500円）。
空欄になる確率は、本当に0円の人で30%、使った人で15%と置く（使わなかった人ほど書かずに飛ばす）。
回答は紙（40%）とWeb（60%）の2つの入口から来る。使い方は入口で同じと置き、紙のほうが空欄が多いと置く。
空欄の扱いは2つ：(1) 0円で埋める、(2) 空欄を除く。全員の本当の値と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 971
SRC = "架空のカフェの会員アンケート（作成者が乱数で作成、seed 971）"
N = 3000
REPS = 300
P_SPEND = 0.45
MEDIAN_YEN, SIGMA = 1500, 0.8
P_PAPER = 0.4
# 空欄になる確率（本当に0円の人、使った人）：入口ごと
Q = {"paper": (0.45, 0.25), "web": (0.20, 0.0833)}


def q_overall():
    q0 = P_PAPER * Q["paper"][0] + (1 - P_PAPER) * Q["web"][0]
    q1 = P_PAPER * Q["paper"][1] + (1 - P_PAPER) * Q["web"][1]
    return q0, q1


def make(rng, n=N, p_spend=P_SPEND, q=None):
    paper = rng.random(n) < P_PAPER
    spend = rng.random(n) < p_spend
    amt = np.where(spend, np.round(MEDIAN_YEN * np.exp(rng.normal(0, SIGMA, n)), -1), 0.0)
    amt = np.where(spend & (amt < 10), 10.0, amt)
    if q is None:
        q0 = np.where(paper, Q["paper"][0], Q["web"][0])
        q1 = np.where(paper, Q["paper"][1], Q["web"][1])
    else:
        q0, q1 = np.full(n, q[0]), np.full(n, q[1])
    blank = rng.random(n) < np.where(spend, q1, q0)
    return paper, spend, amt, blank


def readings(amt, blank, mask=None):
    if mask is None:
        mask = np.ones(len(amt), bool)
    a, b = amt[mask], blank[mask]
    filled = np.where(b, 0.0, a)
    kept = a[~b]
    return {"mean_true": a.mean(), "mean_zero": filled.mean(), "mean_drop": kept.mean(),
            "share_true": (a > 0).mean(), "share_zero": (filled > 0).mean(), "share_drop": (kept > 0).mean(),
            "spender_mean_true": a[a > 0].mean(), "spender_mean_zero": filled[filled > 0].mean(),
            "spender_mean_drop": kept[kept > 0].mean(),
            "blank_rate": b.mean(), "blank_true_zero_share": (a[b] == 0).mean() if b.any() else np.nan}


def one(rng, **kw):
    paper, spend, amt, blank = make(rng, **kw)
    o = readings(amt, blank)
    if kw.get("q") is None:
        for nm, mk in [("paper", paper), ("web", ~paper)]:
            for k, v in readings(amt, blank, mk).items():
                o[f"{nm}_{k}"] = v
    return o


def run(seed0, reps, **kw):
    d = pd.DataFrame([one(np.random.default_rng(seed0 + r), **kw) for r in range(reps)])
    for k in ["mean", "share", "spender_mean"]:
        for m in ["zero", "drop"]:
            d[f"{k}_{m}_err_pct"] = (d[f"{k}_{m}"] / d[f"{k}_true"] - 1) * 100
    return d


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    q0, q1 = q_overall()
    res = {"setting": {"respondents": N, "reps": REPS, "p_spend": P_SPEND, "median_yen": MEDIAN_YEN, "sigma_log": SIGMA,
                       "paper_share": P_PAPER, "blank_prob_paper_zero_spender": list(Q["paper"]),
                       "blank_prob_web_zero_spender": list(Q["web"]), "blank_prob_overall_zero_spender": [r4(q0), r4(q1)]}}

    # 1) 例の回答3,000人（data）
    rng = np.random.default_rng(SEED)
    paper, spend, amt, blank = make(rng)
    pd.DataFrame({"respondent_id": np.arange(1, N + 1), "channel": np.where(paper, "paper", "web"),
                  "true_yen": amt.astype(int), "answer_yen": np.where(blank, "", amt.astype(int).astype(str))}
                 ).to_csv(DATA / "answers_example.csv", index=False)

    # 2) 基本（300回）
    d = run(SEED * 1000, REPS)
    keys = ["mean_true", "mean_zero", "mean_drop", "share_true", "share_zero", "share_drop",
            "spender_mean_true", "spender_mean_zero", "spender_mean_drop", "blank_rate", "blank_true_zero_share",
            "mean_zero_err_pct", "mean_drop_err_pct", "share_zero_err_pct", "share_drop_err_pct",
            "spender_mean_zero_err_pct", "spender_mean_drop_err_pct"]
    base = {k: r4(d[k].mean()) for k in keys}
    for k in ["mean_zero_err_pct", "mean_drop_err_pct"]:
        base[k + "_p10"] = r4(d[k].quantile(.1)); base[k + "_p90"] = r4(d[k].quantile(.9))
    for k in ["share_true", "share_zero", "share_drop"]:
        base[k.replace("share", "share_pt")] = r4(d[k].mean() * 100)
    res["base"] = base
    # 式どおりの確かめ（空欄が金額と関係なく起きると置いたので、0で埋めた値は本当の値×(1−q1)）
    res["formula"] = {"share_zero": r4(P_SPEND * (1 - q1)),
                      "share_drop": r4(P_SPEND * (1 - q1) / (P_SPEND * (1 - q1) + (1 - P_SPEND) * (1 - q0))),
                      "mean_zero_err_pct": r4(-q1 * 100),
                      "blank_true_zero_share": r4((1 - P_SPEND) * q0 / ((1 - P_SPEND) * q0 + P_SPEND * q1)),
                      "blank_rate": r4((1 - P_SPEND) * q0 + P_SPEND * q1)}

    # 3) 紙とWeb（使い方は同じと置いた）
    ch = {}
    for nm in ["paper", "web"]:
        for k in ["mean_true", "mean_zero", "mean_drop", "share_true", "share_zero", "share_drop", "blank_rate",
                  "blank_true_zero_share"]:
            ch[f"{nm}_{k}"] = r4(d[f"{nm}_{k}"].mean())
    for k in ["mean_true", "mean_zero", "mean_drop"]:
        ch[f"diff_{k}_yen"] = r4((d[f"paper_{k}"] - d[f"web_{k}"]).mean())
        ch[f"ratio_{k}_paper_over_web"] = r4((d[f"paper_{k}"] / d[f"web_{k}"]).mean())
    for k in ["share_true", "share_zero", "share_drop"]:
        ch[f"diff_{k}_pt"] = r4((d[f"paper_{k}"] - d[f"web_{k}"]).mean() * 100)
    ch["runs_paper_lower_mean_zero"] = r4((d.paper_mean_zero < d.web_mean_zero).mean())
    ch["runs_paper_higher_mean_drop"] = r4((d.paper_mean_drop > d.web_mean_drop).mean())
    ch["runs_paper_lower_mean_true"] = r4((d.paper_mean_true < d.web_mean_true).mean())
    res["channels"] = ch

    # 4) 確かめ：使った人の割合 × 空欄の確率（0円の人・使った人）、各100回
    grid, k = [], 0
    for p in [0.25, 0.45, 0.70]:
        for qq0 in [0.10, 0.30, 0.50]:
            for qq1 in [0.0, 0.05, 0.15, 0.30]:
                s = run(SEED * 5000 + k * 1000, 100, p_spend=p, q=(qq0, qq1))
                k += 1
                grid.append({"p_spend": p, "blank_prob_zero": qq0, "blank_prob_spender": qq1,
                             "blank_rate": r4(s.blank_rate.mean()), "blank_true_zero_share": r4(s.blank_true_zero_share.mean()),
                             "mean_zero_err_pct": r4(s.mean_zero_err_pct.mean()), "mean_drop_err_pct": r4(s.mean_drop_err_pct.mean()),
                             "share_zero_err_pct": r4(s.share_zero_err_pct.mean()), "share_drop_err_pct": r4(s.share_drop_err_pct.mean()),
                             "share_zero_err_pt": r4((s.share_zero - s.share_true).mean() * 100),
                             "share_drop_err_pt": r4((s.share_drop - s.share_true).mean() * 100)})
    grid = pd.DataFrame(grid)
    grid["zero_fill_closer_mean"] = grid.mean_zero_err_pct.abs() < grid.mean_drop_err_pct.abs()
    grid.to_csv(RES / "robustness.csv", index=False)
    g1 = grid[grid.blank_prob_spender > 0]
    closer = grid[grid.zero_fill_closer_mean]
    farther = grid[~grid.zero_fill_closer_mean]
    res["robustness"] = {
        "combos": int(len(grid)),
        "combos_spender_blank_gt0": int(len(g1)),
        "mean_zero_err_pct_range_spender_blank_gt0": [r4(g1.mean_zero_err_pct.min()), r4(g1.mean_zero_err_pct.max())],
        "share_zero_err_pct_range_spender_blank_gt0": [r4(g1.share_zero_err_pct.min()), r4(g1.share_zero_err_pct.max())],
        "mean_drop_err_pct_range_all": [r4(grid.mean_drop_err_pct.min()), r4(grid.mean_drop_err_pct.max())],
        "share_zero_err_pt_range_spender_blank_gt0": [r4(g1.share_zero_err_pt.min()), r4(g1.share_zero_err_pt.max())],
        "share_drop_err_pt_range_all": [r4(grid.share_drop_err_pt.min()), r4(grid.share_drop_err_pt.max())],
        "combos_zero_fill_closer_mean": int(len(closer)),
        "blank_true_zero_share_when_zero_fill_closer_min": r4(closer.blank_true_zero_share.min()),
        "blank_true_zero_share_when_drop_closer_max": r4(farther.blank_true_zero_share.max()),
        "combos_equal_blank_prob": int((grid.blank_prob_zero == grid.blank_prob_spender).sum()),
    }

    b = base
    # 図1：平均金額と使った人の割合
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4))
    labs = ["本当の値\n（空欄なし）", "空欄を\n0円で埋める", "空欄を\n除く"]
    cols = [BLUE, ORANGE, GREEN]
    for ax, vals, unit, ttl in [(axes[0], [b["mean_true"], b["mean_zero"], b["mean_drop"]], "円", "1人あたりの平均金額"),
                                (axes[1], [b["share_true"] * 100, b["share_zero"] * 100, b["share_drop"] * 100], "%", "使った人の割合")]:
        bars = ax.bar(labs, vals, color=cols, width=0.6)
        for b_, v, v0 in zip(bars, vals, [vals[0]] * 3):
            t = f"{v:,.0f}円" if unit == "円" else f"{v:.1f}%"
            if v != v0:
                t += f"\n（{(v / v0 - 1) * 100:+.1f}%）"
            ax.text(b_.get_x() + b_.get_width() / 2, v * 1.02, t, ha="center", va="bottom", fontsize=9.5)
        ax.set_ylim(0, max(vals) * 1.3)
        ax.set_title(ttl, fontsize=11.5)
    axes[0].set_ylabel("円（300回の平均）"); axes[1].set_ylabel("%（300回の平均）")
    fig.suptitle(f"回答の{b['blank_rate']*100:.1f}%が空欄（うち本当に0円は{b['blank_true_zero_share']*100:.1f}%）。"
                 "0円で埋めると低く、除くと高く出る", fontsize=12)
    fig.tight_layout()
    save(fig, "a971_mean_share.png", SRC + "。回答3,000人を300回作り直した平均。括弧は本当の値とのずれ")

    # 図2：紙とWeb（使い方は同じ）
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(3)
    pv = [ch["paper_mean_true"], ch["paper_mean_zero"], ch["paper_mean_drop"]]
    wv = [ch["web_mean_true"], ch["web_mean_zero"], ch["web_mean_drop"]]
    b1 = ax.bar(x - 0.2, pv, 0.38, color=ORANGE, label=f"紙（空欄 {ch['paper_blank_rate']*100:.1f}%）")
    b2 = ax.bar(x + 0.2, wv, 0.38, color=BLUE, label=f"Web（空欄 {ch['web_blank_rate']*100:.1f}%）")
    for bars in [b1, b2]:
        for b_ in bars:
            ax.text(b_.get_x() + b_.get_width() / 2, b_.get_height() + 15, f"{b_.get_height():,.0f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(["本当の値", "空欄を0円で埋める", "空欄を除く"])
    ax.set_ylabel("1人あたりの平均金額（円）")
    ax.set_ylim(0, max(pv + wv) * 1.25)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.set_title("使い方は同じでも、空欄の多い紙は「0円で埋める」と低く、「除く」と高く見える", fontsize=11.5)
    save(fig, "a971_channels.png", SRC + "。300回の平均。紙とWebの本当の使い方は同じと置いた")

    # 図3：確かめ（空欄のうち本当に0円の割合と、平均のずれ）
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.scatter(grid.blank_true_zero_share * 100, grid.mean_zero_err_pct, color=ORANGE, label="空欄を0円で埋める", s=28)
    ax.scatter(grid.blank_true_zero_share * 100, grid.mean_drop_err_pct, color=GREEN, marker="^", label="空欄を除く", s=28)
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.scatter([b["blank_true_zero_share"] * 100] * 2, [b["mean_zero_err_pct"], b["mean_drop_err_pct"]], facecolors="none",
               edgecolors=INK, s=110, lw=1.2, label="基本の置き方")
    ax.set_xlabel("空欄のうち、本当に0円だった人の割合（%）")
    ax.set_ylabel("1人あたりの平均金額のずれ（%）")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.set_title("空欄に0円の人が多いほど「0円で埋める」が近く、少ないほど「除く」が近い\n（36通り、各100回）", fontsize=11.5)
    save(fig, "a971_robustness.png", SRC + "。使った人の割合（25・45・70%）×空欄の確率（0円の人・使った人）の36通り")

    res["run_sec"] = round(time.time() - t0, 1)
    with open(RES / "a971_main.json", "w", encoding="utf-8") as f:
        json.dump({k_: v for k_, v in res.items() if k_ != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
