"""03 分析：ファンネルプロット、順位の入れ替わり、経験ベイズによる縮小、シミュレーション。

A ファンネルプロット（2023年度の大腸がん検診）：全国の率のまわりに、偶然だけで出る範囲（95%・99.8%）を引く
B 年度ごとの順位：1位・上位50・下位50に、どの規模の町が入るか。翌年も残るか
C 経験ベイズ（ベータ二項）：年度ごとに全国の分布を推定し、各団体の率を全国寄りに縮める
D 縮めた値は翌年の値をよく当てるか
E シミュレーション：全団体の本当の率が同じでも、1位はどの規模の町になるか
F 死亡（標準化死亡比、ポアソン・ガンマ）でも同じことをする
G 頑健性
"""
import json
import numpy as np
import pandas as pd
from scipy import stats, optimize, special
from common import DATA, RES, SEED, ROOT

rng = np.random.default_rng(SEED)
YEARS = [2021, 2022, 2023, 2024]
SIZES = ["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]


# ---------- 経験ベイズ（ベータ二項） ----------
def fit_betabinom_ml(y, n):
    """y ~ BetaBinom(n, a, b) を最尤で推定。a=mu*k, b=(1-mu)*k"""
    y = np.asarray(y, float); n = np.asarray(n, float)
    mu0 = y.sum() / n.sum()

    def nll(par):
        mu = special.expit(par[0]); k = np.exp(par[1])
        a, b = mu * k, (1 - mu) * k
        ll = (special.gammaln(n + 1) - special.gammaln(y + 1) - special.gammaln(n - y + 1)
              + special.betaln(y + a, n - y + b) - special.betaln(a, b))
        return -ll.sum()

    r = optimize.minimize(nll, [special.logit(mu0), np.log(50.0)], method="Nelder-Mead",
                          options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 4000})
    mu = special.expit(r.x[0]); k = np.exp(r.x[1])
    return mu, k


def fit_betabinom_mom(y, n):
    """モーメント法（重み付き）"""
    y = np.asarray(y, float); n = np.asarray(n, float)
    p = y / n
    mu = y.sum() / n.sum()
    # 団体の間の分散 tau2 = 観測の分散 − 二項の分散
    w = n / n.sum()
    s2 = np.sum(w * (p - mu) ** 2)
    binvar = mu * (1 - mu) * np.sum(w / n)
    tau2 = max(s2 - binvar, 1e-8)
    k = mu * (1 - mu) / tau2 - 1
    return mu, max(k, 1.0)


def eb_rate(y, n, mu, k):
    return (y + mu * k) / (n + k)


# ---------- 経験ベイズ（ポアソン・ガンマ） ----------
def fit_poisgamma_ml(O, E):
    """O ~ NegBin with mean E*theta, theta ~ Gamma(shape=s, rate=s/m)"""
    O = np.asarray(O, float); E = np.asarray(E, float)

    def nll(par):
        m = np.exp(par[0]); s = np.exp(par[1])
        r = s; p = s / (s + E * m)
        ll = (special.gammaln(O + r) - special.gammaln(r) - special.gammaln(O + 1)
              + r * np.log(p) + O * np.log1p(-p))
        return -ll.sum()

    r = optimize.minimize(nll, [np.log(O.sum() / E.sum()), np.log(50.0)], method="Nelder-Mead",
                          options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 4000})
    return np.exp(r.x[0]), np.exp(r.x[1])


def eb_smr(O, E, m, s):
    return 100 * (O + s) / (E + s / m)


def topk_share(df, col, k, size_col="size", largest=True):
    d = df.sort_values(col, ascending=not largest).head(k)
    return d[size_col].value_counts().reindex(d[size_col].cat.categories if hasattr(d[size_col], "cat") else None).fillna(0).astype(int).to_dict()


def size_comp(df, col, k, largest, cats):
    d = df.sort_values(col, ascending=not largest).head(k)
    return {c: int((d["size"] == c).sum()) for c in cats}


