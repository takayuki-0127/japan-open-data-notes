"""1035 道のりの長い日ほど、1kmあたりの時間は短いのか？（架空のデータ）

架空の配送の車1台の、1日の道のり（km）と1日の時間（分）。
1日の時間＝決まった時間（積み込み・車を停める準備など、道のりによらない）＋道のり×その日の走りの遅さ（分/km）。
遅くなると前もって分かる日（行事の日など）は、道のりを短く組む（選び方）。
道のりの記録には誤差がある。
作成者が置いたこの決まりで、「道のりの長い日ほど1kmあたりが短い」の見え方のうち、
同じ日に道のりを足したときに本当に短くなる分（決まった時間の割り算）がどれだけかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1035
SRC = "架空の配送の車の記録（作成者が乱数で作成、seed 1035）"
BASE = {"fixed": 25.0, "beta": 1.5, "err": 0.06}
PACE, D0, SD_D, SK, SU = 2.4, 60.0, 0.25, 0.12, 0.10
N_DAY, REPS = 300, 200


def make(rng, n=N_DAY, fixed=25.0, beta=1.5, err=0.06):
    k = rng.normal(0, SK, n)                      # 前もって分かる遅さ（対数）
    u = rng.normal(0, SU, n)                      # 当日にならないと分からない遅さ（対数）
    pace = PACE * np.exp(k + u)                   # 分/km
    true_km = D0 * np.exp(rng.normal(0, SD_D, n) - beta * k)
    rec_km = true_km * np.exp(rng.normal(0, err, n)) if err > 0 else true_km.copy()
    drive = true_km * pace
    total = fixed + drive
    return pd.DataFrame({"day": np.arange(1, n + 1), "known_slow": k, "pace_min_per_km": pace,
                         "true_km": true_km, "rec_km": rec_km, "drive_min": drive,
                         "fixed_min": np.full(n, fixed), "total_min": total})


def measure(df, fixed):
    q1, q3 = df.rec_km.quantile([.25, .75])
    s, l = df[df.rec_km <= q1], df[df.rec_km >= q3]
    pk = df.total_min / df.rec_km
    obs = float(pk[l.index].mean() - pk[s.index].mean())
    # 決まった時間の割り算（決まった時間÷本当の道のり）の、長い日と短い日の差。
    # 同じ日に道のりだけを変えたとき（走りの遅さは同じ）に動くのはこの分だけ
    causal = float((fixed / l.true_km).mean() - (fixed / s.true_km).mean())
    plus10 = float((fixed / (df.true_km + 10) - fixed / df.true_km).mean())
    true_pk = df.total_min / df.true_km
    true_gap = float(true_pk[l.index].mean() - true_pk[s.index].mean())
    pace_gap = float(l.pace_min_per_km.mean() - s.pace_min_per_km.mean())
    b, a = np.polyfit(df.rec_km, df.total_min, 1)
    return {"obs_gap": obs, "causal_gap": causal, "plus10": plus10, "truekm_gap": true_gap,
            "pace_gap": pace_gap, "short_km": float(s.rec_km.mean()), "long_km": float(l.rec_km.mean()),
            "short_pk": float(pk[s.index].mean()), "long_pk": float(pk[l.index].mean()),
            "intercept": float(a), "slope": float(b), "mean_pace": float(df.pace_min_per_km.mean())}


def reps(seed0, n_rep, **kw):
    rows = [measure(make(np.random.default_rng(seed0 + r), **kw), kw["fixed"]) for r in range(n_rep)]
    return pd.DataFrame(rows)


def r(x, d=3):
    return round(float(x), d)


def main():
    t0 = time.time()
    df = make(np.random.default_rng(SEED), **BASE)
    df.round(4).to_csv(DATA / "days.csv", index=False)
    one = measure(df, BASE["fixed"])

    # 帯ごと（1回分の300日）
    bands = [(0, 45), (45, 55), (55, 65), (65, 75), (75, 999)]
    brows = []
    for lo, hi in bands:
        g = df[(df.rec_km >= lo) & (df.rec_km < hi)]
        brows.append({"band": f"{lo}〜{hi if hi < 999 else ''}km", "days": len(g),
                      "per_km_min": r((g.total_min / g.rec_km).mean()), "pace_min_per_km": r(g.pace_min_per_km.mean()),
                      "fixed_per_km_min": r((g.fixed_min / g.true_km).mean())})
    pd.DataFrame(brows).to_csv(RES / "bands_one.csv", index=False)

    # 200回の平均：基本と、しくみを1つずつ
    cases = [("基本（決まった時間・選び方・記録の誤差）", BASE),
             ("決まった時間だけ", {"fixed": 25.0, "beta": 0.0, "err": 0.0}),
             ("選び方だけ", {"fixed": 0.0, "beta": 1.5, "err": 0.0}),
             ("記録の誤差だけ", {"fixed": 0.0, "beta": 0.0, "err": 0.06}),
             ("どれもなし", {"fixed": 0.0, "beta": 0.0, "err": 0.0})]
    crow, base_sim = [], None
    for i, (name, kw) in enumerate(cases):
        s = reps(SEED * 1000 + i * REPS, REPS, **kw)
        if i == 0:
            base_sim = s
        crow.append({"case": name, **{k: kw[k] for k in ["fixed", "beta", "err"]},
                     "obs_gap": r(s.obs_gap.mean()), "obs_gap_p10": r(s.obs_gap.quantile(.1)),
                     "obs_gap_p90": r(s.obs_gap.quantile(.9)), "causal_gap": r(s.causal_gap.mean()),
                     "causal_share": r(s.causal_gap.mean() / s.obs_gap.mean()) if abs(s.obs_gap.mean()) > 1e-9 else None,
                     "truekm_gap": r(s.truekm_gap.mean()), "pace_gap": r(s.pace_gap.mean()),
                     "plus10": r(s.plus10.mean()), "short_km": r(s.short_km.mean(), 2), "long_km": r(s.long_km.mean(), 2),
                     "short_pk": r(s.short_pk.mean()), "long_pk": r(s.long_pk.mean()),
                     "intercept": r(s.intercept.mean(), 2), "slope": r(s.slope.mean()), "mean_pace": r(s.mean_pace.mean())})
    cdf = pd.DataFrame(crow)
    cdf.to_csv(RES / "mechanisms.csv", index=False)

    # 確かめ：決まった時間 × 選び方の強さ × 記録の誤差（36通り、各50回）
    grow = []
    j = 0
    for f in [0.0, 10.0, 25.0, 40.0]:
        for b in [0.0, 1.5, 3.0]:
            for e in [0.0, 0.06, 0.12]:
                s = reps(SEED * 100000 + j * 50, 50, fixed=f, beta=b, err=e)
                j += 1
                o, c = s.obs_gap.mean(), s.causal_gap.mean()
                grow.append({"fixed": f, "beta": b, "err": e, "obs_gap": r(o), "causal_gap": r(c),
                             "causal_share": r(c / o) if o < -0.005 else None,
                             "intercept": r(s.intercept.mean(), 2)})
    gdf = pd.DataFrame(grow)
    gdf.to_csv(RES / "grid.csv", index=False)
    nz = gdf[(gdf.beta > 0) | (gdf.err > 0)]
    nz = nz[nz.fixed > 0]
    out = {
        "base": BASE, "pace_mean_min_per_km_set": PACE, "D0_km": D0, "n_day": N_DAY, "reps": REPS,
        "one_draw": {k: r(v) for k, v in one.items()},
        "mechanisms_200reps": cdf.to_dict("records"),
        "base_parts": {
            "obs_gap": r(cdf.obs_gap[0]), "causal_gap": r(cdf.causal_gap[0]), "pace_gap": r(cdf.pace_gap[0]),
            "record_error_part": r(cdf.obs_gap[0] - cdf.truekm_gap[0]),
            "sum_of_single_mechanisms": r(cdf.obs_gap[1] + cdf.obs_gap[2] + cdf.obs_gap[3]),
            "intercept_over_fixed": r(cdf.intercept[0] / BASE["fixed"], 2)},
        "grid_summary": {
            "n": int(len(gdf)),
            "obs_gap_min": r(gdf.obs_gap.min()), "obs_gap_max": r(gdf.obs_gap.max()),
            "causal_share_min_fixed_gt0_and_other": r(nz.causal_share.min()),
            "causal_share_max_fixed_gt0_and_other": r(nz.causal_share.max()),
            "n_fixed_gt0_and_other": int(len(nz)),
            "all_zero_obs_gap": r(gdf[(gdf.fixed == 0) & (gdf.beta == 0) & (gdf.err == 0)].obs_gap.iloc[0]),
            "fixed_only_share_min": r(gdf[(gdf.fixed > 0) & (gdf.beta == 0) & (gdf.err == 0)].causal_share.min()),
            "fixed_only_share_max": r(gdf[(gdf.fixed > 0) & (gdf.beta == 0) & (gdf.err == 0)].causal_share.max()),
            "intercept_base_cell": r(gdf[(gdf.fixed == 25) & (gdf.beta == 1.5) & (gdf.err == 0.06)].intercept.iloc[0], 2),
            "intercept_min_fixed25": r(gdf[gdf.fixed == 25].intercept.min(), 2),
            "intercept_max_fixed25": r(gdf[gdf.fixed == 25].intercept.max(), 2),
            "intercept_fixed0_min": r(gdf[gdf.fixed == 0].intercept.min(), 2),
            "intercept_fixed0_max": r(gdf[gdf.fixed == 0].intercept.max(), 2),
        },
    }

    # 図1：1回分の300日
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.rec_km, df.total_min / df.rec_km, s=10, color=BLUE, alpha=.5, lw=0, label="1日（300日）")
    bd = pd.DataFrame(brows)
    mids = [40, 50, 60, 70, 82]
    ax.plot(mids, bd.per_km_min, color=ORANGE, marker="o", lw=2, label="道のりの帯ごとの平均")
    ax.set_xlabel("記録の道のり（km/日）"); ax.set_ylabel("1kmあたりの時間（分）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("道のりの長い日ほど、1kmあたりの時間は短く見える（1回分の300日）")
    save(fig, "a1035_scatter.png", SRC)

    # 図2：見かけの差と、同じ日に伸ばしたときの差（200回の平均）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    names = cdf.case.tolist()[::-1]
    y = np.arange(len(names))
    ax.barh(y + 0.18, -cdf.obs_gap[::-1], height=0.36, color=GRAY, label="見かけの差（長い4分の1の日−短い4分の1の日）")
    ax.barh(y - 0.18, -cdf.causal_gap[::-1], height=0.36, color=BLUE, label="道のりで本当に変わる分（決まった時間÷道のり の差）")
    for yy, v in zip(y, -cdf.obs_gap[::-1]):
        ax.text(max(v, 0) + 0.005, yy + 0.18, f"{v + 0.0:.3f}".replace("-", "−"), va="center", fontsize=8)
    for yy, v in zip(y, -cdf.causal_gap[::-1]):
        ax.text(max(v, 0) + 0.005, yy - 0.18, f"{abs(v) if abs(v) < 5e-4 else v:.3f}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("1kmあたり短くなる時間（分、200回の平均）")
    ax.set_xlim(0, max(-cdf.obs_gap.min(), 0.1) * 1.3)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("見かけの差（灰）のうち、道のりで本当に変わる分（青）は基本で4割ほど")
    save(fig, "a1035_mechanisms.png", SRC)

    # 図3：36通り
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    cols = {0.0: GRAY, 1.5: BLUE, 3.0: ORANGE}
    labs = {0.0: "遅い日を短く組む β＝0（しない）", 1.5: "β＝1.5（基本）", 3.0: "β＝3（強く短くする）"}
    for b, g in gdf.groupby("beta"):
        ax.scatter(-g.obs_gap, -g.causal_gap, color=cols[b], s=28, label=labs[b])
    m = max(-gdf.obs_gap.max(), -gdf.obs_gap.min()) * 1.05
    ax.plot([0, m], [0, m], color=INK, lw=0.8, ls="--")
    ax.text(m * 0.62, m * 0.66, "見かけ＝本当", fontsize=8, color=INK, rotation=0)
    ax.set_xlabel("見かけの差（1kmあたり短くなる分）"); ax.set_ylabel("道のりで本当に変わる分（分）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("置き方36通り：点線より下の分は、伸ばしても短くならない")
    save(fig, "a1035_grid.png", SRC)

    out["run_sec_note"] = "所要時間は results に入れない（流すたびに変わるため）"
    json.dump(out, open(RES / "a1035_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
