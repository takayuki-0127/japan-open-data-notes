"""941 部署ごとの平均点の差は、人の差か評価者の差か？（架空のデータ）

架空の会社の10部署（A部〜J部）。部署ごとに評価者は1人（その部署の上司）。
人ごとの評価点 ＝ 本当の働きぶり（部署の差＋人の差）＋ 評価者の甘さ辛さ ＋ その年の振れ。
部署の平均点の差のうち、どれだけが人の差で、どれだけが評価者の差かを、作成者が置いた正解から数える。
評価者が全員で同じ「共通の事例」を採点して甘さ辛さを見積もり、部署の平均を直す方法も比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 941
SRC = "架空の会社の部署の評価点（作成者が乱数で作成、seed 941）"
rng = np.random.default_rng(SEED)

DEPTS = [f"{c}部" for c in "ABCDEFGHIJ"]
SIZES = np.array([12, 15, 18, 20, 22, 25, 28, 30, 35, 40])
BASE = {"sd_dept": 1.5, "sd_person": 6.0, "sd_rater": 3.0, "sd_noise": 4.0, "k_common": 0}
N_REP = 2000
KS = [0, 3, 5, 10, 20]


def make(rng, sd_dept=1.5, sd_person=6.0, sd_rater=3.0, sd_noise=4.0, k_common=0, **_):
    d = rng.normal(0, sd_dept, 10)
    L = rng.normal(0, sd_rater, 10)
    dept = np.repeat(np.arange(10), SIZES)
    u = rng.normal(0, sd_person, len(dept))
    e = rng.normal(0, sd_noise, len(dept))
    true = 60 + d[dept] + u
    score = true + L[dept] + e
    # 共通の事例：全員の評価者が同じ k 件を採点する（事例の本当の点は人と同じ散らばり）
    kmax = max(KS)
    c = 60 + rng.normal(0, sd_person, kmax)
    ce = rng.normal(0, sd_noise, (10, kmax))
    common = c[None, :] + L[:, None] + ce
    return {"dept": dept, "true": true, "score": score, "d": d, "L": L, "u": u, "e": e, "common": common}


def srank(a):
    """順位（連続の値なので同点は出ない）"""
    return np.argsort(np.argsort(a)).astype(float)


def spearman(a, b):
    return float(np.corrcoef(srank(a), srank(b))[0, 1])


def measure(w, ks=KS):
    dept = w["dept"]
    cnt = np.bincount(dept)
    m_obs = np.bincount(dept, w["score"]) / cnt
    m_true = np.bincount(dept, w["true"]) / cnt          # 部署の人の本当の平均
    part_people = m_true - 60
    part_rater = w["L"]
    part_noise = np.bincount(dept, w["e"]) / cnt
    out = {"var_obs": m_obs.var(ddof=1), "var_people": part_people.var(ddof=1),
           "var_rater": part_rater.var(ddof=1), "var_noise": part_noise.var(ddof=1),
           "range_obs": m_obs.max() - m_obs.min(), "range_true": m_true.max() - m_true.min()}
    for k in ks:
        if k == 0:
            adj = m_obs
        else:
            lh = w["common"][:, :k].mean(1)
            adj = m_obs - (lh - lh.mean())
        out[f"spearman_k{k}"] = spearman(adj, m_true)
        out[f"top_hit_k{k}"] = float(np.argmax(adj) == np.argmax(m_true))
        out[f"mae_k{k}"] = float(np.abs((adj - adj.mean()) - (m_true - m_true.mean())).mean())
    return out, m_obs, m_true, part_people, part_rater, part_noise


def summarize(rows):
    df = pd.DataFrame(rows)
    tot = df.var_people + df.var_rater + df.var_noise
    s = {"share_people": float((df.var_people / tot).mean()), "share_rater": float((df.var_rater / tot).mean()),
         "share_noise": float((df.var_noise / tot).mean()),
         "var_obs": float(df.var_obs.mean()), "range_obs": float(df.range_obs.mean()),
         "range_true": float(df.range_true.mean())}
    for k in KS:
        s[f"spearman_k{k}"] = float(df[f"spearman_k{k}"].mean())
        s[f"top_hit_k{k}"] = float(df[f"top_hit_k{k}"].mean())
        s[f"mae_k{k}"] = float(df[f"mae_k{k}"].mean())
    return {k: round(v, 3) for k, v in s.items()}, df


def formula_shares(sd_dept, sd_person, sd_rater, sd_noise):
    """部署の平均の散らばりの式：人の差＝sd_dept²＋sd_person²×平均(1/人数)、評価者＝sd_rater²、振れ＝sd_noise²×平均(1/人数)"""
    h = float(np.mean(1 / SIZES))
    p, r, n = sd_dept ** 2 + sd_person ** 2 * h, sd_rater ** 2, sd_noise ** 2 * h
    t = p + r + n
    return {"people": round(p / t, 3), "rater": round(r / t, 3), "noise": round(n / t, 3)}


def main():
    # 1) 例の1年（data に置く）
    w = make(rng, **BASE)
    df = pd.DataFrame({"person_id": np.arange(1, len(w["dept"]) + 1), "dept": [DEPTS[i] for i in w["dept"]],
                       "true": w["true"].round(3), "score": w["score"].round(3)})
    df.to_csv(DATA / "people_example.csv", index=False)
    pd.DataFrame(w["common"][:, :max(KS)].round(3), index=DEPTS,
                 columns=[f"case{j+1}" for j in range(max(KS))]).rename_axis("rater_dept").to_csv(DATA / "common_cases_example.csv")
    o, m_obs, m_true, pp, pr, pn = measure(w)
    lh = w["common"][:, :10].mean(1)
    ex_tab = pd.DataFrame({"部署": DEPTS, "人数": SIZES, "見かけの平均点": m_obs.round(2),
                           "人の本当の平均": m_true.round(2),
                           "全社の平均との差": (m_obs - m_obs.mean()).round(2),
                           "うち人の差": (pp - pp.mean()).round(2), "うち評価者の差": (pr - pr.mean()).round(2),
                           "うちその年の振れ": (pn - pn.mean()).round(2),
                           "共通の事例10件で見積もった甘さ": (lh - lh.mean()).round(2),
                           "直した平均点（10件）": (m_obs - (lh - lh.mean())).round(2)})
    ex_tab.to_csv(RES / "example_departments.csv", index=False)
    example = {"spearman_raw": round(o["spearman_k0"], 3), "spearman_k10": round(o["spearman_k10"], 3),
               "top_obs": DEPTS[int(np.argmax(m_obs))], "top_true": DEPTS[int(np.argmax(m_true))],
               "top_adj10": DEPTS[int(np.argmax(m_obs - (lh - lh.mean())))],
               "range_obs": round(float(m_obs.max() - m_obs.min()), 2),
               "range_true": round(float(m_true.max() - m_true.min()), 2)}

    # 2) 2,000回（基本の置き方）
    rows = [measure(make(np.random.default_rng(SEED * 1000 + i), **BASE))[0] for i in range(N_REP)]
    base, bdf = summarize(rows)
    bdf.to_csv(RES / "years_2000.csv", index=False, float_format="%.4f")
    base["formula"] = formula_shares(BASE["sd_dept"], BASE["sd_person"], BASE["sd_rater"], BASE["sd_noise"])
    base["spearman_k0_p10"] = round(float(bdf.spearman_k0.quantile(.1)), 3)
    base["spearman_k0_p90"] = round(float(bdf.spearman_k0.quantile(.9)), 3)
    k_tab = pd.DataFrame({"共通の事例の件数": KS,
                          "順位相関（人の本当の平均と）": [base[f"spearman_k{k}"] for k in KS],
                          "見かけの1位が本当の1位": [base[f"top_hit_k{k}"] for k in KS],
                          "平均のずれ（点）": [base[f"mae_k{k}"] for k in KS]})
    k_tab.to_csv(RES / "by_common_cases.csv", index=False)

    # 3) 確かめ：評価者の甘さ辛さの散らばりと、部署の本当の差の散らばりを変える（各1,000回）
    rob = []
    for i, sr in enumerate([0.0, 1.5, 3.0, 4.5]):
        for j, sdp in enumerate([0.0, 1.5, 3.0]):
            kw = dict(BASE); kw["sd_rater"] = sr; kw["sd_dept"] = sdp
            s, _ = summarize([measure(make(np.random.default_rng(SEED * 7 + i * 100000 + j * 10000 + r), **kw))[0]
                              for r in range(1000)])
            f = formula_shares(sdp, BASE["sd_person"], sr, BASE["sd_noise"])
            rob.append({"評価者の甘さ辛さ（標準偏差）": sr, "部署の本当の差（標準偏差）": sdp,
                        "評価者の分の割合": s["share_rater"], "人の差の割合": s["share_people"],
                        "その年の振れの割合": s["share_noise"], "式の評価者の分": f["rater"],
                        "順位相関_そのまま": s["spearman_k0"], "順位相関_共通の事例10件で直す": s["spearman_k10"],
                        "1位が当たる_そのまま": s["top_hit_k0"], "1位が当たる_共通の事例10件で直す": s["top_hit_k10"]})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # 4) 評価者だけの差と、人だけの差：見かけの平均点からは見分けられない
    #    部署の差と評価者の差の置き方を入れかえても、見かけの平均点の散らばりは同じになる
    swap = []
    for name, kw in [("評価者の差だけ（評価者3.35・部署0）", {"sd_rater": 3.354, "sd_dept": 0.0}),
                     ("部署の差だけ（評価者0・部署3.35）", {"sd_rater": 0.0, "sd_dept": 3.354})]:
        kk = dict(BASE); kk.update(kw)
        s, sdf = summarize([measure(make(np.random.default_rng(SEED * 11 + r), **kk))[0] for r in range(N_REP)])
        swap.append({"置き方": name, "見かけの平均点の散らばり（分散）": s["var_obs"],
                     "見かけの最大と最小の差": s["range_obs"], "人の本当の平均の最大と最小の差": s["range_true"],
                     "順位相関_そのまま": s["spearman_k0"], "順位相関_共通の事例10件で直す": s["spearman_k10"]})
    swap = pd.DataFrame(swap)
    swap.to_csv(RES / "rater_only_vs_dept_only.csv", index=False)

    out = {"settings": {**BASE, "departments": DEPTS, "sizes": SIZES.tolist(), "n_rep": N_REP, "common_cases": KS},
           "example_year": example, "base_2000": base, "by_common_cases": k_tab.to_dict("records"),
           "rater_only_vs_dept_only": swap.to_dict("records"), "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a941_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1年、部署ごとの「全社の平均との差」の中身（部署は名前の順）
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    xs = np.arange(10)
    parts = [("うち人の差", BLUE), ("うち評価者の差", ORANGE), ("うちその年の振れ", GRAY)]
    pos = np.zeros(10); neg = np.zeros(10)
    for col, c in parts:
        v = ex_tab[col].values
        bottom = np.where(v >= 0, pos, neg)
        ax.bar(xs, v, 0.62, bottom=bottom, color=c, label=col.replace("うち", ""))
        pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
    ax.scatter(xs, ex_tab["全社の平均との差"], color=INK, s=22, zorder=5, label="見かけの差（合計）")
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(xs); ax.set_xticklabels([f"{d}\n{n}人" for d, n in zip(DEPTS, SIZES)], fontsize=9)
    ax.set_ylabel("全社の平均点との差（点）")
    lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 2.6)
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center")
    ax.set_title("部署の平均点の差の中身（例の1年。部署は名前の順）")
    save(fig, "a941_parts.png", SRC)

    # 図2：共通の事例の件数と、部署の順位の当たり
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(KS, k_tab["順位相関（人の本当の平均と）"], color=BLUE, marker="o", label="順位相関（人の本当の平均と）")
    ax.plot(KS, k_tab["見かけの1位が本当の1位"], color=ORANGE, marker="o", label="1位の部署が本当の1位と同じ割合")
    for k, a, b in zip(KS, k_tab["順位相関（人の本当の平均と）"], k_tab["見かけの1位が本当の1位"]):
        ax.text(k, a + 0.03, f"{a:.2f}", ha="center", fontsize=8.5, color=BLUE)
        ax.text(k, b - 0.07, f"{b*100:.1f}%", ha="center", fontsize=8.5, color=ORANGE)
    ax.set_xticks(KS); ax.set_xlabel("評価者が全員で採点した共通の事例の件数（0＝直さない）")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("順位相関／割合（1＝100%）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("評価者の甘さ辛さを標準偏差3点と置くと、共通の事例で直すほど\n部署の順位が当たりやすくなった（2,000回の平均）")
    save(fig, "a941_common_cases.png", SRC)

    # 図3：評価者の分の割合（確かめの12通り）
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    piv = rob.pivot(index="評価者の甘さ辛さ（標準偏差）", columns="部署の本当の差（標準偏差）", values="評価者の分の割合")
    im = ax.imshow(piv.values * 100, cmap="Oranges", vmin=0, vmax=100, aspect="auto", origin="lower")
    for a in range(piv.shape[0]):
        for b in range(piv.shape[1]):
            v = piv.values[a, b] * 100
            ax.text(b, a, f"{v:.0f}%", ha="center", va="center", fontsize=10, color="white" if v > 55 else INK)
    ax.set_xticks(range(piv.shape[1])); ax.set_xticklabels([f"{v:g}" for v in piv.columns])
    ax.set_yticks(range(piv.shape[0])); ax.set_yticklabels([f"{v:g}" for v in piv.index])
    ax.set_xlabel("部署の本当の差（標準偏差、点）"); ax.set_ylabel("評価者の甘さ辛さ（標準偏差、点）")
    ax.set_title("部署の平均点の散らばりのうち、評価者の分の割合\n（人の差の標準偏差6点・振れ4点、各1,000回）")
    save(fig, "a941_share_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
