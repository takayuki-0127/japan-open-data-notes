"""885 案件の時給は、やり取りや修正の時間を入れるとどれだけ下がるのか？（架空のデータ）

架空の副業の人の架空の案件3,000件。作業時間・報酬（見かけの時給×作業時間）を置き、
やり取りの時間（案件ごとの決まった分＋作業に比例する分）と修正の時間（回数×作業の一定割合）を足して、
「作業時間だけで割った時給」と「やり取り・修正も入れて割った時給」を比べる。
時給は円ではなく、見かけの時給の全体の中央値を100とする指数で表す。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 885
SRC = "架空の案件（作成者が乱数で作成、seed 885）"
N = 3000
BASE = dict(F=1.0, c=0.10, lam=1.2, r=0.15, rev_talk=0.3)
CLASS_BINS = [0, 3, 10, 30, np.inf]
CLASS_LAB = ["3時間未満", "3〜10時間", "10〜30時間", "30時間以上"]


def make_projects(rng, n=N, F=1.0, c=0.10, lam=1.2, r=0.15, rev_talk=0.3):
    work = np.exp(rng.uniform(np.log(1), np.log(60), n))            # 作業時間 1〜60時間（対数で一様）
    rate = 100 * np.exp(rng.normal(0, 0.3, n))                      # 見かけの時給（指数）
    reward = rate * work
    fixed = rng.gamma(2.0, F / 2.0, n) if F > 0 else np.zeros(n)    # 1件ごとの決まったやり取り（平均 F 時間）
    talk = fixed + c * work                                          # やり取りの時間
    k = rng.negative_binomial(1.5, 1.5 / (1.5 + lam), n) if lam > 0 else np.zeros(n, int)  # 修正の回数（平均 lam）
    idx = np.repeat(np.arange(n), k)                                 # 修正1回の重さ：作業時間×r×(0.5〜1.5の一様)
    rev = np.bincount(idx, weights=r * work[idx] * rng.uniform(0.5, 1.5, len(idx)), minlength=n) + rev_talk * k
    total = work + talk + rev
    df = pd.DataFrame({"project_id": np.arange(1, n + 1), "work_h": work, "talk_h": talk, "n_revision": k,
                       "revision_h": rev, "total_h": total, "reward": reward})
    df["hourly_work"] = df.reward / df.work_h
    df["hourly_all"] = df.reward / df.total_h
    df["size"] = pd.cut(df.work_h, CLASS_BINS, labels=CLASS_LAB, right=False)
    return df


def summarize(df):
    ratio = df.hourly_all / df.hourly_work
    k = int(len(df) * 0.2)
    top_w = set(df.nlargest(k, "hourly_work").project_id)
    top_a = set(df.nlargest(k, "hourly_all").project_id)
    by = (1 - ratio).groupby(df["size"], observed=False).median()
    return {"drop_median": float(1 - ratio.median()),
            "drop_total": float(1 - df.work_h.sum() / df.total_h.sum()),
            "drop_by_size": {s: float(by[s]) for s in CLASS_LAB},
            "top20_kept": len(top_w & top_a) / k,
            "spearman": float(df.hourly_work.rank().corr(df.hourly_all.rank())),
            "top20_all_small_share": float(df[df.project_id.isin(top_a)].work_h.lt(3).mean()),
            "top20_work_small_share": float(df[df.project_id.isin(top_w)].work_h.lt(3).mean())}


def r3(x):
    if isinstance(x, dict):
        return {k: r3(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r3(v) for v in x]
    return round(float(x), 3)


def main():
    rng = np.random.default_rng(SEED)
    df = make_projects(rng)
    med = df.hourly_work.median()
    df["hourly_work"] = df.hourly_work / med * 100
    df["hourly_all"] = df.hourly_all / med * 100
    df.reward = df.reward / med * 100
    out_df = df.drop(columns="size").round(4)
    out_df.to_csv(DATA / "projects.csv", index=False)

    # 1) 基本の置き方：200回の平均
    reps = [summarize(make_projects(np.random.default_rng(SEED * 1000 + i))) for i in range(200)]
    base = {k: (float(np.mean([r[k] for r in reps])) if not isinstance(reps[0][k], dict)
                else {s: float(np.mean([r[k][s] for r in reps])) for s in CLASS_LAB}) for k in reps[0]}
    base["drop_median_p05_p95"] = [float(np.quantile([r["drop_median"] for r in reps], q)) for q in (.05, .95)]

    one = summarize(df)
    talk_share = float(df.talk_h.sum() / df.total_h.sum()); rev_share = float(df.revision_h.sum() / df.total_h.sum())
    by_size = df.groupby("size", observed=False).agg(n=("project_id", "size"), work_h_median=("work_h", "median"),
                                                     talk_h_median=("talk_h", "median"),
                                                     revision_h_median=("revision_h", "median"),
                                                     hourly_work_median=("hourly_work", "median"),
                                                     hourly_all_median=("hourly_all", "median"))
    by_size["drop_median"] = (1 - df.hourly_all / df.hourly_work).groupby(df["size"], observed=False).median()
    by_size.round(3).to_csv(RES / "by_size_one_draw.csv")
    df["rev_cls"] = np.minimum(df.n_revision, 4).astype(str).replace({"4": "4回以上"})
    by_rev = df.groupby("rev_cls").agg(n=("project_id", "size"),
                                      drop_median=("hourly_all", lambda s: float((1 - s / df.loc[s.index, "hourly_work"]).median())))
    by_rev.round(3).to_csv(RES / "by_revision_one_draw.csv")

    # 2) 頑健性：決まったやり取り F・修正の回数 lam・1回の修正の重さ r を変える（各20回の平均）
    rows = []
    for F in [0, 0.5, 1.0, 2.0]:
        for lam in [0.5, 1.2, 2.5]:
            for r in [0.10, 0.15, 0.30]:
                rs = [summarize(make_projects(np.random.default_rng(SEED * 7 + 100 * i + int(F * 10) + int(lam * 1000) + int(r * 100000)),
                                              F=F, lam=lam, r=r)) for i in range(20)]
                row = {"F": F, "lam": lam, "r": r}
                for k in ["drop_median", "drop_total", "top20_kept", "spearman"]:
                    row[k] = float(np.mean([x[k] for x in rs]))
                for s in CLASS_LAB:
                    row["drop_" + s] = float(np.mean([x["drop_by_size"][s] for x in rs]))
                rows.append(row)
    grid = pd.DataFrame(rows).round(3)
    grid.to_csv(RES / "robustness_grid.csv", index=False)
    rng_summary = {k: [float(grid[k].min()), float(grid[k].max())] for k in
                   ["drop_median", "drop_total", "top20_kept", "drop_3時間未満", "drop_30時間以上"]}
    f0 = grid[grid.F == 0]
    gap = (grid["drop_3時間未満"] - grid["drop_30時間以上"])
    rob = {"ranges_all36": rng_summary,
           "F0_small_minus_large_gap": [float(gap[grid.F == 0].min()), float(gap[grid.F == 0].max())],
           "Fpos_small_minus_large_gap": [float(gap[grid.F > 0].min()), float(gap[grid.F > 0].max())],
           "F0_drop_median_range": [float(f0.drop_median.min()), float(f0.drop_median.max())]}
    # 式：中央値ではなく合計で見た下がり方は（やり取り＋修正）÷（全部の時間）
    theory_total = float((BASE["F"] + BASE["c"] * df.work_h.mean() +
                          BASE["lam"] * (BASE["r"] * df.work_h.mean() + BASE["rev_talk"])) /
                         (df.work_h.mean() * (1 + BASE["c"] + BASE["lam"] * BASE["r"]) + BASE["F"] + BASE["lam"] * BASE["rev_talk"]))

    out = {"assumptions": BASE, "base_200reps": r3(base), "one_draw": r3(one),
           "one_draw_share_of_time": {"talk": round(talk_share, 3), "revision": round(rev_share, 3)},
           "theory_drop_total_base": round(theory_total, 3), "robustness": r3(rob)}
    json.dump(out, open(RES / "a885_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：作業時間と、時給の下がり方（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.work_h, (df.hourly_all / df.hourly_work) * 100, s=6, color=BLUE, alpha=.35, lw=0)
    xs = np.exp(np.linspace(0, np.log(60), 30))
    mids = [np.median((df.hourly_all / df.hourly_work)[(df.work_h >= a) & (df.work_h < b)]) * 100
            for a, b in zip(xs[:-1], xs[1:])]
    ax.plot(np.sqrt(xs[:-1] * xs[1:]), mids, color=ORANGE, lw=2, label="中央値")
    ax.set_xscale("log"); ax.set_xticks([1, 2, 5, 10, 20, 50]); ax.set_xticklabels(["1", "2", "5", "10", "20", "50"])
    ax.set_xlabel("作業時間（時間、対数の目盛り）")
    ax.set_ylabel("やり取り・修正を入れた時給\n（作業時間だけの時給＝100）")
    ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("作業時間の短い案件ほど、やり取りと修正を入れると時給が下がる（案件3,000件）")
    save(fig, "a885_scatter.png", SRC)

    # 図2：大きさ別の下がり方（決まったやり取り F を変える、修正は基本の置き方）
    sub = grid[(grid.lam == 1.2) & (grid.r == 0.15)]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.2
    cols = [GRAY, LIGHT, BLUE, INK]
    for j, (F, cc) in enumerate(zip(sub.F, cols)):
        vals = [sub[sub.F == F]["drop_" + s].iloc[0] * 100 for s in CLASS_LAB]
        x = np.arange(4) + (j - 1.5) * w
        ax.bar(x, vals, w * 0.92, color=cc, label=f"1件ごとの決まったやり取り {F:g}時間")
    ax.set_xticks(range(4)); ax.set_xticklabels([f"作業{s}" for s in CLASS_LAB])
    ax.set_ylabel("時給が下がった割合（%、中央値）"); ax.set_ylim(0, 75)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
    ax.set_title("1件ごとの決まったやり取りが長いほど、小さい案件の時給が下がる")
    save(fig, "a885_by_size.png", SRC)

    # 図3：修正の回数別の下がり方（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    lab = ["0", "1", "2", "3", "4回以上"]
    vals = [by_rev.loc[l, "drop_median"] * 100 for l in lab]
    ax.bar([f"{l}回" if l != "4回以上" else l for l in lab], vals, color=BLUE, width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_xlabel("修正の回数"); ax.set_ylabel("時給が下がった割合（%、中央値）"); ax.set_ylim(0, max(vals) + 10)
    ax.set_title("修正の回数が増えるほど、時給は下がる（1回分の案件3,000件）")
    save(fig, "a885_by_revision.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(by_size.round(3)); print(by_rev.round(3))


if __name__ == "__main__":
    main()