def main():
    s = pd.read_csv(DATA / "screening.csv", dtype={"code": str})
    s["size"] = pd.Categorical(s["size"], SIZES, ordered=True)
    out = {}

    # ===== C 経験ベイズ（各年度、大腸がん） =====
    priors = {}
    for yr in YEARS:
        d = s[s.year == yr]
        mu, k = fit_betabinom_ml(d.y_colon, d.n_colon)
        mu2, k2 = fit_betabinom_mom(d.y_colon, d.n_colon)
        priors[yr] = {"mu_ml": mu, "k_ml": k, "mu_mom": mu2, "k_mom": k2,
                      "sd_between_ml": float(np.sqrt(mu * (1 - mu) / (k + 1)))}
        idx = s.year == yr
        s.loc[idx, "p_raw"] = s.loc[idx, "y_colon"] / s.loc[idx, "n_colon"]
        s.loc[idx, "p_eb"] = eb_rate(s.loc[idx, "y_colon"], s.loc[idx, "n_colon"], mu, k)
        s.loc[idx, "w_raw"] = s.loc[idx, "n_colon"] / (s.loc[idx, "n_colon"] + k)
        s.loc[idx, "p_eb_mom"] = eb_rate(s.loc[idx, "y_colon"], s.loc[idx, "n_colon"], mu2, k2)
        # 都道府県ごとの平均を事前の中心に、ばらつきは全国共通
        pm = d.groupby("pref").apply(lambda g: g.y_colon.sum() / g.n_colon.sum())
        mu_p = s.loc[idx, "pref"].map(pm)
        # 都道府県の中のばらつきで k を推定し直す（モーメント法）
        dd = d.assign(mu_p=d.pref.map(pm))
        w = dd.n_colon / dd.n_colon.sum()
        s2 = np.sum(w * (dd.y_colon / dd.n_colon - dd.mu_p) ** 2)
        binv = np.sum(w * dd.mu_p * (1 - dd.mu_p) / dd.n_colon)
        tau2 = max(s2 - binv, 1e-8)
        kp = float(np.average(dd.mu_p * (1 - dd.mu_p), weights=w) / tau2 - 1)
        priors[yr]["k_pref"] = kp
        s.loc[idx, "p_eb_pref"] = (s.loc[idx, "y_colon"] + mu_p * kp) / (s.loc[idx, "n_colon"] + kp)
        # 肺がん
        dl = d.dropna(subset=["n_lung", "y_lung"])
        mul, kl = fit_betabinom_ml(dl.y_lung, dl.n_lung)
        priors[yr]["mu_lung"] = mul; priors[yr]["k_lung"] = kl
        s.loc[idx, "pl_raw"] = s.loc[idx, "y_lung"] / s.loc[idx, "n_lung"]
        s.loc[idx, "pl_eb"] = eb_rate(s.loc[idx, "y_lung"], s.loc[idx, "n_lung"], mul, kl)
    out["priors"] = priors
    # 縮める重み（生の率にかける重み）の規模別の中央値（2023年度）
    d23 = s[s.year == 2023]
    out["weight_raw_by_size_2023"] = d23.groupby("size", observed=True)["w_raw"].median().round(3).to_dict()
    out["shift_by_size_2023_pt"] = (d23.assign(sh=(d23.p_eb - d23.p_raw).abs() * 100)
                                    .groupby("size", observed=True)["sh"].median().round(2).to_dict())

    # ===== A ファンネル（2023年度） =====
    p0 = d23.y_colon.sum() / d23.n_colon.sum()
    se = np.sqrt(p0 * (1 - p0) / d23.n_colon)
    z = (d23.p_raw - p0) / se
    phi = float(np.sum(z ** 2) / (len(d23) - 1))
    fun = d23.assign(z=z, out95=np.abs(z) > 1.96, out998=np.abs(z) > 3.09)
    out["funnel_2023"] = {
        "p0": float(p0), "n_units": int(len(d23)),
        "share_out95": float(fun.out95.mean()), "share_out998": float(fun.out998.mean()),
        "overdispersion_phi": phi,
        "share_out998_phi_adjusted": float((np.abs(z) / np.sqrt(phi) > 3.09).mean()),
        "share_out998_by_size": fun.groupby("size", observed=True)["out998"].mean().round(3).to_dict(),
        "spread_raw_by_size_sd_pt": d23.groupby("size", observed=True)["p_raw"].std().mul(100).round(2).to_dict(),
        "spread_eb_by_size_sd_pt": d23.groupby("size", observed=True)["p_eb"].std().mul(100).round(2).to_dict(),
    }
    fun[["code", "year", "n_colon", "y_colon", "p_raw", "p_eb", "z", "size"]].to_csv(RES / "_funnel_2023.csv", index=False)

    # ===== B 順位：1位・上位・下位の規模 =====
    rows = []
    top1 = []
    for yr in YEARS:
        d = s[s.year == yr]
        for col, lab in (("p_raw", "生の率"), ("p_eb", "経験ベイズ")):
            for k in (10, 50):
                for largest, side in ((True, "上位"), (False, "下位")):
                    comp = size_comp(d, col, k, largest, SIZES)
                    rows.append({"year": yr, "value": lab, "side": side, "k": k, **comp})
            t1 = d.sort_values(col, ascending=False).iloc[0]
            b1 = d.sort_values(col, ascending=True).iloc[0]
            top1.append({"year": yr, "value": lab, "top1_code": t1.code, "top1_n": int(t1.n_colon),
                         "top1_size": t1["size"], "top1_rate": round(float(t1[col]) * 100, 1),
                         "bottom1_n": int(b1.n_colon), "bottom1_size": b1["size"]})
    comp = pd.DataFrame(rows)
    comp.to_csv(RES / "topk_size_composition.csv", index=False)
    top1 = pd.DataFrame(top1)
    top1.drop(columns=["top1_code"]).to_csv(RES / "top1_by_year.csv", index=False)
    out["top1"] = {
        "distinct_top1_raw": int(top1[top1.value == "生の率"].top1_code.nunique()),
        "distinct_top1_eb": int(top1[top1.value == "経験ベイズ"].top1_code.nunique()),
        "top1_raw_sizes": top1[top1.value == "生の率"].top1_size.tolist(),
        "top1_eb_sizes": top1[top1.value == "経験ベイズ"].top1_size.tolist(),
        "top1_raw_n": top1[top1.value == "生の率"].top1_n.tolist(),
        "top1_eb_n": top1[top1.value == "経験ベイズ"].top1_n.tolist(),
    }
    share_small = s.drop_duplicates("code")["size"].value_counts(normalize=True).reindex(SIZES).round(3).to_dict()
    out["share_units_by_size"] = share_small
    avg = comp.groupby(["value", "side", "k"])[SIZES].mean().round(1)
    out["topk_avg_composition"] = {f"{v}|{sd}|{k}": avg.loc[(v, sd, k)].to_dict() for v, sd, k in avg.index}

    # 翌年も残る割合
    wide_raw = s.pivot(index="code", columns="year", values="p_raw")
    wide_eb = s.pivot(index="code", columns="year", values="p_eb")
    size_of = s.drop_duplicates("code").set_index("code")["size"]

    def retention(w, k, largest):
        r = []
        for a, b in zip(YEARS[:-1], YEARS[1:]):
            ta = set(w[a].sort_values(ascending=not largest).head(k).index)
            tb = set(w[b].sort_values(ascending=not largest).head(k).index)
            r.append(len(ta & tb) / k)
        return float(np.mean(r))

    ret = {}
    for k in (1, 10, 50):
        for largest, side in ((True, "上位"), (False, "下位")):
            ret[f"{side}{k}"] = {"生の率": retention(wide_raw, k, largest), "経験ベイズ": retention(wide_eb, k, largest)}
    out["retention_next_year"] = ret

    # 年度の間の順位相関（全体・規模別）
    def sp(w, codes=None):
        ww = w if codes is None else w.loc[codes]
        return float(np.mean([stats.spearmanr(ww[a], ww[b]).statistic for a, b in zip(YEARS[:-1], YEARS[1:])]))
    out["spearman_next_year"] = {"生の率": sp(wide_raw), "経験ベイズ": sp(wide_eb)}
    by = {}
    for c in SIZES:
        codes = size_of[size_of == c].index
        by[c] = {"生の率": round(sp(wide_raw, codes), 3), "経験ベイズ": round(sp(wide_eb, codes), 3)}
    out["spearman_by_size"] = by

    # 4年間の順位の幅（中央値、規模別）
    rk_raw = wide_raw.rank(ascending=False)
    rk_eb = wide_eb.rank(ascending=False)
    rng_raw = (rk_raw.max(axis=1) - rk_raw.min(axis=1)).rename("raw")
    rng_eb = (rk_eb.max(axis=1) - rk_eb.min(axis=1)).rename("eb")
    rr = pd.concat([rng_raw, rng_eb, size_of], axis=1)
    out["rank_range_median_by_size"] = rr.groupby("size", observed=True)[["raw", "eb"]].median().round(0).to_dict()
    rr.reset_index(drop=True).to_csv(RES / "_rank_range.csv", index=False)

    # ===== D 翌年の値を当てる力 =====
    pred = []
    for a, b in zip(YEARS[:-1], YEARS[1:]):
        x = s[s.year == a].set_index("code"); yv = s[s.year == b].set_index("code")
        j = x.join(yv[["p_raw"]].rename(columns={"p_raw": "next"}))
        for col in ("p_raw", "p_eb", "p_eb_pref"):
            e = (j[col] - j["next"]) ** 2
            for c in SIZES + ["全体"]:
                sel = j["size"] == c if c != "全体" else slice(None)
                pred.append({"from": a, "pred": col, "size": c, "mse": float(e[sel].mean())})
    pred = pd.DataFrame(pred)
    pm = pred.groupby(["pred", "size"]).mse.mean().unstack(0)
    imp = (1 - pm["p_eb"] / pm["p_raw"]).round(3)
    imp_p = (1 - pm["p_eb_pref"] / pm["p_raw"]).round(3)
    out["next_year_mse_improvement"] = {"全国の事前": imp.to_dict(), "都道府県の事前": imp_p.to_dict()}
    pred.to_csv(RES / "next_year_prediction.csv", index=False)

    # ===== E シミュレーション：本当の率が全団体で同じ =====
    nsim = 2000
    d = s[s.year == 2023]
    n = d.n_colon.values.astype(int)
    sizes = d["size"].astype(str).values
    top1_sizes = []
    top50 = np.zeros(len(SIZES))
    bot50 = np.zeros(len(SIZES))
    for _ in range(nsim):
        y = rng.binomial(n, p0)
        p = y / n
        order = np.argsort(-p + rng.uniform(0, 1e-9, len(p)))
        top1_sizes.append(sizes[order[0]])
        for i, c in enumerate(SIZES):
            top50[i] += np.sum(sizes[order[:50]] == c)
            bot50[i] += np.sum(sizes[order[-50:]] == c)
    t1 = pd.Series(top1_sizes).value_counts(normalize=True).reindex(SIZES).fillna(0).round(3)
    out["simulation_same_rate"] = {
        "nsim": nsim, "p0": float(p0),
        "top1_size_share": t1.to_dict(),
        "top50_avg": dict(zip(SIZES, (top50 / nsim).round(1))),
        "bottom50_avg": dict(zip(SIZES, (bot50 / nsim).round(1))),
    }

    # ===== F 死亡（標準化死亡比） =====
    m = pd.read_csv(DATA / "smr.csv", dtype={"code": str})
    MS = ["100人未満", "100〜300人", "300〜1,000人", "1,000人以上"]
    m["size"] = pd.Categorical(m["size"], MS, ordered=True)
    smr_out = {}
    for k in ("all", "heart", "stroke"):
        mm = m.dropna(subset=[f"O_{k}", f"E_{k}"])
        mm = mm[mm[f"E_{k}"] > 0]
        mu, sh = fit_poisgamma_ml(mm[f"O_{k}"], mm[f"E_{k}"])
        raw = 100 * mm[f"O_{k}"] / mm[f"E_{k}"]
        eb = eb_smr(mm[f"O_{k}"], mm[f"E_{k}"], mu, sh)
        z = (mm[f"O_{k}"] - mm[f"E_{k}"] * mu) / np.sqrt(mm[f"E_{k}"] * mu)
        t = mm.assign(raw=raw, eb=eb)
        comp_k = {}
        for col in ("raw", "eb"):
            for largest, side in ((True, "高い"), (False, "低い")):
                dd = t.sort_values(col, ascending=not largest).head(50)
                comp_k[f"{col}|{side}50"] = {c: int((dd["size"] == c).sum()) for c in MS}
        smr_out[k] = {"mean_ratio": float(mu), "shape": float(sh),
                      "sd_between_pct": float(100 * mu / np.sqrt(sh)),
                      "share_out998": float((np.abs(z) > 3.09).mean()),
                      "raw_range": [float(raw.min()), float(raw.max())],
                      "eb_range": [float(eb.min()), float(eb.max())],
                      "top_bottom50_size": comp_k,
                      "shift_median_by_size": t.assign(sh=(t.eb - t.raw).abs()).groupby("size", observed=True)["sh"].median().round(1).to_dict()}
        smr_out[k]["share_out998_by_size"] = t.assign(o=np.abs(z) > 3.09).groupby("size", observed=True)["o"].mean().round(3).to_dict()
        smr_out[k]["weight_raw_median_by_size"] = t.assign(w=t[f"E_{k}"] / (t[f"E_{k}"] + sh / mu)).groupby("size", observed=True)["w"].median().round(3).to_dict()
        if k == "all":
            # シミュレーション：全地域の本当の SMR が同じ（=mu）でも、いちばん高い・低い地域はどの規模になるか
            Ev = t[f"E_{k}"].values; sz = t["size"].astype(str).values
            top1 = []; hi50 = np.zeros(len(MS)); lo50 = np.zeros(len(MS))
            for _ in range(2000):
                Os = rng.poisson(Ev * mu)
                r = Os / Ev + rng.uniform(0, 1e-9, len(Ev))
                o = np.argsort(-r)
                top1.append(sz[o[0]])
                for i, c in enumerate(MS):
                    hi50[i] += np.sum(sz[o[:50]] == c); lo50[i] += np.sum(sz[o[-50:]] == c)
            smr_out[k]["sim_same_smr"] = {
                "top1_size_share": pd.Series(top1).value_counts(normalize=True).reindex(MS).fillna(0).round(3).to_dict(),
                "high50_avg": dict(zip(MS, (hi50 / 2000).round(1))), "low50_avg": dict(zip(MS, (lo50 / 2000).round(1)))}
            t[["code", "E_all", "O_all", "raw", "eb", "size"]].to_csv(RES / "_smr_all_eb.csv", index=False)
            # F27 の BYM2 との一致
            f27 = ROOT.parent / "F27_disease_map_bym2" / "results" / "theta_main.csv"
            if f27.exists():
                th = pd.read_csv(f27, dtype={"code": str})
                col = "smr_bym2"
                j = t.merge(th[["code", col]], on="code")
                smr_out[k]["corr_with_F27_bym2"] = float(np.corrcoef(j.eb, j[col])[0, 1])
                smr_out[k]["corr_raw_with_F27_bym2"] = float(np.corrcoef(j.raw, j[col])[0, 1])
                smr_out[k]["F27_column_used"] = col
    out["smr"] = smr_out

    # ===== G 頑健性 =====
    rob = []
    def add(name, wr, we, k=50):
        rob.append({"設定": name,
                    "順位相関_生": round(sp(wr), 3), "順位相関_EB": round(sp(we), 3),
                    "上位10が翌年も残る_生": round(retention(wr, 10, True), 3),
                    "上位10が翌年も残る_EB": round(retention(we, 10, True), 3),
                    "上位50の500人未満_生": round(np.mean([np.sum(size_of[wr[y].sort_values(ascending=False).head(k).index] == "500人未満") for y in YEARS]), 1),
                    "上位50の500人未満_EB": round(np.mean([np.sum(size_of[we[y].sort_values(ascending=False).head(k).index] == "500人未満") for y in YEARS]), 1)})
    add("基本（大腸がん・全国の事前・最尤）", wide_raw, wide_eb)
    add("モーメント法", wide_raw, s.pivot(index="code", columns="year", values="p_eb_mom"))
    add("都道府県の平均を事前の中心に", wide_raw, s.pivot(index="code", columns="year", values="p_eb_pref"))
    wl_raw = s.pivot(index="code", columns="year", values="pl_raw").dropna()
    wl_eb = s.pivot(index="code", columns="year", values="pl_eb").loc[wl_raw.index]
    add("肺がん検診", wl_raw, wl_eb)
    nz = s.groupby("code").y_colon.min() > 0
    add("受診者0人の年がある団体を除く", wide_raw.loc[nz[nz].index], wide_eb.loc[nz[nz].index])
    for kk in (20, 100):
        rob.append({"設定": f"上位{kk}で数える", **{
            "上位50の500人未満_生": round(np.mean([np.sum(size_of[wide_raw[y].sort_values(ascending=False).head(kk).index] == "500人未満") for y in YEARS]), 1),
            "上位50の500人未満_EB": round(np.mean([np.sum(size_of[wide_eb[y].sort_values(ascending=False).head(kk).index] == "500人未満") for y in YEARS]), 1)}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.to_dict(orient="records")

    s.drop(columns=["name"]).to_csv(RES / "_screening_with_eb.csv", index=False)
    with open(RES / "summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:12000])


if __name__ == "__main__":
    main()
