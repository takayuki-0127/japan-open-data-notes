"""1091 ときどき落ちるテストを再実行で通すと、本当の不具合を何%見逃すのか？（架空のデータ）

架空のアプリの自動テスト（1,500本）を置く。うち60本は、バグがなくてもときどき落ちるテスト（落ちる確率を作成者が置く）。
本当のバグは、1本のテストを落とす。いつも落とすバグ（7割）と、ときどき落とすバグ（3割、落とす確率を作成者が置く）がある。
落ちたテストを最大 k 回（0〜3回）再実行し、1回でも通れば「通った」とする決まりで、
・本当のバグがあるのに通ってしまう割合（1回のビルド、リリースまでの10回のビルド）
・バグがないのに赤くなるビルドの割合
・「再実行で通った」記録を数えると、ときどき落とすバグに気づけるか
を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1091
SRC = "架空のアプリの自動テストとバグ（作成者が置いた数と確率からの乱数、seed 1091）"
BASE = {"n_tests": 1500, "n_flaky": 60, "flaky_beta": (1.0, 19.0), "share_intermittent": 0.3, "bug_beta": (2.0, 3.0),
        "builds": 10, "flag_min": 2}
KS = [0, 1, 2, 3]
N_BUGS = 20000
N_BUILDS_CLEAN = 4000
GRID_BUGS = 6000
GRID_BUILDS = 1500


def r(x, d=4):
    return round(float(x), d)


def bug_sim(rng, p, k, n_bugs):
    inter = rng.random(n_bugs) < p["share_intermittent"]
    rr = np.where(inter, rng.beta(*p["bug_beta"], n_bugs), 1.0)
    B = p["builds"]
    first = rng.random((n_bugs, B)) < rr[:, None]
    if k > 0:
        rer = rng.random((k, n_bugs, B)) < rr[None, :, None]
        allf = rer.all(0)
    else:
        allf = np.ones((n_bugs, B), bool)
    red = first & allf
    pr = first & ~allf
    det_build = np.where(red.any(1), red.argmax(1) + 1, 0)  # 何回目のビルドで赤くなったか（0＝10回で一度も）
    # 赤くなるまでの「再実行で通った」回数（赤くなったビルドより前、または10回まで）
    upto = np.where(det_build > 0, det_build - 1, B)
    mask = np.arange(B)[None, :] < upto[:, None]
    pr_before = (pr & mask).sum(1)
    flagged = pr_before >= p["flag_min"]
    return pd.DataFrame({"intermittent": inter, "fail_prob": rr, "first_build_red": red[:, 0], "first_build_first_fail": first[:, 0],
                         "detected_build": det_build, "pass_on_rerun_before": pr_before, "flagged_by_record": flagged})


def clean_sim(rng, p, k, n_builds):
    """バグのないビルド：ときどき落ちるテストだけが落ちる。10回のビルドごとにテストの組（落ちる確率）を作り直す。
    赤いビルドの割合と、10回のうち「再実行で通った」が2回以上のテストの数"""
    B = p["builds"]
    nb = n_builds // B
    f = rng.beta(*p["flaky_beta"], (nb, 1, p["n_flaky"]))
    first = rng.random((nb, B, p["n_flaky"])) < f
    if k > 0:
        allf = (rng.random((k, nb, B, p["n_flaky"])) < f[None]).all(0)
    else:
        allf = np.ones_like(first)
    red = first & allf
    pr = first & ~allf
    return {"red_build_share": red.any(2).mean(), "red_tests_per_build": red.sum(2).mean(),
            "flaky_flagged_per_10": (pr.sum(1) >= p["flag_min"]).sum(1).mean(), "first_fail_share": first.any(2).mean()}


def formulas(p, k):
    a, b = p["bug_beta"]
    def ebeta_pow(n):  # E[r^n]
        v = 1.0
        for i in range(n):
            v *= (a + i) / (a + b + i)
        return v
    s = p["share_intermittent"]
    e1, ek1 = ebeta_pow(1), ebeta_pow(k + 1)
    miss_build_inter = 1 - ek1
    rerun_hides = 1 - ek1 / e1  # 1回目に落ちたうち、再実行で通る割合
    return {"miss_build_intermittent": miss_build_inter, "miss_build_all": s * miss_build_inter,
            "rerun_hides_among_first_fail": rerun_hides}


def summarize(df, cl, p, k):
    it = df[df.intermittent]
    first_fail = it[it.first_build_first_fail]
    return {"k": k,
            "miss_build_all": r(1 - df.first_build_red.mean()), "miss_build_intermittent": r(1 - it.first_build_red.mean()),
            "rerun_hides_among_first_fail": r(1 - first_fail.first_build_red.mean()),
            "miss_10builds_all": r((df.detected_build == 0).mean()), "miss_10builds_intermittent": r((it.detected_build == 0).mean()),
            "mean_build_detected_intermittent": r(it[it.detected_build > 0].detected_build.mean()),
            "flagged_intermittent_missed10": r(it[it.detected_build == 0].flagged_by_record.mean()) if (it.detected_build == 0).any() else None,
            "flagged_or_red_intermittent": r((it.flagged_by_record | (it.detected_build > 0)).mean()),
            "red_build_share_clean": r(cl["red_build_share"]), "red_tests_per_build_clean": r(cl["red_tests_per_build"]),
            "flaky_flagged_per_10": r(cl["flaky_flagged_per_10"]), **{f"{kk}_formula": r(v) for kk, v in formulas(p, k).items()}}


def main():
    t0 = time.time()
    p = dict(BASE)
    rows, one = [], None
    for k in KS:
        rng = np.random.default_rng(SEED * 10 + k)
        df = bug_sim(rng, p, k, N_BUGS)
        cl = clean_sim(rng, p, k, N_BUILDS_CLEAN)
        rows.append(summarize(df, cl, p, k))
        if k == 1:
            one = df
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "by_reruns.csv", index=False)

    # 落とす確率ごと（k=1、ときどき落とすバグ）：10回のビルドで見逃す割合
    it = one[one.intermittent].copy()
    it["band"] = pd.cut(it.fail_prob, [0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["0〜0.2", "0.2〜0.4", "0.4〜0.6", "0.6〜0.8", "0.8〜1"])
    band = it.groupby("band", observed=False).agg(n=("fail_prob", "size"), miss_build=("first_build_red", lambda x: 1 - x.mean()),
                                                   miss_10builds=("detected_build", lambda x: (x == 0).mean()),
                                                   flagged_or_red=("flagged_by_record", "mean")).reset_index()
    band["flagged_or_red"] = it.assign(fr=(it.flagged_by_record | (it.detected_build > 0))).groupby("band", observed=False).fr.mean().values
    band["not_flagged_not_red"] = 1 - band["flagged_or_red"]
    band = band.round(4)
    band.to_csv(RES / "by_fail_prob_k1.csv", index=False)

    # 確かめ：ときどき落とすバグの割合×落とす確率×ときどき落ちるテストの本数（27通り）
    grid, gi = [], 0
    for si in [0.1, 0.3, 0.5]:
        for bb, bm in [((1.0, 4.0), 0.2), ((2.0, 3.0), 0.4), ((3.0, 2.0), 0.6)]:
            for nf in [20, 60, 150]:
                pp = dict(BASE, share_intermittent=si, bug_beta=bb, n_flaky=nf)
                row = {"share_intermittent": si, "bug_fail_mean": bm, "n_flaky": nf}
                for k in [0, 1, 2]:
                    rng = np.random.default_rng(SEED * 100000 + gi * 10 + k)
                    s = summarize(bug_sim(rng, pp, k, GRID_BUGS), clean_sim(rng, pp, k, GRID_BUILDS), pp, k)
                    row[f"k{k}_miss_build_all"] = s["miss_build_all"]
                    row[f"k{k}_miss_10builds_all"] = s["miss_10builds_all"]
                    row[f"k{k}_red_build_clean"] = s["red_build_share_clean"]
                    row[f"k{k}_flaky_flagged_per_10"] = s["flaky_flagged_per_10"]
                    row[f"k{k}_flagged_or_red_intermittent"] = s["flagged_or_red_intermittent"]
                grid.append(row); gi += 1
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid27.csv", index=False)

    data = one.head(2000).copy()
    data.insert(0, "bug", [f"B{i:04d}" for i in range(len(data))])
    data["fail_prob"] = data.fail_prob.round(4)
    data = data.astype({"intermittent": int, "first_build_red": int, "first_build_first_fail": int, "flagged_by_record": int})
    data.to_csv(DATA / "bugs_k1_first2000.csv", index=False)

    t = tab.set_index("k")
    out = {"settings": {**{k: (list(v) if isinstance(v, tuple) else v) for k, v in BASE.items()}, "reruns": KS, "n_bugs": N_BUGS,
                        "n_builds_clean": N_BUILDS_CLEAN, "grid_bugs": GRID_BUGS, "grid_builds": GRID_BUILDS, "seed": SEED,
                        "flaky_fail_mean": r(BASE["flaky_beta"][0] / sum(BASE["flaky_beta"])), "bug_fail_mean": r(BASE["bug_beta"][0] / sum(BASE["bug_beta"]))},
           "by_reruns": tab.to_dict("records"),
           "by_fail_prob_k1": band.to_dict("records"),
           "grid27_ranges": {c: [r(grid[c].min()), r(grid[c].max())] for c in grid.columns if c.startswith("k")},
           "max_abs_formula_gap": r(max((tab[c] - tab[c + "_formula"]).abs().max() for c in ["miss_build_all", "miss_build_intermittent", "rerun_hides_among_first_fail"])),
           "grid27_red_clean_by_n_flaky": grid.groupby("n_flaky")[["k0_red_build_clean", "k1_red_build_clean", "k2_red_build_clean", "k1_flaky_flagged_per_10"]].mean().round(4).reset_index().to_dict("records"),
           "grid27_k1_minus_k0_miss10": [r((grid.k1_miss_10builds_all - grid.k0_miss_10builds_all).min()), r((grid.k1_miss_10builds_all - grid.k0_miss_10builds_all).max())],
           "data_check": {"rows": len(data), "miss_build_all_first2000": r(1 - data.first_build_red.mean())}}
    json.dump(out, open(RES / "a1091_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：再実行の回数と、見逃し・赤いビルド
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    ax = axes[0]
    x = np.arange(len(KS)); wdt = 0.36
    v1 = t.miss_build_intermittent * 100; v2 = t.miss_10builds_intermittent * 100
    ax.bar(x - wdt / 2, v1, wdt, color=LIGHT, label="1回のビルドで")
    ax.bar(x + wdt / 2, v2, wdt, color=ORANGE, label="10回のビルドで一度も赤くならない")
    for xx, a in zip(x - wdt / 2, v1):
        ax.text(xx, a + 1.5, f"{round(a, 2):g}", ha="center", fontsize=7.5)
    for xx, a in zip(x + wdt / 2, v2):
        ax.text(xx, a + 1.5, f"{round(a, 2):g}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{k}回" for k in KS]); ax.set_xlabel("落ちたときの再実行の回数（最大）")
    ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("見逃した割合（%）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("ときどき落とす本当のバグ", fontsize=11)
    ax = axes[1]
    v3 = t.red_build_share_clean * 100
    ax.bar(x, v3, 0.5, color=GRAY)
    for xx, a in zip(x, v3):
        ax.text(xx, a + 1.5, f"{round(a, 2):g}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{k}回" for k in KS]); ax.set_xlabel("落ちたときの再実行の回数（最大）")
    ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("赤くなったビルドの割合（%）")
    ax.set_title("バグのないビルド（ときどき落ちるテスト60本）", fontsize=11)
    fig.suptitle("再実行を増やすと、バグのないビルドは赤くならなくなるが、ときどき落とすバグも通る", fontsize=12, y=1.03)
    save(fig, "a1091_reruns.png", SRC, y=-0.03)

    # 図2：落とす確率ごと（k=1）
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    x = np.arange(len(band)); wdt = 0.27
    ax.bar(x - wdt, band.miss_build * 100, wdt, color=LIGHT, label="1回のビルドで見逃す")
    ax.bar(x, band.miss_10builds * 100, wdt, color=ORANGE, label="10回のビルドで一度も赤くならない")
    ax.bar(x + wdt, (1 - band.flagged_or_red) * 100, wdt, color=INK, label="10回で赤くもならず、「再実行で通った」も2回未満")
    ax.set_xticks(x); ax.set_xticklabels([f"{b}\n（{n}件）" for b, n in zip(band.band, band.n)], fontsize=8.5)
    ax.set_xlabel("ときどき落とすバグが、1回の実行でテストを落とす確率")
    ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("割合（%、再実行は最大1回）")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("落とす確率の低いバグほど通る。「再実行で通った」の記録で拾える分もある", fontsize=11)
    save(fig, "a1091_by_prob.png", SRC, y=-0.04)

    # 図3：27通り（全部のバグのうち、10回のビルドで一度も赤くならない割合）
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    g9 = grid[grid.n_flaky == 60].reset_index(drop=True)
    x = np.arange(len(g9)); wdt = 0.27
    for j, (k, col) in enumerate([(0, GRAY), (1, ORANGE), (2, BLUE)]):
        ax.bar(x + (j - 1) * wdt, g9[f"k{k}_miss_10builds_all"] * 100, wdt, color=col, label=f"再実行 最大{k}回")
    ax.set_xticks(x); ax.set_xticklabels([f"{int(s * 100)}%\n平均{m}" for s, m in zip(g9.share_intermittent, g9.bug_fail_mean)], fontsize=8.5)
    ax.set_xlabel("ときどき落とすバグの割合と、その落とす確率の平均")
    ax.set_ylabel("一度も赤くならないバグ（全部のうち、%）")
    ax.set_ylim(0, max(g9.k2_miss_10builds_all.max() * 100 * 1.3, 10))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("置き方9通り（ときどき落ちるテスト60本）：10回のビルドで一度も赤くならないバグは、\nときどき落とすバグの多さと落とす確率で大きく変わる", fontsize=11)
    save(fig, "a1091_robust.png", SRC, y=-0.04)

    print(tab.T.to_string()); print(band.to_string())
    print(json.dumps({k: out[k] for k in ["grid27_ranges", "grid27_k1_minus_k0_miss10", "data_check"]}, ensure_ascii=False, indent=1))
    print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
