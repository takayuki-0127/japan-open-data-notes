"""水害の被害額の傾き（名目・実質・国民所得比）、上位の年の影響、頑健性（オフライン）。乱数はブートストラップだけで種を固定。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SEED = 20261116
Y0, Y1 = 1961, 2023


def ols_slope(y, v):
    return float(np.polyfit(y, np.log(v), 1)[0])


def theil_sen(y, v):
    y = np.asarray(y, float); lv = np.log(np.asarray(v, float))
    i, j = np.triu_indices(len(y), 1)
    return float(np.median((lv[j] - lv[i]) / (y[j] - y[i])))


def block_boot_ci(y, v, block=5, n=2000, seed=SEED):
    """傾きの95%区間：トレンドを引いた残差を5年ブロックで並べ替えて足し戻す（残差の自己相関を残す）。"""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float); lv = np.log(np.asarray(v, float))
    b, a = np.polyfit(y, lv, 1)
    fit = a + b * y; res = lv - fit
    T = len(y); nb = int(np.ceil(T / block))
    out = []
    for _ in range(n):
        starts = rng.integers(0, T - block + 1, nb)
        r = np.concatenate([res[s:s + block] for s in starts])[:T]
        out.append(np.polyfit(y, fit + r, 1)[0])
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def pct(x):
    return float((np.exp(x) - 1) * 100)


def main():
    RES.mkdir(exist_ok=True)
    d = pd.read_csv(ROOT / "data" / "flood_damage.csv")
    d["ratio_real_pct"] = d.damage_real2015_oku / d.ni_real2015_oku * 100
    d["ratio_nominal_pct"] = d.damage_nominal_oku / d.ni_nominal_oku * 100
    m = d[(d.year >= Y0) & (d.year <= Y1)].copy()
    series = {"名目額": "damage_nominal_oku", "実質額（平成27年価格）": "damage_real2015_oku", "国民所得に対する割合（実質÷実質）": "ratio_real_pct",
              "国民所得に対する割合（名目÷名目）": "ratio_nominal_pct"}
    trend = []
    for lab, c in series.items():
        ci = block_boot_ci(m.year, m[c])
        trend.append(dict(series=lab, col=c, ols_pct_per_year=pct(ols_slope(m.year, m[c])), theil_sen_pct_per_year=pct(theil_sen(m.year, m[c])),
                          boot_ci_low_pct=pct(ci[0]), boot_ci_high_pct=pct(ci[1])))
    tr = pd.DataFrame(trend)
    tr.round(4).to_csv(RES / "trend.csv", index=False)

    # 10年ごと（1961〜70, ..., 2011〜2020, 2021〜23）
    m["decade"] = ((m.year - 1961) // 10) * 10 + 1961
    dec = m.groupby("decade").agg(n=("year", "size"), real_mean=("damage_real2015_oku", "mean"), real_median=("damage_real2015_oku", "median"),
                                  ratio_mean=("ratio_real_pct", "mean"), ratio_median=("ratio_real_pct", "median"),
                                  nominal_mean=("damage_nominal_oku", "mean")).reset_index()
    dec["label"] = dec.decade.astype(str) + "〜" + np.minimum(dec.decade + 9, Y1).astype(str)
    dec.round(4).to_csv(RES / "decades.csv", index=False)

    # 上位の年
    top = m.sort_values("damage_real2015_oku", ascending=False)
    tot = float(m.damage_real2015_oku.sum())
    top_share = {k: float(top.damage_real2015_oku.head(k).sum() / tot) for k in [1, 3, 5, 10]}
    top10 = top.head(10)[["year", "damage_real2015_oku", "ratio_real_pct"]]
    top10.round(4).to_csv(RES / "top_years.csv", index=False)

    # H4：近年（2014〜2023）の平均、上位2年を除いた平均と、1961〜2013年の10年ごとの平均の最大
    rec = m[m.year.between(2014, 2023)]
    rec_top2 = rec.sort_values("damage_real2015_oku", ascending=False).head(2).year.tolist()
    rec_mean = float(rec.damage_real2015_oku.mean())
    rec_mean_ex = float(rec[~rec.year.isin(rec_top2)].damage_real2015_oku.mean())
    early = m[m.year <= 2013].copy()
    early["blk"] = (early.year - 1961) // 10
    early_blk = early.groupby("blk").damage_real2015_oku.mean()
    early_max = float(early_blk.max())
    early_blk_lab = int(1961 + 10 * early_blk.idxmax())
    early_min = float(early_blk.min())
    early_min_lab = int(1961 + 10 * early_blk.idxmin())

    T = {r["col"]: r for r in trend}
    hyp = {
        "H1": dict(rule="名目額の傾きが正なら支持", value_pct_per_year=T["damage_nominal_oku"]["ols_pct_per_year"],
                   verdict="支持" if T["damage_nominal_oku"]["ols_pct_per_year"] > 0 else "外れ"),
        "H2": dict(rule="実質額の傾きが正で95%区間が0を含まなければ外れ", value_pct_per_year=T["damage_real2015_oku"]["ols_pct_per_year"],
                   ci=[T["damage_real2015_oku"]["boot_ci_low_pct"], T["damage_real2015_oku"]["boot_ci_high_pct"]],
                   verdict="外れ" if T["damage_real2015_oku"]["boot_ci_low_pct"] > 0 else "支持"),
        "H3": dict(rule="被害率（実質÷実質）の傾きが負なら支持", value_pct_per_year=T["ratio_real_pct"]["ols_pct_per_year"],
                   verdict="支持" if T["ratio_real_pct"]["ols_pct_per_year"] < 0 else "外れ"),
        "H4": dict(rule="上位2年を除いた2014〜23年の平均が、1961〜2013年の10年ごとの平均の最大を上回れば外れ", recent_mean=rec_mean,
                   recent_mean_excl_top2=rec_mean_ex, recent_top2=rec_top2, early_decade_max=early_max, early_decade_max_start=early_blk_lab,
                   verdict="外れ" if rec_mean_ex > early_max else "支持"),
    }
    # 頑健性
    rob = []
    for lab, (a, b) in {"1946〜2023年（前は別の推計）": (1946, 2023), "本線 1961〜2023年": (1961, 2023), "1976〜2023年": (1976, 2023),
                        "1991〜2023年": (1991, 2023)}.items():
        u = d[(d.year >= a) & (d.year <= b)].dropna(subset=["damage_real2015_oku"])
        rob.append(dict(check=lab, real_ols=pct(ols_slope(u.year, u.damage_real2015_oku)), real_ts=pct(theil_sen(u.year, u.damage_real2015_oku)),
                        ratio_ols=pct(ols_slope(u.year, u.ratio_real_pct)), ratio_ts=pct(theil_sen(u.year, u.ratio_real_pct))))
    top3 = top.head(3).year.tolist()
    u = m[~m.year.isin(top3)]
    rob.append(dict(check="上位3年を除く（1961〜2023年）", real_ols=pct(ols_slope(u.year, u.damage_real2015_oku)), real_ts=pct(theil_sen(u.year, u.damage_real2015_oku)),
                    ratio_ols=pct(ols_slope(u.year, u.ratio_real_pct)), ratio_ts=pct(theil_sen(u.year, u.ratio_real_pct))))
    rb = pd.DataFrame(rob)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)

    v = lambda y, c: float(d.loc[d.year == y, c].iloc[0])
    main_ = dict(period=[Y0, Y1], trend=tr.round(4).to_dict(orient="records"), hypotheses=hyp, top_share_real=top_share, top3_years=top3,
                 top_years=top10.round(2).to_dict(orient="records"), robustness=rb.round(4).to_dict(orient="records"),
                 decades=dec.round(3).to_dict(orient="records"), early_decade_min=early_min, early_decade_min_start=early_min_lab,
                 real_1961=v(1961, "damage_real2015_oku"), real_2019=v(2019, "damage_real2015_oku"), real_2023=v(2023, "damage_real2015_oku"),
                 nominal_1961=v(1961, "damage_nominal_oku"), nominal_2019=v(2019, "damage_nominal_oku"),
                 ratio_1961=v(1961, "ratio_real_pct"), ratio_2019=v(2019, "ratio_real_pct"), ratio_2023=v(2023, "ratio_real_pct"),
                 ni_real_ratio_2023_1961=v(2023, "ni_real2015_oku") / v(1961, "ni_real2015_oku"),
                 max_abs_diff_ratio_vs_table=float((d.ratio_real_pct - d.damage_ratio_pct_table).abs().max()))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    d.round(5).to_csv(RES / "series.csv", index=False)
    print(tr.round(2).to_string()); print(json.dumps(hyp, ensure_ascii=False)); print(top_share, top3); print(dec.round(2).to_string()); print(rb.round(2).to_string())
    print({k: main_[k] for k in ["real_1961", "real_2019", "ratio_1961", "ratio_2023", "ni_real_ratio_2023_1961", "max_abs_diff_ratio_vs_table"]})


if __name__ == "__main__":
    main()
