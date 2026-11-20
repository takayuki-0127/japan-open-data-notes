"""839 投稿の時刻の効果は、時刻の効果か、内容の効果か？（架空のデータ）

架空のアカウントの1年分の投稿360本。投稿ごとに「内容の出来」を置き、
出来の良い投稿ほど夜20時に出しやすい（作成者が置いた選び方）。時刻そのものの効果は小さく置く
（内容が同じなら、夜は朝より5.1%多く、昼は朝より4.9%少ない）。
時刻ごとの平均をそのまま比べる・「力作」の印で分けて比べる・時刻をくじで決める、の3つで
夜と朝の差を数え、置いた本当の効果とどれだけずれるかを見る。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 839
SRC = "架空のアカウントの投稿（作成者が乱数で作成、seed 839）"
N_POST = 360
SLOTS = ["朝7時", "昼12時", "夜20時"]
EFF = np.array([0.0, -0.05, 0.05])            # 時刻そのものの効果（対数）。夜÷朝 = exp(0.05)
TRUE_NIGHT = float(np.exp(EFF[2] - EFF[0]) - 1)
TRUE_NOON = float(np.exp(EFF[1] - EFF[0]) - 1)
BASE = {"pick": 1.5, "q_eff": 0.5, "noise": 0.7, "label_cut": 0.5, "eff_scale": 1.0}


def make_posts(rng, n=N_POST, pick=1.5, q_eff=0.5, noise=0.7, label_cut=0.5, eff_scale=1.0, random_slot=False,
               label_only=False):
    z = rng.normal(0, 1, n)                                  # 内容の出来（記録には残らない）
    label = (z > label_cut).astype(int)                      # 記録に残る「力作」の印
    drive = (label - label.mean()) * 2 if label_only else z  # 時刻の選び方が何に沿うか
    u = np.c_[np.zeros(n), np.zeros(n), pick * drive]
    p = np.exp(u) / np.exp(u).sum(1, keepdims=True)
    if random_slot:
        p = np.full((n, 3), 1 / 3)
    slot = (rng.random(n)[:, None] > p.cumsum(1)).sum(1)
    lv = np.log(3000) + eff_scale * EFF[slot] + q_eff * z + rng.normal(0, noise, n)
    return pd.DataFrame({"post_id": np.arange(1, n + 1), "slot": slot, "label": label, "quality": z,
                         "view": np.round(np.exp(lv)).astype(int)})


def naive(df, a, b=0):
    m = df.groupby("slot").view.mean()
    return float(m[a] / m[b] - 1) if a in m and b in m else np.nan


def stratified(df, a, b=0):
    """「力作」の印ごとに時刻の平均を出し、全体の印の割合で重みを付けて合わせる"""
    w = df.label.value_counts(normalize=True)
    num = den = 0.0
    for lab, wt in w.items():
        g = df[df.label == lab].groupby("slot").view.mean()
        if a not in g or b not in g:
            return np.nan
        num += wt * g[a]; den += wt * g[b]
    return float(num / den - 1)


def summarize(v, truth):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    return {"median": round(float(np.median(v)), 3), "p10": round(float(np.quantile(v, .1)), 3),
            "p90": round(float(np.quantile(v, .9)), 3), "share_ge_20pct": round(float((v >= 0.2).mean()), 3),
            "share_wrong_sign": round(float((np.sign(v) != np.sign(truth)).mean()), 3) if truth != 0 else None,
            "mean_bias": round(float(v.mean() - truth), 3)}


def run(setting, reps, seed0, random_slot=False, label_only=False, a=2):
    nv, sv = [], []
    truth = float(np.exp(setting.get("eff_scale", 1.0) * (EFF[a] - EFF[0])) - 1)
    for r in range(reps):
        g = make_posts(np.random.default_rng(seed0 + r), random_slot=random_slot, label_only=label_only, **setting)
        nv.append(naive(g, a)); sv.append(stratified(g, a))
    return summarize(nv, truth), summarize(sv, truth), nv, sv, truth


def main():
    rng = np.random.default_rng(SEED)
    df = make_posts(rng, **BASE)
    df.round(4).to_csv(DATA / "posts.csv", index=False)

    # 1) 3つの数え方（各1,000回）
    R = 1000
    n_obs, s_obs, nv_obs, sv_obs, _ = run(BASE, R, SEED * 1000)
    n_rnd, s_rnd, nv_rnd, sv_rnd, _ = run(BASE, R, SEED * 1000, random_slot=True)
    n_lab, s_lab, _, _, _ = run(BASE, R, SEED * 1000, label_only=True)
    n_noon, s_noon, _, _, _ = run(BASE, R, SEED * 1000, a=1)
    methods = pd.DataFrame([
        {"case": "出来を見て時刻を選ぶ", "method": "時刻ごとの平均をそのまま", **n_obs},
        {"case": "出来を見て時刻を選ぶ", "method": "力作の印で分けて合わせる", **s_obs},
        {"case": "力作の印だけで時刻を選ぶ", "method": "時刻ごとの平均をそのまま", **n_lab},
        {"case": "力作の印だけで時刻を選ぶ", "method": "力作の印で分けて合わせる", **s_lab},
        {"case": "時刻をくじで決める", "method": "時刻ごとの平均をそのまま", **n_rnd}])
    methods.to_csv(RES / "night_vs_morning_methods.csv", index=False)

    # 2) 確かめ：選び方の強さ・本当の効果・出来の効き方（各1,000回）
    rob = []
    variants = [("基本（選び方の強さ1.5）", {}), ("選び方の強さ 0（出来と時刻は無関係）", {"pick": 0.0}),
                ("選び方の強さ 0.75", {"pick": 0.75}), ("選び方の強さ 3", {"pick": 3.0}),
                ("時刻の効果を0にする", {"eff_scale": 0.0}), ("時刻の効果を2倍にする", {"eff_scale": 2.0}),
                ("出来の効き方 小（0.25）", {"q_eff": 0.25}), ("出来の効き方 大（1.0）", {"q_eff": 1.0}),
                ("力作の印を広く（上位5割）", {"label_cut": 0.0}), ("力作の印を狭く（上位1割）", {"label_cut": 1.28})]
    for i, (lab, ch) in enumerate(variants):
        st = {**BASE, **ch}
        nn, ss, _, _, tr = run(st, R, SEED * 1000 if i == 0 else SEED * 10 ** 6 + i * 10000)
        rob.append({"setting": lab, "true_night_vs_morning": round(tr, 3), "naive_median": nn["median"],
                    "stratified_median": ss["median"], "naive_share_ge_20pct": nn["share_ge_20pct"],
                    "stratified_share_ge_20pct": ss["share_ge_20pct"]})
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)

    # 3) くじで決めたとき、本数ごとの振れ（各1,000回）
    exp_n = []
    for n in [120, 360, 1080]:
        v = [naive(make_posts(np.random.default_rng((SEED * 1000 if n == N_POST else SEED * 10 ** 7 + n * 1000) + r), n=n, random_slot=True, **BASE), 2)
             for r in range(R)]
        sm = summarize(v, TRUE_NIGHT)
        exp_n.append({"n_post": n, **sm})
    exp_n = pd.DataFrame(exp_n); exp_n.to_csv(RES / "random_slot_by_n.csv", index=False)

    # 1回分
    m1 = df.groupby("slot").agg(n=("view", "size"), mean_view=("view", "mean"), label_share=("label", "mean"),
                                quality_mean=("quality", "mean")).round(3)
    m1.index = [SLOTS[i] for i in m1.index]
    one = {"by_slot": m1.reset_index(names="slot").to_dict("records"), "naive_night": round(naive(df, 2), 3),
           "stratified_night": round(stratified(df, 2), 3), "naive_noon": round(naive(df, 1), 3),
           "stratified_noon": round(stratified(df, 1), 3), "label_share_all": round(float(df.label.mean()), 3)}
    out = {"setting": BASE, "n_post": N_POST, "reps": R,
           "true_night_vs_morning": round(TRUE_NIGHT, 3), "true_noon_vs_morning": round(TRUE_NOON, 3),
           "night_vs_morning": methods.to_dict("records"),
           "noon_vs_morning_choose_by_quality": {"naive": n_noon, "stratified": s_noon},
           "random_slot_by_n": exp_n.to_dict("records"),
           "robust_naive_median_range": [float(rob.naive_median.min()), float(rob.naive_median.max())],
           "robust_stratified_median_range": [float(rob.stratified_median.min()), float(rob.stratified_median.max())],
           "one_draw": one}
    json.dump(out, open(RES / "a839_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の時刻ごとの平均と、力作の割合
    fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.8))
    ax[0].bar(m1.index, m1.mean_view, color=[GRAY, GRAY, ORANGE])
    for i, v in enumerate(m1.mean_view):
        ax[0].text(i, v + 50, f"{v:,.0f}", ha="center", fontsize=9)
    ax[0].set_ylabel("再生回数の平均"); ax[0].set_title("時刻ごとの再生回数の平均", fontsize=11)
    ax[1].bar(m1.index, m1.label_share * 100, color=[GRAY, GRAY, ORANGE])
    for i, v in enumerate(m1.label_share * 100):
        ax[1].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
    ax[1].set_ylabel("「力作」の印の付いた投稿の割合（%）"); ax[1].set_title("時刻ごとの「力作」の割合", fontsize=11)
    fig.suptitle(f"夜は朝より{one['naive_night']*100:.0f}%多く見えるが、夜には力作が集まっている（1年分360本）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a839_by_slot.png", SRC)

    # 図2：3つの数え方の見積もりの散らばり（1,000回）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.linspace(-0.45, 1.95, 81)
    ax.hist(np.array(nv_obs) * 100, bins=bins * 100, color=ORANGE, alpha=.55, label="時刻ごとの平均をそのまま")
    ax.hist(np.array(sv_obs) * 100, bins=bins * 100, color=BLUE, alpha=.55, label="力作の印で分けて合わせる")
    ax.hist(np.array(nv_rnd) * 100, bins=bins * 100, color=GREEN, alpha=.55, label="時刻をくじで決めて比べる")
    ax.axvline(TRUE_NIGHT * 100, color=INK, lw=1.2, ls="--")
    top = ax.get_ylim()[1]; ax.set_ylim(0, top * 1.18)
    ax.text(TRUE_NIGHT * 100 + 2, top * 1.1, f"置いた本当の効果 +{TRUE_NIGHT*100:.1f}%", fontsize=9)
    ax.set_xlabel("夜20時が朝7時より何%多いか（見積もり）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("そのままの比べ方は大きく外れ、印で分けても残りのずれがある")
    save(fig, "a839_estimates.png", SRC)

    # 図3：選び方の強さを変えると
    r3 = rob[rob.setting.str.startswith("選び方") | rob.setting.str.startswith("基本")].copy()
    r3["pick"] = [1.5, 0.0, 0.75, 3.0]
    r3 = r3.sort_values("pick")
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(r3.pick, r3.naive_median * 100, color=ORANGE, marker="o", label="時刻ごとの平均をそのまま")
    ax.plot(r3.pick, r3.stratified_median * 100, color=BLUE, marker="o", label="力作の印で分けて合わせる")
    ax.axhline(TRUE_NIGHT * 100, color=INK, lw=1, ls="--", label=f"置いた本当の効果（+{TRUE_NIGHT*100:.1f}%）")
    ax.set_xticks(r3.pick); ax.set_xlabel("出来の良い投稿を夜に出す度合い（0は無関係）")
    ax.set_ylabel("夜が朝より何%多いか（1,000回の中央値）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("出来で時刻を選ぶ度合いが強いほど、時刻の効果は大きく見える")
    save(fig, "a839_by_pick.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
