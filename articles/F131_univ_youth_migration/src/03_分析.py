"""03 分析：大学進学率と県外進学、15〜19歳・20〜24歳の転入超過の関係。

主な量（都道府県 p、年 t）
- E  : p の高校出身の大学入学者（どこの大学でも）
- S  : そのうち p の大学に入った人（地元進学）
- O  : E - S（県外の大学へ）
- I  : 他県の高校出身で p の大学に入った人
- G  : p の高校卒業者数（SSDSE-B、2013〜2024年度）
- r = E/G（大学進学の多さ。過年度卒を含むので「率」はおおよそ）、o = O/E（県外進学の比率）
- m15 = 15〜19歳の転入超過数（日本人）/ G、m20 = 20〜24歳の転入超過数 / G
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data")
R = os.path.join(ROOT, "results")
os.makedirs(R, exist_ok=True)
np.random.seed(131)

METRO = ["埼玉", "千葉", "東京", "神奈川", "愛知", "京都", "大阪", "兵庫"]


def build(kinds=("univ",), sheet="計"):
    f = pd.read_csv(os.path.join(D, "flows_univ.csv"))
    f = f[f.kind.isin(kinds) & (f.sheet == sheet)].groupby(["year", "dest", "orig"], as_index=False)["n"].sum()
    E = f.groupby(["year", "orig"]).n.sum().rename("E")
    S = f[f.dest == f.orig].groupby(["year", "orig"]).n.sum().rename("S")
    A = f.groupby(["year", "dest"]).n.sum().rename("A")  # p の大学の入学者
    A.index.names = ["year", "orig"]
    p = pd.concat([E, S, A], axis=1).reset_index().rename(columns={"orig": "pref"})
    p["O"] = p.E - p.S
    p["I"] = p.A - p.S
    p["o"] = p.O / p.E
    return p


def add_mig(p):
    m = pd.read_csv(os.path.join(D, "netmig_age.csv"))
    w = m[m.age.isin(["15-19", "20-24"])].pivot_table(index=["year", "pref"], columns=["sex", "age"], values="net")
    w.columns = [f"net_{'t' if s == '総数' else ('m' if s == '男' else 'f')}{a[:2]}" for s, a in w.columns]
    g = pd.read_csv(os.path.join(D, "hs_grads.csv"))
    # SSDSE-B の「年度」t の卒業者数は t+1 年3月の卒業者（例：2021年度＝990,230人＝2022年3月卒）。
    # 入学年度にそろえるため1年ずらす。
    g["year"] = g["year"] + 1
    out = p.merge(w.reset_index(), on=["year", "pref"], how="left").merge(g, on=["year", "pref"], how="left")
    return out


def fe(df, y, xs, w=None):
    d = df.dropna(subset=[y] + xs).copy()
    form = f"{y} ~ {' + '.join(xs)} + C(pref) + C(year)"
    mod = smf.wls(form, d, weights=d[w] if w else np.ones(len(d))).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.pref)[0]})
    res = {}
    for x in xs:
        res[x] = dict(b=float(mod.params[x]), se=float(mod.bse[x]), lo=float(mod.conf_int().loc[x, 0]),
                      hi=float(mod.conf_int().loc[x, 1]), p=float(mod.pvalues[x]))
    res["n"] = int(mod.nobs)
    # 固定効果を除いた後に残る説明変数のばらつき（標準偏差）
    for x in xs:
        rx = smf.ols(f"{x} ~ C(pref) + C(year)", d).fit().resid
        res[x]["sd_within"] = float(rx.std())
    return res


def main():
    p = add_mig(build())
    p["r"] = p.E / p.hs_grads
    p["out_rate"] = p.O / p.hs_grads          # 県外の大学へ出る人 / 高卒者
    p["stay_rate"] = p.S / p.hs_grads         # 地元の大学へ / 高卒者
    p["in_rate"] = p.I / p.hs_grads
    p["netuni_rate"] = (p.I - p.O) / p.hs_grads
    p["m15"] = p.net_t15 / p.hs_grads
    p["m20"] = p.net_t20 / p.hs_grads
    p["m15_m"] = p.net_m15 / p.hs_grads * 2
    p["m15_f"] = p.net_f15 / p.hs_grads * 2
    p["metro"] = p.pref.isin(METRO)
    p.to_csv(os.path.join(D, "panel.csv"), index=False)
    out = {}

    # A. 全国の推移（2005〜2025）
    nat = p.groupby("year").agg(E=("E", "sum"), O=("O", "sum"), S=("S", "sum"), G=("hs_grads", "sum")).reset_index()
    nat["o"] = nat.O / nat.E
    nat["r"] = (nat.E / nat.G).where(nat.G > 0)
    nm = p[~p.metro].groupby("year").agg(E=("E", "sum"), O=("O", "sum"), G=("hs_grads", "sum"))
    nat["o_nonmetro"] = (nm.O / nm.E).values
    nat["r_nonmetro"] = (nm.E / nm.G).where(nm.G > 0).values
    # 県ごとの o の中央値
    nat["o_median"] = p.groupby("year").o.median().values
    nat.to_csv(os.path.join(R, "national_trend.csv"), index=False)
    out["national"] = nat[nat.year.isin([2005, 2013, 2019, 2024, 2025])].round(4).to_dict("records")

    q = p[(p.year >= 2013) & (p.year <= 2024)].copy()

    # B. 15〜19歳の転入超過は、大学の入学の出入りでどこまで説明できるか
    cs = q.groupby("pref")[["m15", "netuni_rate", "m20", "out_rate", "r", "o"]].mean()
    b = smf.ols("m15 ~ netuni_rate", cs).fit()
    out["cross_m15_on_netuni"] = dict(b=float(b.params["netuni_rate"]), r2=float(b.rsquared),
                                      corr=float(cs[["m15", "netuni_rate"]].corr().iloc[0, 1]))
    b2 = smf.ols("m15 ~ out_rate + in_rate", q.groupby("pref")[["m15", "out_rate", "in_rate"]].mean()).fit()
    out["cross_m15_on_out_in"] = {k: float(v) for k, v in b2.params.items()} | {"r2": float(b2.rsquared)}
    cs.round(4).to_csv(os.path.join(R, "cross_section_means.csv"))

    # C. 固定効果パネル（都道府県と年の固定効果、県でクラスター）
    out["fe_main_r_o"] = fe(q, "m15", ["r", "o"])
    out["fe_r_only"] = fe(q, "m15", ["r"])
    out["fe_out_stay"] = fe(q, "m15", ["out_rate", "stay_rate"])
    out["fe_netuni"] = fe(q, "m15", ["netuni_rate"])
    out["fe_m20_r_o"] = fe(q, "m20", ["r", "o"])

    # D. 分解：県外の大学へ出る人の変化（2013→2024）= 高卒者数 × 進学の多さ × 県外比率
    def decomp(g0, g1):
        a = dict(G=np.log(g1.G / g0.G), r=np.log(g1.r / g0.r), o=np.log(g1.o / g0.o))
        tot = np.log(g1.O / g0.O)
        return {k: float(v) for k, v in a.items()} | {"total": float(tot), "O0": float(g0.O), "O1": float(g1.O)}
    dec = {}
    for name, sub in [("全国", q), ("大都市圏8都府県以外", q[~q.metro]), ("大都市圏8都府県", q[q.metro])]:
        g = sub.groupby("year").agg(O=("O", "sum"), E=("E", "sum"), G=("hs_grads", "sum"))
        g["r"] = g.E / g.G
        g["o"] = g.O / g.E
        dec[name] = decomp(g.loc[2013], g.loc[2024])
    # 県ごと（2013→2024）
    rows = []
    for pr, sub in q.groupby("pref"):
        s0, s1 = sub[sub.year == 2013].iloc[0], sub[sub.year == 2024].iloc[0]
        rows.append(dict(pref=pr, metro=bool(s0.metro), dlnG=np.log(s1.hs_grads / s0.hs_grads), dlnr=np.log(s1.r / s0.r),
                         dlno=np.log(s1.o / s0.o), dlnO=np.log(s1.O / s0.O), o_2013=s0.o, o_2024=s1.o, r_2013=s0.r, r_2024=s1.r,
                         dm15=s1.m15 - s0.m15))
    pd_ = pd.DataFrame(rows)
    pd_.round(4).to_csv(os.path.join(R, "decomp_by_pref.csv"), index=False)
    out["decomp"] = dec
    out["decomp_pref_summary"] = dict(
        share_r_up=float((pd_.dlnr > 0).mean()), share_o_up=float((pd_.dlno > 0).mean()),
        median_dlnr=float(pd_.dlnr.median()), median_dlno=float(pd_.dlno.median()),
        corr_dlnr_dlno=float(pd_[["dlnr", "dlno"]].corr().iloc[0, 1]),
        corr_dlnr_dm15=float(pd_[["dlnr", "dm15"]].corr().iloc[0, 1]))
    big = pd_.dlnr.idxmax()
    out["decomp_pref_summary"]["corr_dlnr_dlno_drop_max"] = float(pd_.drop(big)[["dlnr", "dlno"]].corr().iloc[0, 1])
    # 仕組みどおりなら期待される係数：m15 の変化 = 住民票への表れ方 × (−県外比率) × r の変化
    for k in ["cross_m15_on_netuni"]:
        pass
    out["expected_coef_r"] = dict(o_mean=float(q.o.mean()),
                                  passthrough_cross=out["cross_m15_on_netuni"]["b"],
                                  passthrough_fe=out["fe_netuni"]["netuni_rate"]["b"],
                                  exp_cross=float(-q.o.mean() * out["cross_m15_on_netuni"]["b"]),
                                  exp_fe=float(-q.o.mean() * out["fe_netuni"]["netuni_rate"]["b"]))
    # 進学が増えた県ほど、県外比率は下がったか（県の固定効果パネル）
    out["fe_o_on_r"] = fe(q, "o", ["r"])

    # E. 頑健性
    rob = {}
    rob["期間 2013-2018"] = fe(q[q.year <= 2018], "m15", ["r", "o"])
    rob["期間 2019-2024"] = fe(q[q.year >= 2019], "m15", ["r", "o"])
    rob["2020・2021年を除く"] = fe(q[~q.year.isin([2020, 2021])], "m15", ["r", "o"])
    rob["男性の転入超過"] = fe(q, "m15_m", ["r", "o"])
    rob["女性の転入超過"] = fe(q, "m15_f", ["r", "o"])
    rob["大都市圏8都府県を除く"] = fe(q[~q.metro], "m15", ["r", "o"])
    q2 = q.copy()
    q2["jhs_lag"] = q2.groupby("pref").jhs_grads.shift(3)
    q2["r_j"] = q2.E / q2.jhs_lag
    q2["m15_j"] = q2.net_t15 / q2.jhs_lag
    rob["分母を3年前の中学卒業者"] = fe(q2, "m15_j", ["r_j", "o"])
    rob["高卒者数で重みづけ"] = fe(q, "m15", ["r", "o"], w="hs_grads")
    # 大学＋短大
    pj = add_mig(build(kinds=("univ", "junior")))
    pj = pj[(pj.year >= 2013) & (pj.year <= 2024)].copy()
    pj["r"] = pj.E / pj.hs_grads
    pj["m15"] = pj.net_t15 / pj.hs_grads
    rob["大学＋短期大学"] = fe(pj, "m15", ["r", "o"])
    # 国立だけ・私立だけの県外比率
    for sh in ["国立", "私立"]:
        ps = build(sheet=sh)[["year", "pref", "o", "E"]].rename(columns={"o": "o_" + sh, "E": "E_" + sh})
        q = q.merge(ps, on=["year", "pref"], how="left")
    rob["県外比率を私立だけで"] = fe(q, "m15", ["r", "o_私立"])
    rob["県外比率を国立だけで"] = fe(q, "m15", ["r", "o_国立"])
    out["robust"] = rob

    # 男女（2021〜2025年、表に「計のうち男／女」がある年）
    f = pd.read_csv(os.path.join(D, "flows_univ.csv"))
    sx = []
    for lab in ["計", "男"]:
        g = f[(f.kind == "univ") & (f.sheet == lab) & (f.year >= 2021)]
        E = g.groupby(["year", "orig"]).n.sum()
        S = g[g.dest == g.orig].groupby(["year", "orig"]).n.sum()
        sx.append(((E - S).groupby("year").sum() / E.groupby("year").sum()).rename(lab))
    sxd = pd.concat(sx, axis=1)
    if "男" in sxd:
        # 女 = 計 - 男
        g = f[(f.kind == "univ") & (f.year >= 2021)]
        piv = g.pivot_table(index=["year", "dest", "orig"], columns="sheet", values="n").fillna(0)
        if "男" in piv:
            piv["女"] = piv["計"] - piv["男"]
            pv = piv.reset_index()
            for lab in ["男", "女"]:
                E = pv.groupby("year")[lab].sum()
                S = pv[pv.dest == pv.orig].groupby("year")[lab].sum()
                sxd["o_" + lab] = (E - S) / E
    out["sex_out_share_2021_2025"] = sxd.round(4).reset_index().to_dict("records")

    # 20〜24歳：4年前に県外の大学へ出た人が多い県ほど、20〜24歳の転入超過は大きいか（戻り）
    q3 = p[(p.year >= 2013)].sort_values(["pref", "year"]).copy()
    q3["out_rate_l4"] = q3.groupby("pref").out_rate.shift(4)
    q3["net20_per_G_l4"] = q3.net_t20 / q3.groupby("pref").hs_grads.shift(4)
    out["fe_m20_on_out_l4"] = fe(q3[q3.year <= 2024], "net20_per_G_l4", ["out_rate_l4"])
    cs20 = q3.groupby("pref")[["net20_per_G_l4", "out_rate_l4"]].mean().dropna()
    out["cross_m20_on_out_l4"] = dict(corr=float(cs20.corr().iloc[0, 1]))

    json.dump(out, open(os.path.join(R, "results.json"), "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:9000])


if __name__ == "__main__":
    main()
