"""896 複数のサービスの手数料を差し引いた実入りを、どう比べるか？（架空のデータ）

架空の仲介サービスA・B・C（手数料の決まりは作成者が置いたもの）と、架空のフリーランスの人の1年分の案件。
同じ1年分の案件に3つの決まりを当てて実入り（契約額−手数料−振込の料金）の合計を出し、
これを「正しい比べ方」として、近道の比べ方がどれだけ同じ答えを出すかを数える。
どのサービスがよいか、手数料がいくらなら妥当かは扱わない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 896
SRC = "架空の仲介サービスの手数料の決まりと案件（作成者が乱数で作成、seed 896）"
SV = ["A", "B", "C"]
BASE = {"c_fixed": 3000, "b_scale": 1.0, "dur": 3.0}
METHODS = ["率だけで比べる", "最初の1か月で比べる", "平均の月で比べる"]


def make_jobs(rng, n, dur, rate_med=0.4, start_empty=False):
    """1年分の案件（person, client, month, amount）。取引先は毎月でたらめに増え、平均 dur か月続く"""
    r = np.exp(rng.normal(np.log(rate_med), 0.6, n))
    rows_p, rows_c, rows_s, rows_e = [], [], [], []
    cid = 0
    p = 1.0 / dur
    # 1月の時点で、前の年から続いている取引先（ずっと続けている人と置く。平均の数は1か月の増え方×(dur−1)）
    k0 = np.zeros(n, int) if start_empty else rng.poisson(r * (dur - 1))
    for m in range(0, 13):
        k = k0 if m == 0 else rng.poisson(r)
        tot = k.sum()
        per = np.repeat(np.arange(n), k)
        d = rng.geometric(p, tot)
        s = np.full(tot, max(m, 1))
        rows_p.append(per); rows_s.append(s); rows_e.append(np.minimum(s + d - 1, 12))
        rows_c.append(np.arange(cid, cid + tot)); cid += tot
    per, c, s, e = map(np.concatenate, (rows_p, rows_c, rows_s, rows_e))
    ln = e - s + 1
    per_r, c_r = np.repeat(per, ln), np.repeat(c, ln)
    month = np.concatenate([np.arange(a, b + 1) for a, b in zip(s, e)]) if len(s) else np.array([], int)
    amt = np.round(np.exp(rng.normal(np.log(30000), 0.6, len(month))), -3)
    amt = np.maximum(amt, 3000)
    return pd.DataFrame({"person": per_r, "client": c_r, "month": month, "amount": amt})


def tier_b(x, scale):
    t1, t2 = 100000 * scale, 500000 * scale
    return 0.20 * np.minimum(x, t1) + 0.10 * np.clip(x - t1, 0, t2 - t1) + 0.05 * np.maximum(x - t2, 0)


def fees(jobs, n, c_fixed, b_scale, months=range(1, 13)):
    """人ごとの契約額と、A・B・Cそれぞれの手数料の合計（決まりは作成者が置いたもの）"""
    full = jobs.sort_values(["person", "client", "month"])
    cum = full.groupby(["person", "client"]).amount.cumsum().values  # Bの累計は1年の初めから数える
    fb_all = tier_b(cum, b_scale) - tier_b(cum - full.amount.values, b_scale)
    sel = full.month.isin(list(months)).values
    j = full[sel]
    nm = len(list(months))
    gross = np.bincount(j.person, weights=j.amount, minlength=n)
    act = j.groupby(["person", "month"]).amount.sum().reset_index()
    n_pay = np.bincount(act.person, minlength=n)  # 契約額のあった月（その月に1回引き出す）
    fa = 0.15 * gross + 500 * n_pay
    fb = np.bincount(j.person, weights=fb_all[sel], minlength=n)
    fc = c_fixed * nm + 0.05 * gross + 300 * n_pay
    return gross, np.stack([fa, fb, fc], 1), n_pay


def compare(jobs, n, c_fixed, b_scale):
    gross, F, n_pay = fees(jobs, n, c_fixed, b_scale)
    net = gross[:, None] - F
    truth = net.argmax(1)
    active = gross > 0
    # 率だけ：固定の料金と振込を入れず、段階のある率は最初の段（20%）で読む → A15%・B20%・C5% でいつもC
    m1 = np.full(n, 2)
    # 最初の1か月：1月の案件だけに決まりを当てる（契約額0の人は比べられない＝-1）
    g1, F1, _ = fees(jobs, n, c_fixed, b_scale, months=[1])
    m2 = np.where(g1 > 0, (g1[:, None] - F1).argmax(1), -1)
    # 平均の月：年の契約額÷12 の案件が1社から毎月12か月続くとして計算
    gm = gross / 12
    fa = 0.15 * gross + 500 * 12
    fb = tier_b(gross, b_scale)
    fc = c_fixed * 12 + 0.05 * gross + 300 * 12
    m3 = (gross[:, None] - np.stack([fa, fb, fc], 1)).argmax(1)
    out = {"truth": truth, "m": [m1, m2, m3], "gross": gross, "net": net, "active": active, "n_pay": n_pay}
    return out


def summarize(o):
    a = o["active"]
    t = o["truth"][a]
    res = {"n_active": int(a.sum()), "truth_share": {SV[k]: float((t == k).mean()) for k in range(3)}}
    for name, m in zip(METHODS, o["m"]):
        mm = m[a]
        res[name] = {"match": float((mm == t).mean()), "not_comparable": float((mm < 0).mean()),
                     "match_among_comparable": float((mm == t)[mm >= 0].mean()),
                     "pick_share": {SV[k]: float((mm == k).mean()) for k in range(3)}}
        # 取り違えたときに、実入りの合計がいちばん多い決まりとの差（年の契約額に対する割合）
        wrong = (mm != t) & (mm >= 0)
        net = o["net"][a]
        gap = net[np.arange(len(t)), t] - net[np.arange(len(t)), np.where(mm >= 0, mm, 0)]
        rel = gap / o["gross"][a]
        res[name]["gap_rel_median_when_wrong"] = float(np.median(rel[wrong])) if wrong.any() else 0.0
    return res


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    N = 5000
    jobs = make_jobs(rng, N, BASE["dur"])
    o = compare(jobs, N, BASE["c_fixed"], BASE["b_scale"])
    base = summarize(o)

    # 年の契約額の区切りごとの、実入りの割合（実入り÷契約額）と、合計がいちばん多くなる決まり
    a = o["active"]
    g = o["gross"][a]
    netr = o["net"][a] / g[:, None]
    bins = [0, 150000, 300000, 600000, 1200000, np.inf]
    labels = ["15万円未満", "15〜30万円", "30〜60万円", "60〜120万円", "120万円以上"]
    cut = pd.cut(g, bins, labels=labels, right=False)
    by_g = []
    for lb in labels:
        s = cut == lb
        row = {"gross_band": lb, "people": int(s.sum())}
        for k in range(3):
            row[f"net_ratio_{SV[k]}_median"] = float(np.median(netr[s, k]))
            row[f"best_share_{SV[k]}"] = float((o["truth"][a][s] == k).mean())
        for name, m in zip(METHODS, o["m"]):
            row[f"match_{name}"] = float((m[a][s] == o["truth"][a][s]).mean())
        by_g.append(row)
    by_g = pd.DataFrame(by_g)
    by_g.round(4).to_csv(RES / "by_gross_band.csv", index=False)

    # 実入りの割合：合計で割る と 月ごとの割合の平均（C）
    gm_, Fm_ = [], []
    for m in range(1, 13):
        gg, FF, _ = fees(jobs, N, BASE["c_fixed"], BASE["b_scale"], months=[m])
        gm_.append(gg); Fm_.append(FF)
    gm_ = np.stack(gm_, 1); Fm_ = np.stack(Fm_, 2)  # (N,12), (N,3,12)
    ratio_cmp = {}
    for k in range(3):
        tot = (o["gross"][a] - o["net"][a][:, k]) / o["gross"][a]
        with np.errstate(invalid="ignore", divide="ignore"):
            mr = Fm_[a, k, :] / gm_[a]
        mr = np.where(gm_[a] > 0, mr, np.nan)
        ratio_cmp[SV[k]] = {"fee_ratio_total_median": float(np.median(tot)),
                            "fee_ratio_monthly_mean_median": float(np.median(np.nanmean(mr, 1))),
                            "share_monthly_mean_lower": float((np.nanmean(mr, 1) < tot - 1e-9).mean())}
    # 契約額0の月も固定の料金がかかるC：契約額のある月だけで割合を出すと低く見える
    pd.DataFrame(ratio_cmp).T.round(4).to_csv(RES / "fee_ratio_total_vs_monthly.csv")

    # 実際に使った順で比べる：前半6か月をA、後半6か月をCで通したとして、月あたりの実入りを比べる
    def half_compare(jb, n, start_empty):
        g1, F1, _ = fees(jb, n, BASE["c_fixed"], BASE["b_scale"], months=range(1, 7))
        g2, F2, _ = fees(jb, n, BASE["c_fixed"], BASE["b_scale"], months=range(7, 13))
        gT, FT, _ = fees(jb, n, BASE["c_fixed"], BASE["b_scale"])
        act = (g1 > 0) & (g2 > 0)
        seen_c = (g2 - F2[:, 2]) > (g1 - F1[:, 0])      # 後半のCのほうが実入りが多く見えた
        true_c = (gT - FT[:, 2]) > (gT - FT[:, 0])      # 同じ1年分の案件ではCのほうが多い
        return {"start_empty": start_empty, "people": int(act.sum()),
                "agree": float((seen_c == true_c)[act].mean()),
                "seen_c_better": float(seen_c[act].mean()), "true_c_better": float(true_c[act].mean()),
                "gross_h2_over_h1_median": float(np.median(g2[act] / g1[act]))}
    hc = [half_compare(jobs, N, False)]
    jobs_new = make_jobs(np.random.default_rng(SEED * 3), N, BASE["dur"], start_empty=True)
    hc.append(half_compare(jobs_new, N, True))
    pd.DataFrame(hc).round(4).to_csv(RES / "half_year_compare.csv", index=False)

    # 確かめ：Cの月の固定の料金×Bの段の区切り×取引先の続く長さ（27通り）
    grid = []
    k = 0
    for cf in [1500, 3000, 6000]:
        for bs in [0.5, 1.0, 2.0]:
            for du in [1.5, 3.0, 6.0]:
                jb = make_jobs(np.random.default_rng(SEED * 100 + k), 2000, du)
                s = summarize(compare(jb, 2000, cf, bs))
                grid.append({"c_fixed": cf, "b_scale": bs, "dur": du,
                             **{f"truth_{v}": s["truth_share"][v] for v in SV},
                             **{f"match_{nm}": s[nm]["match"] for nm in METHODS},
                             "m2_not_comparable": s[METHODS[1]]["not_comparable"]})
                k += 1
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)

    # データ：1人分の案件（年の契約額が真ん中あたりの人）
    med_p = int(np.argsort(o["gross"])[int(N * 0.5)])
    d = jobs[jobs.person == med_p].sort_values(["month", "client"]).copy()
    d["client"] = pd.factorize(d.client)[0] + 1
    d[["month", "client", "amount"]].astype(int).to_csv(DATA / "one_person_jobs.csv", index=False)
    one_g, one_F, one_np = fees(jobs[jobs.person == med_p].assign(person=0), 1, BASE["c_fixed"], BASE["b_scale"])

    def r4(x):
        if isinstance(x, float):
            return round(x, 4)
        if isinstance(x, dict):
            return {kk: r4(v) for kk, v in x.items()}
        if isinstance(x, list):
            return [r4(v) for v in x]
        return x
    out = {"rules": {"A": "契約額の15%、契約額のあった月ごとに振込500円",
                     "B": "同じ取引先との累計契約額のうち10万円までの部分20%、10万〜50万円の部分10%、50万円を超える部分5%、振込0円",
                     "C": "毎月3,000円（契約額のない月も）＋契約額の5%、契約額のあった月ごとに振込300円"},
           "base_params": BASE, "n_people": N, "base": base,
           "gross_quantiles": {q: float(np.quantile(o["gross"][a], q)) for q in [0.1, 0.25, 0.5, 0.75, 0.9]},
           "share_zero_gross": float((~a).mean()),
           "months_with_pay_median": float(np.median(o["n_pay"][a])),
           "by_gross_band": by_g.to_dict("records"), "fee_ratio_total_vs_monthly": ratio_cmp,
           "half_year_compare": hc,
           "grid_ranges": {c: [float(grid[c].min()), float(grid[c].max())] for c in
                           [f"match_{nm}" for nm in METHODS] + [f"truth_{v}" for v in SV]},
           "one_person": {"gross": float(one_g[0]), "fee_A": float(one_F[0, 0]), "fee_B": float(one_F[0, 1]),
                          "fee_C": float(one_F[0, 2]), "months_with_pay": int(one_np[0]),
                          "clients": int(d.client.max())}}
    out = r4(out)
    json.dump(out, open(RES / "a896_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：年の契約額と、実入りの割合（人ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for kk, c in zip(range(3), [GRAY, BLUE, ORANGE]):
        ax.scatter(g, netr[:, kk] * 100, s=5, color=c, alpha=.35, lw=0, label=f"決まり{SV[kk]}")
    ax.set_xscale("log"); ax.set_ylim(-40, 100)
    ax.set_xticks([3e4, 1e5, 3e5, 1e6, 3e6]); ax.set_xticklabels(["3万", "10万", "30万", "100万", "300万"])
    ax.set_xlabel("1年の契約額（円、対数の目盛り）"); ax.set_ylabel("実入り÷契約額（%）")
    lg = ax.legend(frameon=False, fontsize=9, loc="lower right", markerscale=3)
    ax.text(0.01, 0.02, "−40%より下は図の外", transform=ax.transAxes, fontsize=8, color=GRAY)
    ax.set_title("同じ案件でも、実入りの割合の順は1年の契約額で入れかわる")
    save(fig, "a896_net_ratio.png", SRC)

    # 図2：近道の比べ方が、同じ案件の合計で比べた答えと一致した割合（契約額の区切りごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(len(labels)); w = 0.26
    for kk, (nm, c) in enumerate(zip(METHODS, [GRAY, BLUE, ORANGE])):
        ax.bar(x + (kk - 1) * w, by_g[f"match_{nm}"] * 100, w, color=c, label=nm)
        for i, v in enumerate(by_g[f"match_{nm}"] * 100):
            ax.text(i + (kk - 1) * w, v + 1.2, f"{v:.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("1年の契約額"); ax.set_ylabel("同じ答えになった人の割合（%）"); ax.set_ylim(0, 115)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    ax.set_title("近道の比べ方は、同じ案件の1年分で比べた答えとどれだけ合うか")
    save(fig, "a896_match_by_band.png", SRC)

    # 図3：置き方を変えたときの幅
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bm = [base[nm]["match"] * 100 for nm in METHODS]
    for i, nm in enumerate(METHODS):
        lo, hi = grid[f"match_{nm}"].min() * 100, grid[f"match_{nm}"].max() * 100
        ax.plot([lo, hi], [i, i], color=LIGHT, lw=8, solid_capstyle="butt")
        ax.plot(bm[i], i, "o", color=BLUE)
        ax.text(hi + 1.5, i, f"{lo:.1f}〜{hi:.1f}%（基本 {bm[i]:.1f}%）", va="center", fontsize=9)
    ax.set_yticks(range(3)); ax.set_yticklabels(METHODS); ax.invert_yaxis()
    ax.set_xlim(0, 135); ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("同じ案件の1年分で比べた答えと一致した人の割合（%）")
    ax.set_title("置き方27通りの幅")
    save(fig, "a896_sensitivity.png", SRC, y=-0.05)

    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])
    print(by_g.round(3).to_string())
    print(grid.round(3).to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
