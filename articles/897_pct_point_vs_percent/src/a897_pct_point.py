"""897 「10%から12%」は、2%増か20%増か？（架空のデータ）

割合の変化には、差で書く「%ポイント」（12−10＝2ポイント）と、元の割合に対する変わった率（2÷10＝20%）の2つがある。
架空の会社の割合の指標600個（低い割合・中くらい・高い割合の3種類、作成者が置いたもの）で、
2つの書き方の数字がどれだけ違うか、「変化が5以上なら大きい」と読む線を引くと判定がどれだけ割れるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 897
SRC = "架空の会社の割合の指標（作成者が乱数で作成、seed 897）"
N_PER = 200
KINDS = {  # 種類: (名前, Beta の a, b)  平均 a/(a+b)
    "low": ("低い割合（購入率など、平均5%）", 5, 95),
    "mid": ("中くらい（クーポンの利用率など、平均30%）", 15, 35),
    "high": ("高い割合（会員の継続率など、平均80%）", 40, 10),
}
GENS = {"logit": "割合の目盛りをならした変化（基本）", "point": "%ポイントで同じ大きさの変化", "ratio": "変わった率で同じ大きさの変化"}


def make_metrics(rng, gen="logit", n=N_PER):
    rows = []
    for k, (name, a, b) in KINDS.items():
        p0 = rng.beta(a, b, n)
        if gen == "logit":  # ロジット（log(p/(1-p))）の目盛りで +0.05・標準偏差0.15
            z = np.log(p0 / (1 - p0)) + rng.normal(0.05, 0.15, n)
            p1 = 1 / (1 + np.exp(-z))
        elif gen == "point":  # %ポイントで平均+0.5・標準偏差2
            p1 = p0 + rng.normal(0.005, 0.02, n)
        else:  # 変わった率で平均+3%・標準偏差10%
            p1 = p0 * (1 + rng.normal(0.03, 0.10, n))
        p1 = np.clip(p1, 0.001, 0.999)
        rows.append(pd.DataFrame({"kind": k, "p0": p0, "p1": p1}))
    df = pd.concat(rows, ignore_index=True)
    df.insert(0, "metric_id", np.arange(1, len(df) + 1))
    df["pt"] = (df.p1 - df.p0) * 100          # %ポイント
    df["rel"] = (df.p1 / df.p0 - 1) * 100     # 変わった率（%）
    return df


def split(df, t):
    big_pt, big_rel = df.pt.abs() >= t, df.rel.abs() >= t
    return {"big_pt": round(float(big_pt.mean()), 3), "big_rel": round(float(big_rel.mean()), 3),
            "disagree": round(float((big_pt != big_rel).mean()), 3),
            "big_rel_only": round(float((big_rel & ~big_pt).mean()), 3),
            "big_pt_only": round(float((big_pt & ~big_rel).mean()), 3)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例：3つの指標の、2つの書き方と読み違え
    ex = []
    for name, a, b in [("10%→12%（題名の例）", 10, 12), ("購入率 4%→5%", 4, 5),
                       ("クーポンの利用率 30%→33%", 30, 33), ("会員の継続率 80%→84%", 80, 84)]:
        pt, rel = b - a, (b / a - 1) * 100
        ex.append({"example": name, "before": a, "after": b, "pt": round(pt, 2), "rel": round(rel, 2),
                   "ratio_rel_over_pt": round(rel / pt, 2),
                   "pt_read_as_rel_after": round(a * (1 + pt / 100), 2),   # 「2%増」を率と読む
                   "rel_read_as_pt_after": round(a + rel, 2)})              # 「20%増」をポイントと読む
    pd.DataFrame(ex).to_csv(RES / "examples.csv", index=False)

    # 2) 基本の600個
    df = make_metrics(rng)
    df.to_csv(DATA / "metrics.csv", index=False, float_format="%.5f")
    by_kind = {}
    for k in KINDS:
        g = df[df.kind == k]
        by_kind[k] = {"name": KINDS[k][0], "p0_median": round(float(g.p0.median() * 100), 2),
                      "ratio_median": round(float((g.rel.abs() / g.pt.abs()).median()), 2),
                      "pt_abs_median": round(float(g.pt.abs().median()), 2),
                      "rel_abs_median": round(float(g.rel.abs().median()), 2),
                      "t5": split(g, 5)}
    rel_bigger = float((df.rel.abs() > df.pt.abs()).mean())
    ratio_err = float(np.nanmax(np.abs(df.rel / df.pt - 1 / df.p0)))
    base = {"n": int(len(df)), "share_rel_bigger": round(rel_bigger, 3), "max_abs_err_ratio_vs_100_over_p0": round(ratio_err, 9), "t5_all": split(df, 5), "by_kind": by_kind}

    # 3) 確かめ：変化の作り方3通り×線の位置3通り（各、指標600個を100回作り直した平均）
    rob = []
    for gen in GENS:
        for t in [2, 5, 10]:
            acc = []
            for r in range(100):
                g = make_metrics(np.random.default_rng(SEED * 100 + r + 1000 * list(GENS).index(gen)), gen)
                s = {"all": split(g, t)}
                for k in KINDS:
                    s[k] = split(g[g.kind == k], t)
                acc.append(s)
            row = {"gen": gen, "gen_name": GENS[gen], "threshold": t}
            for part in ["all"] + list(KINDS):
                for key in ["big_pt", "big_rel", "disagree"]:
                    row[f"{part}_{key}"] = round(float(np.mean([a[part][key] for a in acc])), 3)
            rob.append(row)
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    dis = rob.all_disagree
    rng_dis = {"min": round(float(dis.min()), 3), "max": round(float(dis.max()), 3),
               "base_t5_logit": float(rob[(rob.gen == "logit") & (rob.threshold == 5)].all_disagree.iloc[0])}
    hi = rob.high_disagree
    lo = rob.low_disagree
    kind_range = {"low_min": round(float(lo.min()), 3), "low_max": round(float(lo.max()), 3),
                  "high_min": round(float(hi.min()), 3), "high_max": round(float(hi.max()), 3)}

    out = {"examples": ex, "base_600": base, "robustness_disagree_all": rng_dis,
           "robustness_disagree_by_kind": kind_range,
           "note": "変わった率÷%ポイント＝100÷元の割合（%）。元の割合が100%未満なら変わった率の数字のほうが必ず大きい（式どおり）"}

    # 図1：例の4つ
    e = pd.DataFrame(ex)
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    y = np.arange(len(e))[::-1]
    ax.barh(y + 0.18, e.pt, 0.36, color=BLUE, label="%ポイント（差）")
    ax.barh(y - 0.18, e.rel, 0.36, color=ORANGE, label="変わった率（%）")
    for yi, a, b in zip(y, e.pt, e.rel):
        ax.text(a + 0.4, yi + 0.18, f"{a:g}ポイント", va="center", fontsize=9)
        ax.text(b + 0.4, yi - 0.18, f"{b:g}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(e.example)
    ax.set_xlim(0, 32); ax.set_xlabel("変化の大きさ（同じ変化を2つの書き方で）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("元の割合が低いほど、2つの書き方の数字は大きく離れる")
    save(fig, "a897_examples.png", SRC)

    # 図2：600個の散らばり（%ポイントと変わった率）
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    cols = {"low": ORANGE, "mid": GREEN, "high": BLUE}
    for k in KINDS:
        g = df[df.kind == k]
        ax.scatter(g.pt, g.rel, s=9, color=cols[k], alpha=.55, lw=0, label=KINDS[k][0])
    for v in [-5, 5]:
        ax.axvline(v, color=GRAY, lw=.8, ls="--"); ax.axhline(v, color=GRAY, lw=.8, ls="--")
    ax.set_xlim(-10, 10); ax.set_ylim(-40, 60)
    ax.set_xlabel("%ポイント（差）"); ax.set_ylabel("変わった率（%）")
    ax.text(5.3, 55, "点線：±5", color=GRAY, fontsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title(f"「5以上なら大きい」と読むと、600個のうち{base['t5_all']['disagree']*100:.1f}%で判定が割れた")
    save(fig, "a897_scatter.png", SRC)

    # 図3：確かめ（判定が割れた割合）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    w = 0.26
    xs = np.arange(3)
    for i, (gen, c) in enumerate(zip(GENS, [BLUE, GREEN, ORANGE])):
        v = rob[rob.gen == gen].sort_values("threshold").all_disagree * 100
        ax.bar(xs + (i - 1) * w, v, w, color=c, label=GENS[gen])
        for xx, vv in zip(xs + (i - 1) * w, v):
            ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels(["線が2", "線が5", "線が10"])
    ax.set_ylabel("判定が割れた割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("判定が割れる割合は、線の位置と変化の作り方で動く（各100回の平均）")
    save(fig, "a897_robustness.png", SRC)

    json.dump(out, open(RES / "a897_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
