"""03 分析：労働災害は、どの産業で減り、どこで減らなかったのか。
A. 労働災害動向調査の度数率（100万延べ実労働時間あたり死傷者数、事業所規模100人以上・30〜99人）の長期の変化
   → 産業ごとに、期間別の「年あたりの変化率」を擬似ポアソン回帰（対数リンク）で推定
B. 年千人率（労働者1,000人あたり、休業4日以上、2012〜2025年）→ 労働力調査の雇用者数で死傷者数を近似し、
   offset 付きポアソン回帰（過分散は Pearson χ²で補正）で産業ごとの年変化率
C. 全産業の年千人率の変化を「産業の中の率の変化」と「産業構成の変化」に分ける（シフト・シェア分解）
D. 頑健性：分母（労働者数／労働時間）、期間、産業区分、分解の重みの取り方、農林業の扱い
出力：results/*.csv, results/summary.json
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
np.random.seed(188)

# 年千人率の業種（労働者死傷病報告）→ 労働力調査の産業（雇用者数、万人）
MAP = {"製造業": ["製造業"], "鉱業": ["鉱業"], "建設業": ["建設業"], "運輸業": ["運輸業郵便業"],
       "商業": ["卸売業小売業"], "金融業": ["金融業保険業"], "教育研究業": ["教育学習支援業"],
       "保健衛生業": ["医療福祉"], "接客娯楽業": ["宿泊業飲食サービス業", "生活関連サービス業娯楽業"],
       "漁業": ["漁業"], "農業": ["農業林業"]}


def trend(df, ycol="rate", xcol="year", w=None):
    """擬似ポアソン（対数リンク、尺度は Pearson χ²/df）で年あたり変化率と95%区間"""
    X = sm.add_constant(df[xcol] - df[xcol].mean())
    m = sm.GLM(df[ycol], X, family=sm.families.Poisson(), freq_weights=w).fit(scale="X2")
    b, se = m.params.iloc[1], m.bse.iloc[1]
    return dict(pct=100 * (np.exp(b) - 1), lo=100 * (np.exp(b - 1.96 * se) - 1), hi=100 * (np.exp(b + 1.96 * se) - 1),
                p=float(m.pvalues.iloc[1]), n=len(df), scale=float(m.scale))


def part_a(t):
    out = []
    PER = {"1965-1990": (1965, 1990), "1990-2010": (1990, 2010), "2010-2024": (2010, 2024), "2015-2024": (2015, 2024)}
    for (size, ind), g in t[t.old_scope == 0].groupby(["size", "ind"]):
        for lab, (a, b) in PER.items():
            h = g[(g.year >= a) & (g.year <= b) & (g.fr > 0)]
            if len(h) < 5 or h.year.min() > a + 3:
                continue
            r = trend(h, "fr"); r.update(size=size, ind=ind, ind_ja=g.ind_ja.iloc[0], period=lab, measure="度数率")
            out.append(r)
            h2 = h[h.sr > 0]
            if len(h2) >= 5:
                r = trend(h2, "sr"); r.update(size=size, ind=ind, ind_ja=g.ind_ja.iloc[0], period=lab, measure="強度率")
                out.append(r)
    a = pd.DataFrame(out)
    a.to_csv(R / "a_trend_by_period.csv", index=False)
    # 最初の年と最後の年の比
    lv = []
    for (size, ind), g in t[(t.old_scope == 0)].groupby(["size", "ind"]):
        g = g.sort_values("year"); f, l = g.iloc[0], g.iloc[-1]
        lv.append(dict(size=size, ind=ind, ind_ja=g.ind_ja.iloc[0], first=int(f.year), fr_first=f.fr, last=int(l.year), fr_last=l.fr,
                       ratio=l.fr / f.fr if f.fr > 0 else np.nan, min_year=int(g.loc[g.fr.idxmin(), "year"]), fr_min=g.fr.min()))
    lv = pd.DataFrame(lv); lv.to_csv(R / "a_first_last.csv", index=False)
    return a, lv


def counts_frame(sen, emp):
    rows = []
    for _, e in emp.iterrows():
        y = int(e.year)
        for k, cols in MAP.items():
            wk = sum(e[c] for c in cols) * 1e4
            rate = float(sen.loc[sen.year == y, k].iloc[0])
            rows.append(dict(year=y, ind_ja=k, workers=wk, rate=rate, count=rate / 1000 * wk))
    return pd.DataFrame(rows)


def part_b(cf, per=(2012, 2025)):
    out = []
    for k, g in cf.groupby("ind_ja"):
        h = g[(g.year >= per[0]) & (g.year <= per[1])]
        X = sm.add_constant(h.year - h.year.mean())
        m = sm.GLM(h["count"].round(), X, family=sm.families.Poisson(), offset=np.log(h.workers)).fit(scale="X2")
        b, se = m.params.iloc[1], m.bse.iloc[1]
        out.append(dict(ind_ja=k, period=f"{per[0]}-{per[1]}", pct=100 * (np.exp(b) - 1), lo=100 * (np.exp(b - 1.96 * se) - 1),
                        hi=100 * (np.exp(b + 1.96 * se) - 1), p=float(m.pvalues.iloc[1]), scale=float(m.scale),
                        rate_first=h.rate.iloc[0], rate_last=h.rate.iloc[-1], workers_first=h.workers.iloc[0], workers_last=h.workers.iloc[-1]))
    return pd.DataFrame(out)


def shift_share(sen, emp, y0, y1, ag_forestry_share=0.0, weights="mid"):
    """全産業の年千人率 R = Σ s_i r_i + s_o r_o（その他は残差）。ΔR を構成効果と率の効果に分ける。
    ag_forestry_share>0 のとき、労働力調査の「農業，林業」のうちその割合を林業とみなして林業の率を当てる"""
    def comp(y):
        e = emp[emp.year == y].iloc[0]; s = sen[sen.year == y].iloc[0]; tot = e["総数"] * 1e4
        d = {}
        for k, cols in MAP.items():
            wk = sum(e[c] for c in cols) * 1e4
            if k == "農業" and ag_forestry_share > 0:
                d["林業"] = (wk * ag_forestry_share / tot, float(s["林業"]))
                wk = wk * (1 - ag_forestry_share)
            d[k] = (wk / tot, float(s[k]))
        so = 1 - sum(v[0] for v in d.values())
        ro = (float(s["全産業"]) - sum(v[0] * v[1] for v in d.values())) / so
        d["その他"] = (so, ro)
        return d, float(s["全産業"])
    c0, R0 = comp(y0); c1, R1 = comp(y1)
    rows = []
    for k in c0:
        s0, r0 = c0[k]; s1, r1 = c1[k]
        if weights == "mid":
            mix, within = (s1 - s0) * (r0 + r1) / 2, (s0 + s1) / 2 * (r1 - r0)
        else:  # ラスパイレス型（基準年の重み）＋交差項
            mix, within = (s1 - s0) * r0, s0 * (r1 - r0)
        rows.append(dict(ind_ja=k, share0=s0, share1=s1, rate0=r0, rate1=r1, mix=mix, within=within,
                         inter=(s1 - s0) * (r1 - r0) if weights != "mid" else 0.0))
    df = pd.DataFrame(rows)
    cf_rate = sum(c0[k][0] * c1[k][1] for k in c0)  # 2012年の構成のままなら
    return df, dict(y0=y0, y1=y1, R0=R0, R1=R1, dR=R1 - R0, mix=df.mix.sum(), within=df.within.sum(), inter=df.inter.sum(),
                    rate_if_2012_mix=cf_rate, forestry_share=ag_forestry_share, weights=weights)


def part_d(t, sen):
    """分母を変える：年千人率（労働者あたり）と度数率（労働時間あたり、規模別）の 2012〜2024 年の変化率"""
    pairs = {"全産業": ("total", "全産業"), "製造業": ("manuf", "製造業"), "建設業": ("constr_spec", "建設業"),
             "運輸業": ("transport", "運輸業"), "卸売・小売業": ("trade", "商業"), "林業": ("forestry", "林業")}
    out = []
    for lab, (k, sk) in pairs.items():
        s = sen[(sen.year >= 2012) & (sen.year <= 2024)][["year", sk]].rename(columns={sk: "rate"})
        r = trend(s); r.update(ind=lab, denom="労働者数（年千人率・休業4日以上）"); out.append(r)
        for size in ["100+", "30-99"]:
            h = t[(t.ind == k) & (t["size"] == size) & (t.old_scope == 0) & (t.year >= 2012) & (t.fr > 0)]
            if len(h) >= 8:
                r = trend(h, "fr"); r.update(ind=lab, denom=f"労働時間（度数率・規模{size}人）"); out.append(r)
        if lab == "建設業":
            h = t[(t.ind == "constr_gen") & (t["size"] == "100+") & (t.year >= 2012)]
            r = trend(h, "fr"); r.update(ind=lab, denom="労働時間（度数率・総合工事業の工事現場）"); out.append(r)
    return pd.DataFrame(out)


def main():
    t = pd.read_csv(D / "tidy_dosu.csv")
    sen = pd.read_csv(D / "sennin_rate.csv")
    emp = pd.read_csv(D / "employees_lfs.csv")
    S = {}

    a, lv = part_a(t)
    S["first_last_100"] = lv[lv["size"] == "100+"][["ind_ja", "first", "fr_first", "last", "fr_last", "ratio", "min_year", "fr_min"]].round(3).to_dict("records")

    # 1992〜2003年は調査対象の追加がある。旧範囲の値でつないだ全産業の比較
    tot = t[(t.ind == "total") & (t["size"] == "100+")]
    S["total_old_vs_new_1992_2003"] = tot.pivot_table(index="year", columns="old_scope", values="fr").dropna().round(2).reset_index().to_dict("records")

    cf = counts_frame(sen, emp); cf.to_csv(R / "b_counts_approx.csv", index=False)
    b_full = part_b(cf, (2012, 2025)); b_pre = part_b(cf, (2012, 2019)); b_post = part_b(cf, (2016, 2025))
    b = pd.concat([b_full, b_pre, b_post]); b.to_csv(R / "b_poisson_by_industry.csv", index=False)
    # 年千人率だけ（雇用者数を使わない）の傾きも
    bs = []
    for k in [c for c in sen.columns if c != "year"]:
        r = trend(sen[["year", k]].rename(columns={k: "rate"})); r.update(ind_ja=k); bs.append(r)
    bs = pd.DataFrame(bs); bs.to_csv(R / "b_rate_only_trend.csv", index=False)

    # 全産業の死傷者数（近似）の変化と、その内訳
    c0, c1 = cf[cf.year == 2012].set_index("ind_ja"), cf[cf.year == 2025].set_index("ind_ja")
    S["approx_counts_2012_2025"] = pd.DataFrame({"count2012": c0["count"], "count2025": c1["count"], "workers2012": c0.workers, "workers2025": c1.workers}).round(0).reset_index().to_dict("records")

    ss = []
    summ = []
    for (y0, y1) in [(2012, 2025), (2012, 2019), (2015, 2025)]:
        for fs in [0.0, 0.08, 0.15]:
            for wt in ["mid", "laspeyres"]:
                df, s = shift_share(sen, emp, y0, y1, fs, wt)
                df["y0"], df["y1"], df["forestry_share"], df["weights"] = y0, y1, fs, wt
                ss.append(df); summ.append(s)
    pd.concat(ss).to_csv(R / "c_shift_share_detail.csv", index=False)
    summ = pd.DataFrame(summ); summ.to_csv(R / "c_shift_share_summary.csv", index=False)
    S["shift_share"] = summ.round(4).to_dict("records")

    d = part_d(t, sen); d.to_csv(R / "d_denominator.csv", index=False)

    S["a_trend_100"] = a[(a["size"] == "100+") & (a.measure == "度数率")][["ind_ja", "period", "pct", "lo", "hi", "p", "n"]].round(3).to_dict("records")
    S["a_trend_30"] = a[(a["size"] == "30-99") & (a.measure == "度数率")][["ind_ja", "period", "pct", "lo", "hi", "p", "n"]].round(3).to_dict("records")
    S["a_sev_100"] = a[(a["size"] == "100+") & (a.measure == "強度率")][["ind_ja", "period", "pct", "lo", "hi", "p"]].round(3).to_dict("records")
    S["b"] = b.round(3).to_dict("records")
    S["b_rate_only"] = bs.round(3).to_dict("records")
    S["d"] = d.round(3).to_dict("records")
    json.dump(S, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
    print("ok")


if __name__ == "__main__":
    main()
