"""生命表の自作（再計算）と、平均寿命の差の年齢別分解（Arriaga 法）。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, BANDS, YEARS, PREF

RES.mkdir(exist_ok=True)
LT = pd.read_csv(DATA / "lifetables.csv")


def table(year, pref_code, sex, src="pub", open_age=None):
    d = LT[(LT.year == year) & (LT.pref_code == pref_code) & (LT.sex == sex)].sort_values("age").reset_index(drop=True)
    if src == "own":
        d = rebuild(d)
    if open_age is not None and d.age.max() > open_age:
        d = truncate(d, open_age)
    return d


def rebuild(d):
    """公表の死亡率 nqx だけから、生存数・定常人口・平均余命を計算し直す（自作の生命表）"""
    q = d.qx.values.copy()
    n = len(q)
    lx = np.empty(n)
    lx[0] = 100000.0
    for i in range(1, n):
        lx[i] = lx[i - 1] * (1 - q[i - 1])
    dx = np.append(lx[:-1] - lx[1:], lx[-1])
    ax = np.full(n, 0.5)
    ax[0] = 0.1  # 0歳の平均生存年数（乳児の死亡は生後すぐに多い）
    Lx = lx - (1 - ax) * dx
    # 最後の年齢階級（95歳以上・100歳以上）：公表の平均余命を使う
    Lx[-1] = lx[-1] * d.ex.values[-1]
    Tx = Lx[::-1].cumsum()[::-1]
    ex = Tx / lx
    out = d.copy()
    out["lx"], out["dx"], out["Lx"], out["Tx"], out["ex"] = lx, dx, Lx, Tx, ex
    return out


def truncate(d, a):
    """a 歳以上をまとめた表にする（年次で最高年齢が違うので、比べるときにそろえる）"""
    d = d[d.age <= a].copy()
    i = d.index[d.age == a][0]
    d.loc[i, "Lx"] = d.loc[i, "Tx"]
    d.loc[i, "qx"] = 1.0
    d.loc[i, "dx"] = d.loc[i, "lx"]
    d.loc[i, "open"] = True
    return d.reset_index(drop=True)


def arriaga(d1, d2):
    """d1（基準）→ d2 の平均寿命の差を年齢別に分解する。合計は e0(2) − e0(1) に一致する"""
    l1, l2 = d1.lx.values, d2.lx.values
    L1, L2 = d1.Lx.values, d2.Lx.values
    T1, T2 = d1.Tx.values, d2.Tx.values
    r = l1[0]
    n = len(l1)
    c = np.zeros(n)
    for i in range(n - 1):
        direct = l1[i] / r * (L2[i] / l2[i] - L1[i] / l1[i])
        indirect = T2[i + 1] / r * (l1[i] / l2[i] - l1[i + 1] / l2[i + 1])
        c[i] = direct + indirect
    c[-1] = l1[-1] / r * (T2[-1] / l2[-1] - T1[-1] / l1[-1])
    return pd.Series(c, index=d1.age.values)


def sym(d1, d2):
    """向きによる非対称をならす：(1→2) と −(2→1) の平均"""
    return (arriaga(d1, d2) - arriaga(d2, d1)) / 2


def bands(c, bands=BANDS):
    return pd.Series({lab: c[(c.index >= a) & (c.index <= b)].sum() for a, b, lab in bands})


def e0(d):
    return d.Tx.values[0] / d.lx.values[0]


def var_share(contrib):
    """県の差（gap）の分散を、年齢区分ごとの寄与に分ける：cov(c_b, gap)/var(gap)"""
    gap = contrib.sum(axis=1)
    v = gap.var()
    return contrib.apply(lambda s: s.cov(gap) / v)


def pref_contrib(year, sex, src="pub", open_age=None, ref="national", method="arriaga", band_def=BANDS):
    if ref == "national":
        d1 = table(year, 0, sex, src, open_age)
    else:
        d1 = mean_table(year, sex, open_age)
    rows = {}
    for p in range(1, 48):
        d2 = table(year, p, sex, src, open_age)
        c = arriaga(d1, d2) if method == "arriaga" else sym(d1, d2)
        rows[PREF[p - 1]] = bands(c, band_def)
    return pd.DataFrame(rows).T


def mean_table(year, sex, open_age=None):
    """47都道府県の死亡率 nqx の平均から作る基準の表（全国の代わり）"""
    ds = [table(year, p, sex, "pub", open_age) for p in range(1, 48)]
    d = ds[0].copy()
    d["qx"] = np.mean([x.qx.values for x in ds], axis=0)
    d["ex"] = np.mean([x.ex.values for x in ds], axis=0)
    return rebuild(d)


def main():
    out = {}
    # 1. 自作の生命表と公表値の一致
    chk = []
    for y in YEARS:
        for s in ["男", "女"]:
            for p in range(0, 48):
                pub = table(y, p, s)
                own = rebuild(pub)
                chk.append(dict(year=y, sex=s, pref=("全国" if p == 0 else PREF[p - 1]), e0_pub=pub.ex.values[0],
                                e0_own=own.ex.values[0], e65_pub=pub.loc[pub.age == 65, "ex"].values[0],
                                e65_own=own.loc[own.age == 65, "ex"].values[0]))
    chk = pd.DataFrame(chk)
    chk["diff0"] = chk.e0_own - chk.e0_pub
    chk["diff65"] = chk.e65_own - chk.e65_pub
    chk.to_csv(RES / "rebuild_check.csv", index=False)
    out["rebuild"] = dict(max_abs_diff_e0=float(chk.diff0.abs().max()), mean_abs_diff_e0=float(chk.diff0.abs().mean()),
                          max_abs_diff_e65=float(chk.diff65.abs().max()))

    # 2. 平均寿命の県の差（2020年）
    e = chk[(chk.year == 2020) & (chk.pref != "全国")].pivot(index="pref", columns="sex", values="e0_pub")
    nat = chk[(chk.year == 2020) & (chk.pref == "全国")].set_index("sex").e0_pub
    e.to_csv(RES / "e0_2020.csv")
    out["e0_2020"] = {s: dict(national=float(nat[s]), max=float(e[s].max()), max_pref=e[s].idxmax(),
                               min=float(e[s].min()), range=float(e[s].max() - e[s].min()), sd=float(e[s].std()))
                      for s in ["男", "女"]}
    # 年ごとのばらつき（生命表から）
    disp = chk[chk.pref != "全国"].groupby(["year", "sex"]).e0_pub.agg(["std", "min", "max"])
    disp["range"] = disp["max"] - disp["min"]
    disp.to_csv(RES / "dispersion_by_year.csv")
    out["dispersion"] = disp.round(3).reset_index().to_dict(orient="records")

    # 3. 県と全国の差の年齢別分解（2020年）
    allc = {}
    for s in ["男", "女"]:
        c = pref_contrib(2020, s)
        e_gap = pd.Series({PREF[p - 1]: e0(table(2020, p, s)) - e0(table(2020, 0, s)) for p in range(1, 48)})
        assert np.allclose(c.sum(axis=1).loc[e_gap.index], e_gap, atol=1e-3), "分解の合計が差と合わない"
        out.setdefault("check_sum", {})[s] = float((c.sum(axis=1).loc[e_gap.index] - (e[s] - nat[s]).loc[e_gap.index]).abs().max())
        c.to_csv(RES / f"arriaga_2020_{s}.csv")
        allc[s] = c
        vs = var_share(c)
        gap = c.sum(axis=1).sort_values()
        lo5, hi5 = gap.index[:5], gap.index[-5:]
        out[f"arriaga_2020_{s}"] = dict(
            var_share=vs.round(3).to_dict(),
            top5_mean=c.loc[hi5].mean().round(3).to_dict(), top5_gap=float(gap[hi5].mean()),
            bottom5_mean=c.loc[lo5].mean().round(3).to_dict(), bottom5_gap=float(gap[lo5].mean()),
            top_minus_bottom=(c.loc[hi5].mean() - c.loc[lo5].mean()).round(3).to_dict(),
            top5=list(hi5[::-1]))
    # 4. 20年の変化（2000→2020）。最高年齢を95歳以上にそろえる
    ch = {}
    for s in ["男", "女"]:
        d0 = table(2000, 0, s, open_age=95)
        d1 = table(2020, 0, s, open_age=95)
        cn = bands(arriaga(d0, d1))
        ch[s] = dict(national_change=float(e0(d1) - e0(d0)), by_band=cn.round(3).to_dict())
        c00 = pref_contrib(2000, s, open_age=95)
        c20 = pref_contrib(2020, s, open_age=95)
        g00, g20 = c00.sum(axis=1), c20.sum(axis=1)
        dc = c20 - c00
        dc.to_csv(RES / f"gap_change_2000_2020_{s}.csv")
        lo = g00.sort_values().index[:10]
        ch[s].update(dict(
            sd2000=float(g00.std()), sd2020=float(g20.std()),
            var_share2000=var_share(c00).round(3).to_dict(), var_share2020=var_share(c20).round(3).to_dict(),
            corr_gap2000_change=float(np.corrcoef(g00, g20 - g00)[0, 1]),
            bottom10_2000_gap2000=float(g00[lo].mean()), bottom10_2000_gap2020=float(g20[lo].mean()),
            bottom10_change_by_band=dc.loc[lo].mean().round(3).to_dict()))
    out["change_2000_2020"] = ch

    # 5. 頑健性：県の差の分散のうち、年齢区分ごとの割合
    fine = [(0, 0, "0歳")] + [(a, a + 4 if a > 0 else 4, f"{a}〜{a + 4}") for a in range(1, 95, 5)][:0]
    five = [(0, 0, "0歳"), (1, 4, "1-4")] + [(a, a + 4, f"{a}-{a + 4}") for a in range(5, 95, 5)] + [(95, 200, "95+")]
    rob = {}
    for s in ["男", "女"]:
        base = var_share(allc[s])
        sets = {
            "本体（全国が基準・公表の表）": base,
            "基準を47都道府県の平均の表にする": var_share(pref_contrib(2020, s, ref="mean")),
            "向きをならした分解（対称版）": var_share(pref_contrib(2020, s, method="sym")),
            "自作の生命表で分解": var_share(pref_contrib(2020, s, src="own")),
            "最高年齢を90歳以上にそろえる": var_share(pref_contrib(2020, s, open_age=90)),
            "2015年": var_share(pref_contrib(2015, s)),
        }
        rob[s] = pd.DataFrame(sets).T
        rob[s].to_csv(RES / f"robust_varshare_{s}.csv")
        # 5歳刻み
        c5 = pref_contrib(2020, s, band_def=five)
        v5 = var_share(c5)
        v5.to_csv(RES / f"varshare_5yr_{s}.csv", header=["share"])
        rob[s + "_5yr_top"] = v5.sort_values(ascending=False).head(6).round(3).to_dict()
        # 65歳の平均余命の差（65歳以上だけの差）の大きさ
        e65 = chk[(chk.year == 2020) & (chk.pref != "全国")].pivot(index="pref", columns="sex", values="e65_pub")[s]
        rob[s + "_e65"] = dict(sd=float(e65.std()), range=float(e65.max() - e65.min()),
                               corr_with_e0=float(np.corrcoef(e65, e[s].loc[e65.index])[0, 1]))
    out["robust"] = {k: (v.round(3).to_dict(orient="index") if isinstance(v, pd.DataFrame) else v) for k, v in rob.items()}

    # 6. 年次推移（付録80000）のばらつき
    tr = pd.read_csv(DATA / "e0_trend.csv")
    tr = tr[(tr.pref != "全国") & (tr.year >= 1965)]
    td = tr.groupby(["sex", "year"]).e0.agg(["std", "min", "max", "count"])
    td["range"] = td["max"] - td["min"]
    td.to_csv(RES / "trend_dispersion.csv")
    out["trend"] = td.round(3).reset_index().to_dict(orient="records")
    json.dump(out, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["rebuild", "e0_2020"]}, ensure_ascii=False, indent=1))
    for s in ["男", "女"]:
        print(s, json.dumps(out[f"arriaga_2020_{s}"], ensure_ascii=False))
        print(s, json.dumps(ch[s], ensure_ascii=False))
        print(rob[s].round(2).to_string())
        print(rob[s + "_5yr_top"], rob[s + "_e65"])
    print(td.loc[:, ["std", "range", "count"]].round(2).to_string())


if __name__ == "__main__":
    main()
