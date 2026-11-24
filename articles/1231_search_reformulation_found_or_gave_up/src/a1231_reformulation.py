"""1231 言いかえて検索し直す人が減ったのは、見つかったからか、あきらめたからか？（架空のデータ）

架空の社内の文書検索。1回の検索の場（セッション）ごとに、探しものが「よくある探しもの」か「まれな探しもの」かを置き、
検索するたびに正しい文書が上位10件に入る確率を、古い検索 A と新しい検索 B で置く。
見つからなければ、確率 q で言いかえて検索し直し、そうでなければあきらめる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1231
SRC = "架空の社内の文書検索の記録（作成者が乱数で作成、seed 1231）"
N = 20000
MAXQ = 5
BASE = dict(rare_share=0.3, pA_common=0.55, pA_rare=0.30, pB_common=0.70, pB_rare=0.15,
            q0=0.75, decay=0.8, mB=0.8, snippet=0.2, wrong_click=0.4, wrong_long=0.15)


def simulate(rng, prm, arm, n=N):
    rare = rng.random(n) < prm["rare_share"]
    p = np.where(rare, prm[f"p{arm}_rare"], prm[f"p{arm}_common"])
    m = prm["mB"] if arm == "B" else 1.0
    nq = np.zeros(n, int)
    found = np.zeros(n, bool)
    done = np.zeros(n, bool)
    longclick = np.zeros(n, bool)
    anyclick = np.zeros(n, bool)
    for t in range(1, MAXQ + 1):
        act = ~done
        nq[act] += 1
        hit = act & (rng.random(n) < p)
        found |= hit
        snip = rng.random(n) < prm["snippet"]
        anyclick |= hit & ~snip
        longclick |= hit & ~snip
        miss = act & ~hit
        wc = miss & (rng.random(n) < prm["wrong_click"])
        anyclick |= wc
        longclick |= wc & (rng.random(n) < prm["wrong_long"])
        q = prm["q0"] * prm["decay"] ** (t - 1) * m if t < MAXQ else 0.0
        again = miss & (rng.random(n) < q)
        done |= hit | (miss & ~again)
    return pd.DataFrame({"rare": rare.astype(int), "queries": nq, "found": found.astype(int),
                         "gave_up": (~found).astype(int), "any_click": anyclick.astype(int),
                         "long_click": longclick.astype(int)})


def summarize(df):
    one = df.queries == 1
    return {"reform_share": df.queries.gt(1).mean() * 100,
            "mean_queries": df.queries.mean(),
            "found": df.found.mean() * 100, "gave_up": df.gave_up.mean() * 100,
            "found_at1": (one & (df.found == 1)).mean() * 100,
            "gaveup_at1": (one & (df.found == 0)).mean() * 100,
            "zero_click": (df.any_click == 0).mean() * 100,
            "long_click": df.long_click.mean() * 100,
            "found_common": df[df.rare == 0].found.mean() * 100, "found_rare": df[df.rare == 1].found.mean() * 100,
            "zero_click_found": ((df.any_click == 0) & (df.found == 1)).mean() * 100}


def compare(prm, seed, reps):
    out = {"A": [], "B": []}
    for r in range(reps):
        for arm in ["A", "B"]:
            out[arm].append(summarize(simulate(np.random.default_rng(seed * 1000 + r * 2 + (arm == "B")), prm, arm)))
    return {a: pd.DataFrame(v).mean() for a, v in out.items()}


def main():
    t0 = time.time()
    ex = simulate(np.random.default_rng(SEED), BASE, "B")
    ex.insert(0, "session", np.arange(1, N + 1))
    ex.to_csv(DATA / "sessions_B_example.csv", index=False)

    res = compare(BASE, SEED, 50)
    A, B = res["A"], res["B"]
    keys = ["reform_share", "mean_queries", "found", "gave_up", "found_at1", "gaveup_at1", "zero_click",
            "long_click", "found_common", "found_rare", "zero_click_found"]
    tab = pd.DataFrame({"metric": keys, "A_old": [round(A[k], 4 if k == "mean_queries" else 2) for k in keys],
                        "B_new": [round(B[k], 4 if k == "mean_queries" else 2) for k in keys]})
    tab["B_minus_A"] = [round(B[k] - A[k], 4) for k in keys]
    tab.to_csv(RES / "base_compare.csv", index=False)
    d_reform = B.reform_share - A.reform_share
    d_f1 = B.found_at1 - A.found_at1
    d_g1 = B.gaveup_at1 - A.gaveup_at1
    headline = {
        "reform_A": round(A.reform_share, 2), "reform_B": round(B.reform_share, 2),
        "reform_drop_pt": round(-d_reform, 2),
        "drop_from_found_at1_pt": round(d_f1, 2), "drop_from_gaveup_at1_pt": round(d_g1, 2),
        "drop_share_gaveup_pct": round(d_g1 / -d_reform * 100, 2),
        "found_A": round(A.found, 2), "found_B": round(B.found, 2),
        "gaveup_A": round(A.gave_up, 2), "gaveup_B": round(B.gave_up, 2),
        "zero_click_A": round(A.zero_click, 2), "zero_click_B": round(B.zero_click, 2),
        "zero_click_found_A": round(A.zero_click_found, 2), "zero_click_found_B": round(B.zero_click_found, 2),
        "long_click_A": round(A.long_click, 2), "long_click_B": round(B.long_click, 2),
        "found_rare_A": round(A.found_rare, 2), "found_rare_B": round(B.found_rare, 2),
        "found_common_A": round(A.found_common, 2), "found_common_B": round(B.found_common, 2),
        "sessions": N, "reps": 50,
    }
    ex_sum = {"arm": "B", "sessions": N, "reform_share": round(ex.queries.gt(1).mean() * 100, 2),
              "found": round(ex.found.mean() * 100, 2), "zero_click": round((ex.any_click == 0).mean() * 100, 2)}

    # 確かめ：まれな探しもの（B）× あきらめやすさ × 要約で済む割合 × まれな探しものの割合
    rows = []
    i = 0
    for pr in [0.15, 0.25, 0.30]:
        for mB in [1.0, 0.8, 0.6]:
            for sn in [0.0, 0.2, 0.4]:
                for rs in [0.3, 0.5]:
                    prm = dict(BASE, pB_rare=pr, mB=mB, snippet=sn, rare_share=rs)
                    r = compare(prm, SEED * 10 + i, 10); i += 1
                    a, b = r["A"], r["B"]
                    dr = b.reform_share - a.reform_share
                    rows.append({"pB_rare": pr, "giveup_factor_B": mB, "snippet": sn, "rare_share": rs,
                                 "reform_A": round(a.reform_share, 2), "reform_B": round(b.reform_share, 2),
                                 "found_A": round(a.found, 2), "found_B": round(b.found, 2),
                                 "zero_click_A": round(a.zero_click, 2), "zero_click_B": round(b.zero_click, 2),
                                 "long_click_A": round(a.long_click, 2), "long_click_B": round(b.long_click, 2),
                                 "d_reform": round(dr, 2), "d_found": round(b.found - a.found, 2),
                                 "d_found_at1": round(b.found_at1 - a.found_at1, 2),
                                 "d_gaveup_at1": round(b.gaveup_at1 - a.gaveup_at1, 2),
                                 "gaveup_share_of_drop": round((b.gaveup_at1 - a.gaveup_at1) / -dr * 100, 2) if dr < 0 else None,
                                 "d_long_click": round(b.long_click - a.long_click, 2)})
    g = pd.DataFrame(rows)
    g.to_csv(RES / "grid.csv", index=False)
    fell = g[g.d_reform < 0]
    robust = {
        "settings": len(g), "reform_fell": len(fell),
        "reform_fell_and_found_fell": int((fell.d_found < 0).sum()),
        "reform_fell_and_found_rose": int((fell.d_found > 0).sum()),
        "gaveup_share_of_drop_min": float(fell.gaveup_share_of_drop.min()),
        "gaveup_share_of_drop_max": float(fell.gaveup_share_of_drop.max()),
        "d_found_min": float(g.d_found.min()), "d_found_max": float(g.d_found.max()),
        "d_reform_min": float(g.d_reform.min()), "d_reform_max": float(g.d_reform.max()),
        "longclick_sign_matches_found": int((np.sign(g.d_long_click) == np.sign(g.d_found)).sum()),
        "zero_click_rose_while_found_rose": int(((g.zero_click_B > g.zero_click_A) & (g.d_found > 0)).sum()),
        "mB1_reform_fell": int((fell.giveup_factor_B == 1.0).sum()),
        "mB1_settings": int((g.giveup_factor_B == 1.0).sum()),
        "mB1_gaveup_share_min": float(fell[fell.giveup_factor_B == 1.0].gaveup_share_of_drop.min()),
        "mB1_gaveup_share_max": float(fell[fell.giveup_factor_B == 1.0].gaveup_share_of_drop.max()),
        "mB06_gaveup_share_min": float(fell[fell.giveup_factor_B == 0.6].gaveup_share_of_drop.min()),
        "mB06_gaveup_share_max": float(fell[fell.giveup_factor_B == 0.6].gaveup_share_of_drop.max()),
    }
    json.dump({"headline": headline, "example_one_run_B": ex_sum, "robust": robust, "setup": BASE},
              open(RES / "a1231_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：1回目で終わった場の内訳
    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = ["A 古い検索", "B 新しい検索"]
    f1 = [round(A.found_at1, 2), round(B.found_at1, 2)]
    g1 = [round(A.gaveup_at1, 2), round(B.gaveup_at1, 2)]
    rf = [headline["reform_A"], headline["reform_B"]]
    y = [1, 0]
    ax.barh(y, f1, color=BLUE, label="1回目で見つかって終わった")
    ax.barh(y, g1, left=f1, color=ORANGE, label="1回目であきらめて終わった")
    ax.barh(y, rf, left=np.add(f1, g1), color=GRAY, label="言いかえて検索し直した")
    for yi, a, b, c in zip(y, f1, g1, rf):
        for left, w in [(0, a), (a, b), (a + b, c)]:
            ax.text(left + w / 2, yi, f"{w:.2f}%", ha="center", va="center", color="white", fontsize=10)
    ax.set_yticks(y, labels); ax.set_xlim(0, 100); ax.set_xlabel("検索の場の割合（%、2万件×50回の平均）")
    ax.set_title(f"検索し直した割合 {rf[0]}%→{rf[1]}%：減りの{headline['drop_share_gaveup_pct']}%は1回目であきらめた場の増え", fontsize=11.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=9, frameon=False)
    save(fig, "a1231_first_query.png", SRC, y=-0.30)

    # 図2：見える数と本当の数
    fig, ax = plt.subplots(figsize=(8, 4))
    names = ["検索し直した", "クリックなし", "長く読んだ\nクリック", "本当に\n見つかった", "本当に\nあきらめた"]
    va = [headline["reform_A"], headline["zero_click_A"], headline["long_click_A"], headline["found_A"], headline["gaveup_A"]]
    vb = [headline["reform_B"], headline["zero_click_B"], headline["long_click_B"], headline["found_B"], headline["gaveup_B"]]
    x = np.arange(len(names))
    b1 = ax.bar(x - 0.2, va, 0.4, color=GRAY, label="A 古い検索")
    b2 = ax.bar(x + 0.2, vb, 0.4, color=BLUE, label="B 新しい検索")
    for bars, vals in [(b1, va), (b2, vb)]:
        for bb, v in zip(bars, vals):
            ax.text(bb.get_x() + bb.get_width() / 2, v + 1, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.axvline(2.5, color=INK, lw=0.6, ls=":")
    ax.text(1, 92, "記録から見える数", ha="center", fontsize=10); ax.text(3.5, 92, "本当の数（記録には残らない）", ha="center", fontsize=10)
    ax.set_xticks(x, names); ax.set_ylim(0, 100); ax.set_ylabel("検索の場の割合（%）")
    ax.set_title("検索し直しは減ったが、本当に見つかった割合も下がった")
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0, 0.92))
    save(fig, "a1231_seen_vs_true.png", SRC)

    # 図3：54通り
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for mB, c, mk in zip([1.0, 0.8, 0.6], [GRAY, BLUE, ORANGE], ["o", "s", "^"]):
        gg = g[g.giveup_factor_B == mB]
        ax.scatter(gg.d_reform, gg.d_found, color=c, marker=mk, s=30,
                   label=f"B で見つからないときの検索し直しやすさ A の{mB:g}倍")
    ax.axhline(0, color=INK, lw=0.8); ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("検索し直した割合の変化 B−A（ポイント）"); ax.set_ylabel("本当に見つかった割合の変化 B−A（ポイント）")
    ax.set_title(f"検索し直しが減った{robust['reform_fell']}通りのうち{robust['reform_fell_and_found_fell']}通りは、見つかった割合も下がった", fontsize=11.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1231_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust), f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
