"""1211 1回の調査で見つからなかった種は、その場所にいないと言えるのか？（架空のデータ）

架空の池300か所。種Aがいる池（4割）と、いる池での数（作成者が置いた）、1回探したときに1匹を見つける確率と、
日ごとの見つけやすさの上下（天気など、作成者が置いた）から、探した回数ごとに「見つからなかった池」のうち本当はいた割合を数える。
探す日を分けるか、同じ日にまとめて探すか、見つける確率を平均で1つに置いた式とどれだけ違うかも比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1211
SRC = "架空の池の種A（作成者が乱数で作成、seed 1211）"
PONDS, REPS, KMAX = 300, 200, 20
BASE = dict(psi=0.4, r=0.08, day_sd=0.6, mean_n=6.0)


def sim(rng, psi, r, day_sd, mean_n, reps=REPS, ponds=PONDS, kmax=KMAX):
    shape = (reps, ponds)
    present = rng.random(shape) < psi
    lam = rng.gamma(1.0, mean_n - 1, size=shape)          # 池ごとの数の目安（小さな池が多い）
    n = np.where(present, 1 + rng.poisson(lam), 0)
    # 日ごとの見つけやすさ（平均1になるよう置いた倍率）
    f = np.exp(rng.normal(-day_sd ** 2 / 2, day_sd, size=(reps, ponds, kmax)))
    rr = np.minimum(r * f, 1.0)
    p_sep = 1 - (1 - rr) ** n[..., None]                   # 別々の日に探す：回ごとの見つける確率
    p_same = 1 - (1 - rr[..., :1]) ** n[..., None]          # 同じ日にまとめて探す：日の倍率を共有
    u = rng.random((reps, ponds, kmax))
    det_sep = u < p_sep
    det_same = u < p_same
    found_sep = np.cumsum(det_sep, axis=2) > 0
    found_same = np.cumsum(det_same, axis=2) > 0
    pbar = float((1 - (1 - r) ** n[present]).mean()) if present.any() else 0.0   # いる池の、1回の見つける確率（日の上下を除いた平均）
    return dict(present=present, n=n, found_sep=found_sep, found_same=found_same, pbar=pbar)


def p_present_given_missed(d, key):
    pr = d["present"][..., None]
    miss = ~d[key]
    return (miss & pr).sum((0, 1)) / np.maximum(miss.sum((0, 1)), 1)


def formula(psi, p, k):
    a = psi * (1 - p) ** k
    return a / (a + 1 - psi)


def need(curve, thr=0.05):
    idx = np.where(np.asarray(curve) <= thr)[0]
    return int(idx[0] + 1) if idx.size else None


def main():
    rng = np.random.default_rng(SEED)
    d = sim(rng, **BASE)
    ks = np.arange(1, KMAX + 1)
    sep = p_present_given_missed(d, "found_sep")
    same = p_present_given_missed(d, "found_same")
    form = formula(BASE["psi"], d["pbar"], ks)
    curve = pd.DataFrame({"visits": ks, "present_among_not_found_sep_days_pct": np.round(sep * 100, 2),
                          "present_among_not_found_same_day_pct": np.round(same * 100, 2),
                          "formula_one_p_pct": np.round(form * 100, 2),
                          "found_share_sep_days_pct": np.round(d["found_sep"].mean((0, 1)) * 100, 2)})
    curve.to_csv(RES / "base_by_visits.csv", index=False)

    pr = d["present"]
    f1 = d["found_sep"][..., 0]
    n = d["n"]
    n_found = n[pr & f1]
    n_missed = n[pr & ~f1]
    f3 = d["found_sep"][..., 2]
    first = dict(
        true_present_share_pct=round(float(pr.mean() * 100), 2),
        found_share_1visit_pct=round(float(f1.mean() * 100), 2),
        found_share_3visits_pct=round(float(f3.mean() * 100), 2),
        missed_among_present_1visit_pct=round(float((~f1[pr]).mean() * 100), 2),
        present_among_not_found_1visit_pct=round(float(sep[0] * 100), 2),
        median_n_present_ponds=float(np.median(n[pr])), mean_n_present_ponds=round(float(n[pr].mean()), 2),
        median_n_found_ponds=float(np.median(n_found)), median_n_missed_ponds=float(np.median(n_missed)),
        share_n_le3_found_pct=round(float((n_found <= 3).mean() * 100), 2),
        share_n_le3_missed_pct=round(float((n_missed <= 3).mean() * 100), 2),
        mean_p_one_visit=round(d["pbar"], 4),
        visits_needed_5pct_sep_days=need(sep), visits_needed_5pct_same_day=need(same),
        visits_needed_5pct_formula=need(form),
    )

    # 例の1回分
    ex = pd.DataFrame({"pond": np.arange(1, PONDS + 1), "present": d["present"][0].astype(int), "n": d["n"][0]})
    for k in [1, 3, 5]:
        ex[f"found_by_visit{k}_sep_days"] = d["found_sep"][0, :, k - 1].astype(int)
        ex[f"found_by_visit{k}_same_day"] = d["found_same"][0, :, k - 1].astype(int)
    ex.to_csv(DATA / "example_ponds.csv", index=False)
    e0 = ex
    example = dict(present=int(e0.present.sum()), found_1=int(e0.found_by_visit1_sep_days.sum()),
                   not_found_1=int((e0.found_by_visit1_sep_days == 0).sum()),
                   present_among_not_found_1=int(((e0.found_by_visit1_sep_days == 0) & (e0.present == 1)).sum()),
                   found_3_sep=int(e0.found_by_visit3_sep_days.sum()), found_3_same=int(e0.found_by_visit3_same_day.sum()))

    # 確かめ：いる池の割合 × 1匹を見つける確率 × 日ごとの上下（18通り、各100回）
    rows = []
    for psi in [0.1, 0.4, 0.7]:
        for r in [0.04, 0.08, 0.16]:
            for ds in [0.0, 0.6]:
                g = sim(rng, psi, r, ds, BASE["mean_n"], reps=100)
                s1 = p_present_given_missed(g, "found_sep")
                s2 = p_present_given_missed(g, "found_same")
                fm = formula(psi, g["pbar"], ks)
                rows.append(dict(present_share=psi, r_one=r, day_sd=ds, mean_p_one_visit=round(g["pbar"], 4),
                                 present_among_nf_1_pct=round(float(s1[0] * 100), 2),
                                 present_among_nf_3_sep_pct=round(float(s1[2] * 100), 2),
                                 present_among_nf_3_same_pct=round(float(s2[2] * 100), 2),
                                 formula_3_pct=round(float(fm[2] * 100), 2),
                                 need_sep=need(s1), need_same=need(s2), need_formula=need(fm)))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    gn = grid.dropna(subset=["need_sep", "need_formula"])
    out = dict(setting=BASE, ponds=PONDS, reps=REPS, base=first, example=example,
               curve_at=dict((f"visits{k}", curve.iloc[k - 1].to_dict()) for k in [1, 2, 3, 5, 8, 10, 15, 20]),
               grid_summary=dict(
                   present_among_nf_1_range=[float(grid.present_among_nf_1_pct.min()), float(grid.present_among_nf_1_pct.max())],
                   present_among_nf_3_sep_range=[float(grid.present_among_nf_3_sep_pct.min()),
                                                 float(grid.present_among_nf_3_sep_pct.max())],
                   need_sep_range=[float(grid.need_sep.min()), float(grid.need_sep.max())],
                   need_sep_missing_over20=int(grid.need_sep.isna().sum()),
                   sim_above_formula_at3=int((grid.present_among_nf_3_sep_pct > grid.formula_3_pct).sum()),
                   need_sep_minus_formula_range=[float((gn.need_sep - gn.need_formula).min()),
                                                 float((gn.need_sep - gn.need_formula).max())],
                   same_above_sep_at3_dayvar=int((grid[grid.day_sd > 0].present_among_nf_3_same_pct >
                                                  grid[grid.day_sd > 0].present_among_nf_3_sep_pct).sum()),
               ))
    json.dump(out, open(RES / "a1211_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：探した回数と、見つからなかった池のうち本当はいた割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    kk = curve.visits[:12]
    ax.plot(kk, curve.present_among_not_found_sep_days_pct[:12], marker="o", color=BLUE, label="別々の日に探す")
    ax.plot(kk, curve.present_among_not_found_same_day_pct[:12], marker="s", color=ORANGE, label="同じ日にまとめて探す")
    ax.plot(kk, curve.formula_one_p_pct[:12], ls="--", color=GRAY, label="見つける確率を平均の1つに置いた式")
    ax.axhline(5, color=INK, lw=0.6, ls=":")
    ax.text(1, 5.6, "5%", ha="left", fontsize=8.5)
    ax.set_ylim(0, 40); ax.set_xticks(kk)
    ax.set_xlabel("探した回数"); ax.set_ylabel("見つからなかった池のうち、\n本当は種Aがいた割合（%）", linespacing=1.6)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("見つからなかった池にも、種Aはいた（いる池4割、200回の平均）")
    save(fig, "a1211_curve.png", SRC)

    # 図2：見つかった池と見逃した池の数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(1, 31)
    hf = np.bincount(np.minimum(n_found, 30), minlength=31)[1:31] / n_found.size * 100
    hm = np.bincount(np.minimum(n_missed, 30), minlength=31)[1:31] / n_missed.size * 100
    ax.bar(bins - 0.2, hf, width=0.4, color=BLUE, label="1回目で見つかった池")
    ax.bar(bins + 0.2, hm, width=0.4, color=ORANGE, label="いたのに1回目で見つからなかった池")
    ax.set_xlabel("池にいた種Aの数（30以上は30にまとめた）"); ax.set_ylabel("池の割合（%）")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("見逃した池の多くは、数の少ない池だった")
    save(fig, "a1211_n.png", SRC)

    # 図3：18通りの、5%を下回るのに要る回数
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    xx = np.arange(len(grid))
    ns = grid.need_sep.fillna(KMAX + 1); nf = grid.need_formula.fillna(KMAX + 1)
    ax.bar(xx - 0.2, ns, width=0.4, color=BLUE, label="別々の日に探す（数えた値）")
    ax.bar(xx + 0.2, nf, width=0.4, color=GRAY, label="見つける確率を平均の1つに置いた式")
    ax.set_ylim(0, KMAX + 6); ax.set_xticks([]); ax.set_yticks(range(0, KMAX + 2, 5))
    ax.set_xlabel("置き方の18通り（いる池の割合 × 1匹を見つける確率 × 日ごとの上下）\n21は20回でも届かなかったもの")
    ax.set_ylabel("「見つからなかった池にいた割合」が\n5%以下になる探す回数", linespacing=1.6)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("要る回数は置き方で大きく変わり、\n見つける確率を平均の1つに置いた式と同じか多かった（各100回）")
    save(fig, "a1211_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(grid.to_string())


if __name__ == "__main__":
    main()
