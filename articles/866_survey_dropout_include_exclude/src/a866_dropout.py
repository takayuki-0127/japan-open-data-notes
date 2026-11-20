"""866 途中でやめた人の回答を入れるか除くかで、結果は変わるのか？（架空のデータ）

架空の家具店の購入者アンケート（12問、1〜5の5段階）。回答を始めた客800人。
客ごとに「本当の満足の高さ」z（標準正規）を置き、問 q の答えは round(μ_q + 0.8z + 0.6e) を1〜5で切ったもの。
正解は「始めた客全員が最後まで答えたときの平均」（作成者だけが知る値）。
問 q に答えたあと、確率 1/(1+exp(−(a − b·z))) でやめる（満足が低い客ほどやめやすい。b=0.8 が基本）。
数え方は3つ：
  入れる：答えた分はすべて使う（問ごとに、そこまで答えた客の平均）
  除く：最後まで答えた客だけ
  除く＋問1で重み：最後まで答えた客を、問1の答えの分布が始めた客全員と同じになるように重み付け
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 866
SRC = "架空の家具店の購入者アンケート（作成者が乱数で作成、seed 866）"
N, REPS, REPS_R = 800, 2000, 500
QS = ["店全体の満足", "品ぞろえ", "店員の説明", "店内の見やすさ", "注文のしやすさ", "配送の日時",
      "組み立ての説明書", "梱包", "届いた品の状態", "問い合わせの対応", "サイトの使いやすさ", "また来たいか"]
MU = np.array([3.6, 3.4, 3.8, 3.5, 3.4, 3.3, 3.1, 3.6, 3.9, 3.2, 3.3, 3.5])
LOAD, NOISE, B = 0.8, 0.6, 0.8
METHODS = ["入れる", "除く", "除く＋問1で重み"]


def a_for(b, target_complete, rng):
    """最後まで答える割合が target_complete になる a を二分法で（大きめの標本で）"""
    z = rng.standard_normal(200000)
    lo, hi = -10.0, 5.0
    for _ in range(50):
        a = (lo + hi) / 2
        h = 1 / (1 + np.exp(-(a - b * z)))
        comp = ((1 - h) ** 11).mean()
        if comp > target_complete:
            lo = a
        else:
            hi = a
    return (lo + hi) / 2


def survey(rng, n, a, b):
    z = rng.standard_normal(n)
    y = np.clip(np.rint(MU + LOAD * z[:, None] + NOISE * rng.standard_normal((n, 12))), 1, 5)
    h = 1 / (1 + np.exp(-(a - b * z)))
    # 何問目まで答えたか（1〜12）。問1は全員答える
    stop = rng.random((n, 11)) < h[:, None]
    last = np.where(stop.any(1), stop.argmax(1) + 1, 12)
    answered = np.arange(1, 13)[None, :] <= last[:, None]
    return z, y, last, answered


def estimates(y, last, answered):
    truth = y.mean(0)
    inc = np.nanmean(np.where(answered, y, np.nan), 0)
    comp = last == 12
    exc = y[comp].mean(0)
    # 問1の答えで重み付け
    w = np.zeros(len(y))
    for v in range(1, 6):
        all_share = (y[:, 0] == v).mean()
        cc = comp & (y[:, 0] == v)
        if cc.sum() > 0:
            w[cc] = all_share / cc.sum()
    w = w / w.sum()
    wtd = (w[:, None] * y).sum(0)
    return truth, {"入れる": inc, "除く": exc, "除く＋問1で重み": wtd}, comp.mean()


def run(rng, reps, a, b, n=N):
    T, E, C, NA = [], {m: [] for m in METHODS}, [], []
    for _ in range(reps):
        z, y, last, answered = survey(rng, n, a, b)
        t, e, c = estimates(y, last, answered)
        T.append(t); C.append(c); NA.append(answered.sum(0))
        for m in METHODS:
            E[m].append(e[m])
    return np.array(T), {m: np.array(v) for m, v in E.items()}, np.array(C), np.array(NA)


def r3(x):
    return round(float(x), 3)


def main():
    rng = np.random.default_rng(SEED)
    a0 = a_for(B, 0.65, np.random.default_rng(SEED + 1))

    # 1回分（data）
    z, y, last, answered = survey(rng, N, a0, B)
    d = pd.DataFrame({"id": np.arange(1, N + 1), "last_answered": last})
    for q in range(12):
        d[f"q{q+1}"] = np.where(answered[:, q], y[:, q], np.nan)
    for q in range(12):
        d[f"full_q{q+1}"] = y[:, q].astype(int)
    d["z"] = [f"{v:.4f}" for v in z]          # 本当の満足の高さ（作成者だけが知る値）。文字で書いて桁を固定
    d.to_csv(DATA / "respondents.csv", index=False, float_format="%.0f")
    pd.DataFrame({"q": np.arange(1, 13), "question": QS, "mu": MU}).to_csv(DATA / "questions.csv", index=False)
    t1, e1, c1 = estimates(y, last, answered)

    # 2,000回
    T, E, C, NA = run(rng, REPS, a0, B)
    tab = pd.DataFrame({"q": np.arange(1, 13), "question": QS, "truth": T.mean(0),
                        "answered_share": NA.mean(0) / N})
    for m in METHODS:
        tab[m] = E[m].mean(0)
        tab[f"bias_{m}"] = (E[m] - T).mean(0)
    tab.round(4).to_csv(RES / "by_question.csv", index=False)

    # 問12−問1 の差（入れる では土台の人が違う）
    diff_true = (T[:, 11] - T[:, 0]).mean()
    diff = {m: r3((E[m][:, 11] - E[m][:, 0]).mean()) for m in METHODS}

    # やめた位置ごとの客の本当の満足（1回分＋全体）
    zpos = []
    for _ in range(200):
        zz, yy, ll, aa = survey(rng, N, a0, B)
        zpos.append([zz[ll == k].mean() if (ll == k).any() else np.nan for k in range(1, 13)])
    zpos = np.nanmean(np.array(zpos), 0)

    out = {"n_started": N, "reps": REPS, "a": r3(a0), "b": B, "complete_share": r3(C.mean()),
           "answered_share_q12": r3(NA.mean(0)[11] / N), "answered_share_q6": r3(NA.mean(0)[5] / N),
           "bias_mean_over_q": {m: r3((E[m] - T).mean()) for m in METHODS},
           "bias_q1": {m: r3((E[m] - T)[:, 0].mean()) for m in METHODS},
           "bias_q12": {m: r3((E[m] - T)[:, 11].mean()) for m in METHODS},
           "abs_bias_max_over_q": {m: r3(np.abs((E[m] - T).mean(0)).max()) for m in METHODS},
           "diff_q12_minus_q1": {"正解": r3(diff_true), **diff},
           "z_by_last_answered": [r3(v) for v in zpos],
           "one_survey": {"complete_share": r3(c1), "truth_q1": r3(t1[0]), "truth_q12": r3(t1[11]),
                          **{f"{m}_q1": r3(e1[m][0]) for m in METHODS}, **{f"{m}_q12": r3(e1[m][11]) for m in METHODS}}}

    # 確かめ：やめやすさと満足の結びつき b × 最後まで答える割合
    rows = []
    for b in [0.0, 0.4, 0.8, 1.2]:
        for comp in [0.85, 0.65, 0.45]:
            g = np.random.default_rng(SEED * 100 + int(b * 10) * 3 + int(comp * 100))
            aa = a_for(b, comp, np.random.default_rng(SEED + 2 + int(b * 10)))
            Tt, Ee, Cc, _ = run(g, REPS_R, aa, b)
            rows.append({"b": b, "complete_target": comp, "complete_share": r3(Cc.mean()),
                         **{f"bias_mean_{m}": r3((Ee[m] - Tt).mean()) for m in METHODS},
                         **{f"bias_q12_{m}": r3((Ee[m] - Tt)[:, 11].mean()) for m in METHODS},
                         "diff_true": r3((Tt[:, 11] - Tt[:, 0]).mean()),
                         "diff_入れる": r3((Ee["入れる"][:, 11] - Ee["入れる"][:, 0]).mean())})
    rob = pd.DataFrame(rows); rob.to_csv(RES / "robustness.csv", index=False)
    nz = rob[rob.b > 0]
    out["robust"] = {"b0_abs_bias_max": r3(rob[rob.b == 0][[f"bias_mean_{m}" for m in METHODS]].abs().max().max()),
                     "bias_mean_除く_range": [float(nz["bias_mean_除く"].min()), float(nz["bias_mean_除く"].max())],
                     "bias_mean_重み_range": [float(nz["bias_mean_除く＋問1で重み"].min()),
                                            float(nz["bias_mean_除く＋問1で重み"].max())],
                     "bias_q12_入れる_range": [float(nz["bias_q12_入れる"].min()), float(nz["bias_q12_入れる"].max())],
                     "diff_入れる_range": [float(nz["diff_入れる"].min()), float(nz["diff_入れる"].max())],
                     "diff_true_range": [float(rob["diff_true"].min()), float(rob["diff_true"].max())],
                     "diff_入れる_positive_count": int((nz["diff_入れる"] > 0.005).sum()), "combos_b_pos": int(len(nz)),
                     "weight_share_of_bias_removed": [r3(1 - (nz["bias_mean_除く＋問1で重み"] / nz["bias_mean_除く"]).max()),
                                                      r3(1 - (nz["bias_mean_除く＋問1で重み"] / nz["bias_mean_除く"]).min())]}
    json.dump(out, open(RES / "a866_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：問ごとのずれ
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(1, 13)
    for m, c, mk in [("入れる", ORANGE, "o"), ("除く", BLUE, "s"), ("除く＋問1で重み", GREEN, "^")]:
        ax.plot(x, tab[f"bias_{m}"], color=c, marker=mk, label=m)
    ax.axhline(0, color=INK, lw=1)
    ax.set_xticks(x); ax.set_xticklabels([f"問{i}" for i in x], fontsize=9)
    ax.set_ylabel("平均の正解からのずれ（点、2,000回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(0.02, 0.62))
    ax.set_title("「入れる」は後の問ほど上にずれ、「除く」はどの問も上にずれる")
    save(fig, "a866_bias_by_question.png", SRC)

    # 図2：残っている人の割合と、やめた位置ごとの本当の満足
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.8))
    axs[0].bar(x, tab.answered_share * 100, color=LIGHT)
    for i, v in zip(x, tab.answered_share * 100):
        if i in (1, 6, 12):
            axs[0].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8.5)
    axs[0].set_xticks(x); axs[0].set_xticklabels([str(i) for i in x], fontsize=8)
    axs[0].set_xlabel("問"); axs[0].set_ylabel("答えた客の割合（%）"); axs[0].set_ylim(0, 110)
    axs[1].bar(x, zpos, color=[BLUE if i < 12 else GRAY for i in x])
    axs[1].axhline(0, color=INK, lw=0.8)
    axs[1].set_xticks(x); axs[1].set_xticklabels([str(i) for i in x], fontsize=8)
    axs[1].set_xlabel("最後に答えた問（12は最後まで答えた客）"); axs[1].set_ylabel("本当の満足の高さ（平均0）")
    fig.suptitle("途中でやめた客ほど、本当の満足が低い（作成者がそう置いた）", fontsize=12)
    save(fig, "a866_who_dropped.png", SRC)

    # 図3：確かめ（満足とやめやすさの結びつき × 最後まで答える割合）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    bs = sorted(rob.b.unique())
    for comp, c in [(0.85, LIGHT), (0.65, BLUE), (0.45, INK)]:
        sub = rob[rob.complete_target == comp].sort_values("b")
        ax.plot(sub.b, sub["bias_mean_除く"], color=c, marker="s", label=f"除く（最後まで{int(comp*100)}%）")
        ax.plot(sub.b, sub["bias_mean_除く＋問1で重み"], color=c, marker="^", ls="--",
                label=f"除く＋問1で重み（最後まで{int(comp*100)}%）")
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xticks(bs); ax.set_xticklabels(["0\n（結びつきなし）", "0.4", "0.8\n（基本）", "1.2"])
    ax.set_xlabel("満足の低さとやめやすさの結びつき（作成者が置いた強さ）")
    ax.set_ylabel("12問の平均のずれ（点、各500回）"); ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("結びつきがなければずれない。強いほど、やめる客が多いほど大きい", fontsize=12)
    save(fig, "a866_robustness.png", SRC, y=-0.08)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
