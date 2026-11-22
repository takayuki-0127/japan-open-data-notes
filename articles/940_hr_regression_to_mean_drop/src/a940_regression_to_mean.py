"""940 去年高かった人の点が下がるのは、本当に下がったのか？（平均への回帰）（架空のデータ）

架空の会社の社員400人。人ごとに「本当の働きぶり」を置き、毎年の評価点は
本当の働きぶり＋その年の振れ（評価者の見方・たまたまの出来事）とする。
基本は2年で本当の働きぶりを変えず、確かめで「本当に下がった人」を1割まぜる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 940
SRC = "架空の会社の社員の評価点（作成者が乱数で作成、seed 940）"
rng = np.random.default_rng(SEED)

BASE = {"n": 400, "mu": 60.0, "sd_true": 6.0, "sd_noise": 6.0, "top": 0.10,
        "decline_share": 0.0, "decline": 6.0}
N_REP = 1000
DROP = 5.0  # 「下がった」とする目安（点）


def make(rng, n=400, mu=60.0, sd_true=6.0, sd_noise=6.0, decline_share=0.0, decline=6.0, **_):
    t1 = mu + rng.normal(0, sd_true, n)
    dec = rng.random(n) < decline_share
    t2 = t1 - dec * decline
    y1 = t1 + rng.normal(0, sd_noise, n)
    y2 = t2 + rng.normal(0, sd_noise, n)
    return t1, t2, y1, y2, dec


def reliability(sd_true, sd_noise):
    return sd_true ** 2 / (sd_true ** 2 + sd_noise ** 2)


def groups(y1, top):
    n = len(y1)
    k = int(round(n * top))
    o = np.argsort(-y1, kind="stable")
    return o[:k], o[-k:]


def one_year(rng, **kw):
    t1, t2, y1, y2, dec = make(rng, **kw)
    hi, lo = groups(y1, kw["top"])
    r = reliability(kw["sd_true"], kw["sd_noise"])
    m1 = y1.mean()
    pred = m1 + r * (y1 - m1)  # 平均へ寄せた見込み（本当の働きぶりが変わらないとき）
    d = y2 - y1
    return {"top_y1": y1[hi].mean(), "top_y2": y2[hi].mean(), "top_true": t1[hi].mean(),
            "top_change": d[hi].mean(), "top_share_down": (d[hi] < 0).mean(),
            "top_share_down5": (d[hi] <= -DROP).mean(),
            "top_pred_change": (pred[hi] - y1[hi]).mean(),
            "bottom_change": d[lo].mean(), "bottom_share_up": (d[lo] > 0).mean(),
            "all_change": d.mean(),
            "formula_top_change": -(1 - r) * (y1[hi].mean() - m1)}


def flag_test(rng, **kw):
    """本当に下がった人を、2年の点から見つけられるか（上位1割の中で）"""
    t1, t2, y1, y2, dec = make(rng, **kw)
    r = reliability(kw["sd_true"], kw["sd_noise"])
    m1 = y1.mean()
    pred = m1 + r * (y1 - m1)
    hi, _ = groups(y1, kw["top"])
    naive = (y2 - y1) <= -DROP
    adj = (y2 - pred) <= -DROP
    out = {}
    for name, f in [("naive", naive), ("adjusted", adj)]:
        fh = f[hi]
        out[name] = {"flag_share_top": fh.mean(),
                     "flag_share_top_unchanged": fh[~dec[hi]].mean() if (~dec[hi]).any() else np.nan,
                     "precision_top": dec[hi][fh].mean() if fh.any() else np.nan,
                     "recall_top": fh[dec[hi]].mean() if dec[hi].any() else np.nan,
                     "flag_share_all_unchanged": f[~dec].mean(),
                     "recall_all": f[dec].mean() if dec.any() else np.nan,
                     "precision_all": dec[f].mean() if f.any() else np.nan}
    return out


def guidance_test(rng, **kw):
    """下位1割に指導、上位1割に表彰をしたと置く（効き目は0）。前年との差で効き目に見えるか"""
    t1, t2, y1, y2, dec = make(rng, **kw)
    n = len(y1)
    hi, lo = groups(y1, kw["top"])
    d = y2 - y1
    mid = np.setdiff1d(np.arange(n), np.concatenate([hi, lo]))
    # 下位2割を半分ずつ（でたらめに）指導あり・なしに分けた比べ方
    k2 = int(round(n * kw["top"] * 2))
    lo2 = np.argsort(y1, kind="stable")[:k2]
    g = rng.permutation(lo2)
    a, b = g[: k2 // 2], g[k2 // 2:]
    return {"guided_change": d[lo].mean(), "praised_change": d[hi].mean(), "others_change": d[mid].mean(),
            "naive_effect_guidance": d[lo].mean() - d[mid].mean(),
            "naive_effect_praise": d[hi].mean() - d[mid].mean(),
            "random_split_effect": d[a].mean() - d[b].mean()}


def agg(rows):
    df = pd.DataFrame(rows)
    return df


def main():
    # 1) 例の1年（data に置く）
    t1, t2, y1, y2, dec = make(rng, **BASE)
    ex = pd.DataFrame({"person_id": np.arange(1, BASE["n"] + 1), "true": t1.round(3),
                       "score_y1": y1.round(3), "score_y2": y2.round(3)})
    ex.to_csv(DATA / "scores_example.csv", index=False)
    ex = pd.read_csv(DATA / "scores_example.csv")
    hi, lo = groups(ex.score_y1.values, BASE["top"])
    d = (ex.score_y2 - ex.score_y1).values
    example = {"top_y1": round(float(ex.score_y1.values[hi].mean()), 2),
               "top_y2": round(float(ex.score_y2.values[hi].mean()), 2),
               "top_true": round(float(ex.true.values[hi].mean()), 2),
               "top_share_down": round(float((d[hi] < 0).mean()), 3),
               "top_share_down5": round(float((d[hi] <= -DROP).mean()), 3),
               "bottom_y1": round(float(ex.score_y1.values[lo].mean()), 2),
               "bottom_y2": round(float(ex.score_y2.values[lo].mean()), 2),
               "bottom_share_up": round(float((d[lo] > 0).mean()), 3),
               "all_y1": round(float(ex.score_y1.mean()), 2), "all_y2": round(float(ex.score_y2.mean()), 2),
               "corr_y1_y2": round(float(np.corrcoef(ex.score_y1, ex.score_y2)[0, 1]), 3)}

    # 2) 1,000回（本当の働きぶりは変えない）
    rows = [one_year(np.random.default_rng(SEED * 1000 + i), **BASE) for i in range(N_REP)]
    df = pd.DataFrame(rows)
    df.to_csv(RES / "years_1000.csv", index=False, float_format="%.4f")
    base = {k: round(float(df[k].mean()), 3) for k in df.columns}
    base["top_change_p10"] = round(float(df.top_change.quantile(.1)), 2)
    base["top_change_p90"] = round(float(df.top_change.quantile(.9)), 2)
    base["reliability"] = reliability(BASE["sd_true"], BASE["sd_noise"])

    # 3) 前年の順位の帯ごとの変化（1,000回の平均）
    bands = [(0, .05), (.05, .1), (.1, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .9), (.9, .95), (.95, 1)]
    bd = np.zeros(len(bands)); bt = np.zeros(len(bands)); by = np.zeros(len(bands))
    for i in range(N_REP):
        _, _, a1, a2, _ = make(np.random.default_rng(SEED * 1000 + i), **BASE)
        o = np.argsort(-a1, kind="stable")
        for j, (lo_, hi_) in enumerate(bands):
            idx = o[int(lo_ * BASE["n"]):int(hi_ * BASE["n"])]
            bd[j] += (a2[idx] - a1[idx]).mean() / N_REP
            by[j] += a1[idx].mean() / N_REP
    band_tab = pd.DataFrame({"前年の順位の帯": [f"上位{int(a*100)}〜{int(b*100)}%" for a, b in bands],
                             "前年の点（平均）": by.round(2), "今年との差（平均）": bd.round(2)})
    band_tab.to_csv(RES / "change_by_band.csv", index=False)

    # 4) 指導・表彰（効き目0）が効いて見えるか
    gt = pd.DataFrame([guidance_test(np.random.default_rng(SEED * 3000 + i), **BASE) for i in range(N_REP)])
    guidance = {k: round(float(gt[k].mean()), 2) for k in gt.columns}
    guidance["random_split_effect_p10"] = round(float(gt.random_split_effect.quantile(.1)), 2)
    guidance["random_split_effect_p90"] = round(float(gt.random_split_effect.quantile(.9)), 2)

    # 5) 本当に下がった人を1割まぜたとき、見つけられるか
    kw = dict(BASE); kw["decline_share"] = 0.10
    ft = [flag_test(np.random.default_rng(SEED * 5000 + i), **kw) for i in range(N_REP)]
    flag = {m: {k: round(float(np.nanmean([f[m][k] for f in ft])), 3) for k in ft[0][m]} for m in ["naive", "adjusted"]}
    # 下がった人をまぜたときの上位1割の下がり方
    mixed = pd.DataFrame([one_year(np.random.default_rng(SEED * 5000 + i), **kw) for i in range(N_REP)])
    flag["mixed_top_change"] = round(float(mixed.top_change.mean()), 3)
    flag["mixed_all_change"] = round(float(mixed.all_change.mean()), 3)

    # 6) 確かめ：振れの大きさ（確かさ）と上位の切り方を変える（各300回）
    rob = []
    for sdn in [3.0, 4.5, 6.0, 9.0, 12.0]:
        for top in [0.05, 0.10, 0.20]:
            kk = dict(BASE); kk["sd_noise"] = sdn; kk["top"] = top
            rr = pd.DataFrame([one_year(np.random.default_rng(SEED * 7 + int(sdn * 10) * 1000 + int(top * 100) * 100000 + i), **kk)
                               for i in range(300)])
            kd = dict(kk); kd["decline_share"] = 0.10
            ff = [flag_test(np.random.default_rng(SEED * 9 + int(sdn * 10) * 1000 + int(top * 100) * 100000 + i), **kd)
                  for i in range(300)]
            rob.append({"振れの標準偏差": sdn, "確かさ（本当の散らばりの割合）": round(reliability(6.0, sdn), 3),
                        "上位の切り方": f"上位{int(top*100)}%",
                        "上位の前年の点": round(float(rr.top_y1.mean()), 2),
                        "上位の今年との差": round(float(rr.top_change.mean()), 2),
                        "式の見込み": round(float(rr.formula_top_change.mean()), 2),
                        "上位で下がった人の割合": round(float(rr.top_share_down.mean()), 3),
                        "上位で5点以上下がった人（変わらない人）_前年と比べる": round(float(np.nanmean([f["naive"]["flag_share_top_unchanged"] for f in ff])), 3),
                        "上位で5点以上下がった人（変わらない人）_見込みと比べる": round(float(np.nanmean([f["adjusted"]["flag_share_top_unchanged"] for f in ff])), 3),
                        "上位で拾った人のうち本当に下がった人_前年と比べる": round(float(np.nanmean([f["naive"]["precision_top"] for f in ff])), 3),
                        "上位で拾った人のうち本当に下がった人_見込みと比べる": round(float(np.nanmean([f["adjusted"]["precision_top"] for f in ff])), 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"settings": {**BASE, "drop_flag_points": DROP, "n_rep": N_REP},
           "example_year": example, "base_1000": base, "by_band": band_tab.to_dict("records"),
           "guidance_praise_no_effect": guidance, "flag_with_10pct_true_decline": flag,
           "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a940_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1年の散布図（前年と今年）
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.scatter(ex.score_y1, ex.score_y2, s=8, color=LIGHT, lw=0)
    ax.scatter(ex.score_y1.values[hi], ex.score_y2.values[hi], s=12, color=ORANGE, lw=0, label="前年の上位1割（40人）")
    ax.scatter(ex.score_y1.values[lo], ex.score_y2.values[lo], s=12, color=BLUE, lw=0, label="前年の下位1割（40人）")
    lim = [min(ex.score_y1.min(), ex.score_y2.min()) - 1, max(ex.score_y1.max(), ex.score_y2.max()) + 1]
    ax.plot(lim, lim, color=GRAY, lw=1, ls="--", label="前年と同じ点の線")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("前年の評価点"); ax.set_ylabel("今年の評価点")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"本当の働きぶりを変えていないのに、前年の上位1割は\n平均{example['top_y1']:.1f}点→{example['top_y2']:.1f}点に下がった（例の1年、400人）")
    save(fig, "a940_scatter.png", SRC)

    # 図2：前年の順位の帯ごとの、今年との差
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    col = [ORANGE if v < 0 else BLUE for v in band_tab["今年との差（平均）"]]
    ax.bar(range(len(bands)), band_tab["今年との差（平均）"], color=col)
    for i, v in enumerate(band_tab["今年との差（平均）"]):
        ax.text(i, v + (0.25 if v >= 0 else -0.25), (f"{v:+.1f}" if abs(v) >= 0.05 else "0.0"), ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(range(len(bands))); ax.set_xticklabels([s.replace("上位", "") for s in band_tab["前年の順位の帯"]], fontsize=9)
    ax.set_xlabel("前年の順位の帯（上から何%）"); ax.set_ylabel("今年の点 − 前年の点（平均）")
    ax.set_ylim(min(bd) - 1.5, max(bd) + 1.5)
    ax.set_title("前年の上の人ほど下がり、下の人ほど上がる（本当の働きぶりは同じ、1,000回の平均）")
    save(fig, "a940_by_band.png", SRC)

    # 図3：本当に下がった人を1割まぜたとき（上位1割の中で、5点以上下がったと拾った人）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labels = ["前年の点と比べる", "平均へ寄せた見込みと比べる"]
    un = [flag["naive"]["flag_share_top_unchanged"] * 100, flag["adjusted"]["flag_share_top_unchanged"] * 100]
    rc = [flag["naive"]["recall_top"] * 100, flag["adjusted"]["recall_top"] * 100]
    xs = np.arange(2)
    ax.bar(xs - 0.2, un, 0.38, color=GRAY, label="本当は変わらない人のうち、拾われた割合")
    ax.bar(xs + 0.2, rc, 0.38, color=ORANGE, label="本当に下がった人のうち、拾われた割合")
    for xi, v in list(zip(xs - 0.2, un)) + list(zip(xs + 0.2, rc)):
        ax.text(xi, v + 1.2, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylim(0, 100); ax.set_ylabel("割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("前年の上位1割で「5点以上下がった」と拾った人（1割が本当に6点下がると置いた）")
    save(fig, "a940_flag.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
