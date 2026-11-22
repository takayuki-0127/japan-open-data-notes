"""922 偏差値60は、上から何%なのか？（分布の形で変わるのか）（架空のデータ）

架空の資格試験。受験者ごとの実力 θ と、問題ごとの難しさ b を作成者が置き、
1問ずつ「実力が難しさを上回るほど正解しやすい」確率（ロジスティックの形）で正解すると置く。
同じ受験者に、やさしい・ふつう・むずかしい試験を受けてもらったときの得点の分布を式で正確に出し、
偏差値60以上・70以上の人の割合を数える。少人数の回の振れは乱数で数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 922
SRC = "架空の資格試験（作成者が乱数で作成、seed 922）"
rng = np.random.default_rng(SEED)
THETA = np.linspace(-6, 6, 601)
Z_ITEMS = {n: rng.normal(0, 1, n) for n in [20, 100]}       # 問題の難しさのもと（試験ごとにずらす）
EXAMS = {"やさしい試験": -2.0, "ふつうの試験": 0.0, "むずかしい試験": 2.0}
NORMAL60, NORMAL70 = float(norm.sf(1)), float(norm.sf(2))


def ability_weights(kind):
    if kind == "正規":
        w = norm.pdf(THETA)
    else:   # 2つの群：初めての人7割（平均−0.5）と経験者3割（平均+1.2）
        w = 0.7 * norm.pdf(THETA, -0.5, 0.8) + 0.3 * norm.pdf(THETA, 1.2, 0.6)
    return w / w.sum()


def score_dist(shift, items=100, a=1.0, kind="正規"):
    """得点の分布（0〜items点）を式で出す：実力ごとの正解数の分布（問題ごとに確率が違う）を足し合わせる"""
    b = Z_ITEMS[items] + shift
    p = 1 / (1 + np.exp(-1.7 * a * (THETA[:, None] - b[None, :])))
    d = np.zeros((len(THETA), items + 1)); d[:, 0] = 1
    for j in range(items):
        pj = p[:, j:j + 1]
        nd = d * (1 - pj)
        nd[:, 1:] += d[:, :-1] * pj
        d = nd
    return (ability_weights(kind)[:, None] * d).sum(0)


def describe(f):
    s = np.arange(len(f))
    m = (f * s).sum(); sd = np.sqrt((f * (s - m) ** 2).sum())
    skew = (f * (s - m) ** 3).sum() / sd ** 3
    kurt = (f * (s - m) ** 4).sum() / sd ** 4 - 3
    t = 50 + 10 * (s - m) / sd
    ge = lambda v: float(f[t >= v - 1e-9].sum())
    tail = np.cumsum(f[::-1])[::-1]                    # P(X ≥ s)
    s16 = int(np.where(tail >= NORMAL60)[0].max())     # 上から15.87%目の人の得点
    s2 = int(np.where(tail >= NORMAL70)[0].max())      # 上から2.28%目の人の得点
    return {"mean": round(float(m), 2), "sd": round(float(sd), 2), "skew": round(float(skew), 3), "excess_kurtosis": round(float(kurt), 3),
            "share_ge60": round(ge(60), 4), "share_ge70": round(ge(70), 4), "share_lt40": round(float(f[t < 40 - 1e-9].sum()), 4),
            "dev_of_top15_87": round(float(t[s16]), 2), "dev_of_top2_28": round(float(t[s2]), 2),
            "max_dev": round(float(t[f > 1e-12].max()), 2), "min_dev": round(float(t[f > 1e-12].min()), 2)}


def main():
    t0 = time.time()
    # 1) 同じ受験者に、3つの難しさの試験
    base, dists = {}, {}
    for name, sh in EXAMS.items():
        f = score_dist(sh); dists[name] = f
        base[name] = describe(f)
    rows = []
    for name, f in dists.items():
        d = base[name]
        for s, q in enumerate(f):
            rows.append({"exam": name, "score": s, "prob": round(float(q), 6),
                         "deviation": round(50 + 10 * (s - d["mean"]) / d["sd"], 2)})
    pd.DataFrame(rows).to_csv(DATA / "score_dist_3exams.csv", index=False)

    # 2) 確かめ：難しさ×問題数×問題の見分ける力×実力の分布
    rob = []
    for kind in ["正規", "2つの群"]:
        for items in [20, 100]:
            for a in [0.6, 1.0, 1.6]:
                for sh in np.arange(-3, 3.01, 0.5):
                    d = describe(score_dist(sh, items, a, kind))
                    rob.append({"ability": kind, "items": items, "a": a, "shift": round(float(sh), 1), **d})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # 3) 少人数の回：ふつうの試験の受験者から30人・300人を取り、その回の平均と標準偏差で偏差値を出す
    f = dists["ふつうの試験"]
    small = {}
    for n in [30, 300]:
        x = rng.choice(len(f), size=(20000, n), p=f)
        m = x.mean(1, keepdims=True); sd = x.std(1, keepdims=True)
        t = 50 + 10 * (x - m) / sd
        sh = (t >= 60 - 1e-9).mean(1)
        small[str(n)] = {"p10": round(float(np.quantile(sh, .1)), 4), "median": round(float(np.median(sh)), 4),
                         "p90": round(float(np.quantile(sh, .9)), 4),
                         "share_sessions_off_5pts": round(float((np.abs(sh - base["ふつうの試験"]["share_ge60"]) > 0.05).mean()), 4),
                         "_sh": sh}
        if n == 30:
            one = pd.DataFrame({"person": np.arange(1, n + 1), "score": x[0],
                                "deviation": np.round(t[0], 2)}).sort_values("score", ascending=False)
            one.to_csv(DATA / "small_session_30.csv", index=False)
            small["30"]["first_session_share_ge60"] = round(float(sh[0]), 4)

    out = {"normal_share_ge60": round(NORMAL60, 4), "normal_share_ge70": round(NORMAL70, 4),
           "three_exams": base,
           "robust_all": {"share_ge60_min": float(rob.share_ge60.min()), "share_ge60_max": float(rob.share_ge60.max()),
                          "share_ge70_min": float(rob.share_ge70.min()), "share_ge70_max": float(rob.share_ge70.max()),
                          "dev_top15_87_min": float(rob.dev_of_top15_87.min()),
                          "dev_top15_87_max": float(rob.dev_of_top15_87.max()),
                          "n_settings": int(len(rob)),
                          "n_full_marks_below_60": int((rob.max_dev < 60).sum())},
           "shift0_share_ge60_min": float(rob[rob["shift"] == 0].share_ge60.min()),
           "shift0_share_ge60_max": float(rob[rob["shift"] == 0].share_ge60.max()),
           "shift0_kurt_min": float(rob[rob["shift"] == 0].excess_kurtosis.min()),
           "shift0_kurt_max": float(rob[rob["shift"] == 0].excess_kurtosis.max()),
           "small_sessions": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in small.items()}}
    for kind in ["正規", "2つの群"]:
        q = rob[rob.ability == kind]
        out[f"robust_{kind}"] = {"share_ge60_min": float(q.share_ge60.min()),
                                           "share_ge60_max": float(q.share_ge60.max()),
                                           "share_ge70_min": float(q.share_ge70.min()),
                                           "share_ge70_max": float(q.share_ge70.max())}
    json.dump(out, open(RES / "a922_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：3つの試験の得点の分布と偏差値60の位置
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6), sharey=True)
    for ax, (name, f) in zip(axes, dists.items()):
        d = base[name]
        s = np.arange(len(f))
        t = 50 + 10 * (s - d["mean"]) / d["sd"]
        ax.bar(s, f * 100, width=1.0, color=np.where(t >= 60 - 1e-9, ORANGE, LIGHT))
        x60 = d["mean"] + d["sd"]
        ax.axvline(x60, color=INK, lw=1, ls="--")
        ax.set_title(f"{name}\n偏差値60以上 {d['share_ge60']*100:.1f}%", fontsize=11)
        ax.set_xlabel("得点（100問）"); ax.set_xlim(0, 100)
    axes[0].set_ylabel("受験者の割合（%）")
    fig.suptitle("同じ受験者でも、試験の難しさで偏差値60以上の割合が変わる（点線＝偏差値60）", y=1.04, fontsize=12)
    save(fig, "a922_three_exams.png", SRC, y=-0.04)

    # 図2：難しさと偏差値60以上・70以上の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for kind, ls in [("正規", "-"), ("2つの群", "--")]:
        q = rob[(rob["items"] == 100) & (rob.a == 1.0) & (rob.ability == kind)]
        ax.plot(q["shift"], q.share_ge60 * 100, color=BLUE, ls=ls, marker="o", ms=3, label=f"偏差値60以上（実力：{kind}）")
        ax.plot(q["shift"], q.share_ge70 * 100, color=ORANGE, ls=ls, marker="o", ms=3, label=f"偏差値70以上（実力：{kind}）")
    ax.axhline(NORMAL60 * 100, color=BLUE, lw=0.8, ls=":"); ax.axhline(NORMAL70 * 100, color=ORANGE, lw=0.8, ls=":")
    ax.text(3.05, NORMAL60 * 100, "正規分布\n15.87%", color=BLUE, fontsize=8, va="center")
    ax.text(3.05, NORMAL70 * 100, "正規分布\n2.28%", color=ORANGE, fontsize=8, va="center")
    ax.set_xlabel("試験の難しさ（問題の難しさの平均、0がふつう、＋がむずかしい）")
    ax.set_ylabel("受験者の割合（%）"); ax.set_ylim(0, 31)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    ax.set_title("むずかしい試験ほど偏差値70以上が増え、やさしい試験ほど減る（100問）")
    save(fig, "a922_by_difficulty.png", SRC)

    # 図3：少人数の回の振れ
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for n, col, wd in [("30", ORANGE, 2.4), ("300", BLUE, 0.28)]:
        v, c = np.unique(np.round(small[n]["_sh"] * 100, 4), return_counts=True)
        ax.bar(v, c / c.sum() * 100, width=wd, color=col, alpha=.75, label=f"{n}人の回")
    ax.axvline(base["ふつうの試験"]["share_ge60"] * 100, color=INK, lw=1, ls="--")
    ax.set_xlabel("その回で偏差値60以上だった人の割合（%）"); ax.set_ylabel("回の割合（%）")
    ax.set_xlim(0, 40)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("30人の回では、偏差値60以上の割合が回ごとに大きく動く（ふつうの試験）")
    save(fig, "a922_small_sessions.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
