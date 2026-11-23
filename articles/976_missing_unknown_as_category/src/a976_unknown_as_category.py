"""976 「不明」を1つの分類にすると、比べ方はどう変わるのか？（架空のデータ）

架空の2店（A店・B店）の新しい客の「来店のきっかけ」（5つの分類）と、3か月以内の再来店。
作成者が本当のきっかけを置き、記録で「不明」になる客を混ぜる。
基本の置き方：本当のきっかけの割合も、きっかけごとの再来店率も2店で同じ（本当の差は0）。
違うのは記録の仕方だけ：不明の割合は A店10%・B店30%。
不明になりやすさはきっかけで違う（通りがかりは不明になりやすく、紹介はなりにくい）。
2つの読み方を比べる：
  (i) 不明を1つの分類として残し、不明も入れた全体で割る
  (ii) 不明を除き、きっかけの分かった客だけで割る
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 976
SRC = "架空の2店の新しい客の来店のきっかけ（作成者が乱数で作成、seed 976）"
CH = ["通りがかり", "ネット検索", "SNS", "紹介", "チラシ"]
SHARE = np.array([0.35, 0.25, 0.15, 0.15, 0.10])
REPEAT = np.array([0.20, 0.25, 0.30, 0.45, 0.15])
DEP = {"なし": np.array([1.0, 1, 1, 1, 1]), "弱い": np.array([1.7, 1, 1, 0.6, 1]),
       "強い": np.array([3.0, 1, 1, 0.3, 1])}
N = 2000
REPS = 200
BASE = dict(unk_a=0.10, unk_b=0.30, dep="強い", diff=0.0)
REF = 3  # 紹介


def expit(x):
    return 1 / (1 + np.exp(-x))


def unknown_probs(share, target, mult):
    """きっかけごとの不明になる確率（オッズ比 mult、全体の不明の割合が target になるよう合わせる）"""
    lo, hi = -20.0, 20.0
    for _ in range(100):
        mid = (lo + hi) / 2
        q = expit(mid + np.log(mult))
        if (share * q).sum() > target:
            hi = mid
        else:
            lo = mid
    return expit((lo + hi) / 2 + np.log(mult))


def shares_b(diff):
    s = SHARE.copy()
    s[REF] += diff
    s[0] -= diff  # 紹介が増えた分だけ通りがかりが減る
    return s


def one_store(rng, share, unk_rate, mult, n=N):
    ch = rng.choice(len(CH), size=n, p=share)
    rep = rng.random(n) < REPEAT[ch]
    q = unknown_probs(share, unk_rate, mult)
    unk = rng.random(n) < q[ch]
    return ch, rep, unk


def readings(ch, unk):
    cnt = np.bincount(ch[~unk], minlength=len(CH))
    incl = cnt / len(ch)                # (i) 不明も入れて割る
    excl = cnt / max(cnt.sum(), 1)      # (ii) 分かった客だけで割る
    return incl, excl, unk.mean()


def run(rng, unk_a, unk_b, dep, diff):
    m = DEP[dep]
    sa, sb = SHARE, shares_b(diff)
    ca, ra, ua = one_store(rng, sa, unk_a, m)
    cb, rb, ub = one_store(rng, sb, unk_b, m)
    ia, ea, _ = readings(ca, ua)
    ib, eb, _ = readings(cb, ub)
    true_a = np.bincount(ca, minlength=5) / N
    true_b = np.bincount(cb, minlength=5) / N
    rep_unk = (ra[ua].mean(), rb[ub].mean())
    rep_known = [(ra[(~ua) & (ca == k)].mean(), rb[(~ub) & (cb == k)].mean()) for k in range(5)]
    return dict(ia=ia, ib=ib, ea=ea, eb=eb, ta=true_a, tb=true_b, unk_a=ua.mean(), unk_b=ub.mean(),
                rep_unk=rep_unk, rep_known=rep_known, rep_all=(ra.mean(), rb.mean()))


def main():
    t0 = time.time()
    res = {"setting": {"channels": CH, "true_share": SHARE.tolist(), "true_repeat": REPEAT.tolist(),
                       "odds_mult_unknown": {k: v.tolist() for k, v in DEP.items()}, "N_per_store": N, "REPS": REPS,
                       "base": BASE}}

    # 例の1回分（基本の置き方）
    rng = np.random.default_rng(SEED)
    rows = []
    for st, ur in [("A", BASE["unk_a"]), ("B", BASE["unk_b"])]:
        c, r, u = one_store(rng, SHARE, ur, DEP[BASE["dep"]])
        rows.append(pd.DataFrame({"store": st, "customer_id": np.arange(1, N + 1),
                                  "channel_true": np.array(CH)[c],
                                  "channel_recorded": np.where(u, "不明", np.array(CH)[c]),
                                  "repeat_3m": r.astype(int)}))
    ex = pd.concat(rows, ignore_index=True)
    ex.to_csv(DATA / "customers_example.csv", index=False)
    tab = pd.crosstab(ex.channel_recorded, ex.store).reindex(CH + ["不明"])
    res["example_counts"] = {k: {s: int(tab.loc[k, s]) for s in ["A", "B"]} for k in tab.index}

    # 1) 基本の置き方（200回）
    out = [run(np.random.default_rng(SEED * 100 + r), **BASE) for r in range(REPS)]
    mean = lambda key: np.mean([o[key] for o in out], 0)
    ia, ib, ea, eb, ta, tb = (mean(k) for k in ["ia", "ib", "ea", "eb", "ta", "tb"])
    dif_i = np.array([o["ib"] - o["ia"] for o in out])
    dif_e = np.array([o["eb"] - o["ea"] for o in out])
    share_tab = pd.DataFrame({"channel": CH, "true": SHARE * 100,
                              "A_incl": ia * 100, "B_incl": ib * 100, "diff_incl_pt": (ib - ia) * 100,
                              "A_excl": ea * 100, "B_excl": eb * 100, "diff_excl_pt": (eb - ea) * 100,
                              "diff_excl_p10": np.quantile(dif_e, .1, 0) * 100,
                              "diff_excl_p90": np.quantile(dif_e, .9, 0) * 100}).round(2)
    share_tab.to_csv(RES / "shares_base.csv", index=False)
    res["base_shares"] = share_tab.to_dict("records")
    res["base_unknown_rate"] = {"A": round(float(mean("unk_a")) * 100, 2), "B": round(float(mean("unk_b")) * 100, 2)}
    res["base_ref_diff"] = {"incl_pt": round(float(dif_i[:, REF].mean() * 100), 2),
                            "excl_pt": round(float(dif_e[:, REF].mean() * 100), 2),
                            "excl_share_runs_gt_0": round(float((dif_e[:, REF] > 0).mean() * 100), 1),
                            "excl_share_runs_gt_1pt": round(float((dif_e[:, REF] > 0.01).mean() * 100), 1),
                            "incl_share_runs_lt_0": round(float((dif_i[:, REF] < 0).mean() * 100), 1)}

    # 不明の客の再来店率（数えた値と式の値）
    m = DEP[BASE["dep"]]
    f_unk = {}
    for st, ur in [("A", BASE["unk_a"]), ("B", BASE["unk_b"])]:
        q = unknown_probs(SHARE, ur, m)
        w = SHARE * q
        f_unk[st] = float((w * REPEAT).sum() / w.sum())
        known = SHARE * (1 - q)
        f_unk[st + "_known_all"] = float((known * REPEAT).sum() / known.sum())
    ru = mean("rep_unk")
    rk = np.mean([o["rep_known"] for o in out], 0)
    rall = mean("rep_all")
    rep_tab = pd.DataFrame({"channel": CH + ["不明"],
                            "A": np.r_[rk[:, 0], ru[0]] * 100, "B": np.r_[rk[:, 1], ru[1]] * 100,
                            "true": np.r_[REPEAT, np.nan] * 100}).round(2)
    rep_tab.to_csv(RES / "repeat_by_channel.csv", index=False)
    res["repeat"] = {"table": rep_tab.to_dict("records"),
                     "unknown_formula": {"A": round(f_unk["A"] * 100, 2), "B": round(f_unk["B"] * 100, 2)},
                     "known_only_formula": {"A": round(f_unk["A_known_all"] * 100, 2), "B": round(f_unk["B_known_all"] * 100, 2)},
                     "overall": {"A": round(float(rall[0]) * 100, 2), "B": round(float(rall[1]) * 100, 2)},
                     "true_overall": round(float((SHARE * REPEAT).sum()) * 100, 2)}

    # 2) 確かめ：B店の不明の割合 × 不明のなりやすさの偏り × 本当の差（各100回）
    grid = []
    gi = 0
    for diff in [0.0, 0.05]:
        for dep in DEP:
            for ub in [0.10, 0.20, 0.30, 0.40]:
                gi += 1
                oo = [run(np.random.default_rng(SEED * 7 + gi * 1000 + r), BASE["unk_a"], ub, dep, diff) for r in range(100)]
                di = np.mean([o["ib"] - o["ia"] for o in oo], 0)
                de = np.mean([o["eb"] - o["ea"] for o in oo], 0)
                grid.append({"true_diff_pt": diff * 100, "dep": dep, "unk_b": ub * 100,
                             "ref_incl_pt": round(float(di[REF]) * 100, 2), "ref_excl_pt": round(float(de[REF]) * 100, 2),
                             "walk_incl_pt": round(float(di[0]) * 100, 2), "walk_excl_pt": round(float(de[0]) * 100, 2),
                             "maxabs_err_incl_pt": round(float(np.abs(di - (shares_b(diff) - SHARE)).max()) * 100, 2),
                             "maxabs_err_excl_pt": round(float(np.abs(de - (shares_b(diff) - SHARE)).max()) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    g0 = grid[grid.true_diff_pt == 0]
    g5 = grid[grid.true_diff_pt == 5]
    res["robust"] = {
        "n_cases": int(len(grid)),
        "dep_none_excl_maxabs_err": float(g0[g0.dep == "なし"].maxabs_err_excl_pt.max()),
        "dep_none_incl_ref_range": [float(g0[g0.dep == "なし"].ref_incl_pt.min()), float(g0[g0.dep == "なし"].ref_incl_pt.max())],
        "diff0_dep_pos_excl_ref_range": [float(g0[g0.dep != "なし"].ref_excl_pt.min()), float(g0[g0.dep != "なし"].ref_excl_pt.max())],
        "diff0_dep_pos_incl_ref_range": [float(g0[g0.dep != "なし"].ref_incl_pt.min()), float(g0[g0.dep != "なし"].ref_incl_pt.max())],
        "diff0_dep_pos_unkb_gt10_excl_ref_range": [float(g0[(g0.dep != "なし") & (g0.unk_b > 10)].ref_excl_pt.min()),
                                                   float(g0[(g0.dep != "なし") & (g0.unk_b > 10)].ref_excl_pt.max())],
        "diff0_dep_pos_unkb_gt10_excl_maxabs_err_range": [float(g0[(g0.dep != "なし") & (g0.unk_b > 10)].maxabs_err_excl_pt.min()),
                                                          float(g0[(g0.dep != "なし") & (g0.unk_b > 10)].maxabs_err_excl_pt.max())],
        "diff0_unkb_gt10_incl_maxabs_err_range": [float(g0[g0.unk_b > 10].maxabs_err_incl_pt.min()),
                                                  float(g0[g0.unk_b > 10].maxabs_err_incl_pt.max())],
        "n_diff0_unkb_gt10": int((g0.unk_b > 10).sum()),
        "n_diff0_dep_pos_unkb_gt10": int(((g0.dep != "なし") & (g0.unk_b > 10)).sum()),
        "dep_none_excl_maxabs_err_all": float(grid[grid.dep == "なし"].maxabs_err_excl_pt.max()),
        "diff0_unkb10_strong": g0[(g0.dep == "強い") & (g0.unk_b == 10)][["ref_incl_pt", "ref_excl_pt"]].iloc[0].to_dict(),
        "diff5_incl_ref_range": [float(g5.ref_incl_pt.min()), float(g5.ref_incl_pt.max())],
        "diff5_excl_ref_range": [float(g5.ref_excl_pt.min()), float(g5.ref_excl_pt.max())],
        "diff5_strong_unkb40": g5[(g5.dep == "強い") & (g5.unk_b == 40)][["ref_incl_pt", "ref_excl_pt"]].iloc[0].to_dict(),
        "diff5_none_unkb40": g5[(g5.dep == "なし") & (g5.unk_b == 40)][["ref_incl_pt", "ref_excl_pt"]].iloc[0].to_dict(),
    }
    with open(RES / "a976_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：B店−A店の割合の差（本当の差は0）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(5)
    ax.bar(x - .2, share_tab.diff_incl_pt, width=.38, color=GRAY, label="(i) 不明を1つの分類にして、全体で割る")
    ax.bar(x + .2, share_tab.diff_excl_pt, width=.38, color=BLUE, label="(ii) 不明を除き、分かった客だけで割る")
    for i in range(5):
        ax.text(x[i] - .2, share_tab.diff_incl_pt[i] - .35, f"{share_tab.diff_incl_pt[i]:+.1f}", ha="center", va="top", fontsize=8.5)
        v = share_tab.diff_excl_pt[i]
        ax.text(x[i] + .2, v + (.25 if v >= 0 else -.35), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(x); ax.set_xticklabels(CH)
    ax.set_ylabel("B店 − A店（ポイント）"); ax.set_ylim(-12.5, 5)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("本当のきっかけの割合は2店で同じでも、不明の多いB店は違って見える\n（不明 A店10%・B店30%、通りがかりほど不明になりやすい）", fontsize=11.5)
    save(fig, "a976_share_diff.png", SRC + "。200回の平均")

    # 図2：きっかけごとの再来店率（不明も1つの分類として並べる）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(6)
    ax.bar(x - .2, rep_tab.A, width=.38, color=LIGHT, label="A店（不明10%）")
    ax.bar(x + .2, rep_tab.B, width=.38, color=BLUE, label="B店（不明30%）")
    for i in range(6):
        ax.text(x[i] - .2, rep_tab.A[i] + .6, f"{rep_tab.A[i]:.1f}", ha="center", fontsize=8)
        ax.text(x[i] + .2, rep_tab.B[i] + .6, f"{rep_tab.B[i]:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(CH + ["不明"])
    ax.get_xticklabels()[5].set_color(ORANGE)
    ax.set_ylabel("3か月以内の再来店率（%）"); ax.set_ylim(0, 52)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("「不明」の客の再来店率は、不明になった客の混ざり方で決まる", fontsize=12)
    save(fig, "a976_repeat.png", SRC + "。200回の平均。きっかけごとの本当の再来店率は2店で同じ")

    # 図3：確かめ（紹介の割合の B−A、本当の差0と+5）
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.9), sharey=True)
    cols = {"なし": GRAY, "弱い": GREEN, "強い": ORANGE}
    for ax, d in zip(axes, [0, 5]):
        g = grid[grid.true_diff_pt == d]
        for dep in DEP:
            h = g[g.dep == dep]
            ax.plot(h.unk_b, h.ref_excl_pt, "o-", color=cols[dep], lw=1.2, ms=5, label=f"(ii) 除く・偏り{dep}")
            ax.plot(h.unk_b, h.ref_incl_pt, "s--", color=cols[dep], lw=1, ms=4, alpha=.8, label=f"(i) 分類に入れる・偏り{dep}")
        ax.axhline(d, color=INK, lw=1, ls=":")
        ax.set_xticks([10, 20, 30, 40]); ax.set_xlabel("B店の不明の割合（%、A店は10%）")
        ax.set_title(f"本当の差 {d:+d}ポイント（点線）", fontsize=11)
    axes[0].set_ylabel("「紹介」の割合の B店−A店（ポイント）")
    axes[1].legend(frameon=False, fontsize=7.5, loc="lower left", ncol=1)
    fig.suptitle("不明を除くと、不明が偏るときだけずれる。分類に入れると、不明の多い店ほど低く出る（各100回）", fontsize=11, y=1.02)
    save(fig, "a976_robustness.png", SRC + "。偏りは不明になりやすさのオッズ比（通りがかり×1.7／×3、紹介×0.6／×0.3）", y=-0.03)

    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
