"""03 分析：
(1) 全期間で DFM を推定し、共通因子・因子負荷量・景気の山谷との対応を見る
(2) 2008Q1〜2026Q2 の各四半期について、四半期の1・2・3か月目の月末と、四半期の翌月末の4時点で
    その時点に出ているデータだけで GDP 前期比を推定（疑似リアルタイム）。毎回推定し直す
(3) AR(1)・過去平均と比べる（RMSE・Diebold–Mariano 検定）
(4) 2026Q3 のナウキャスト（2026年8月末までのデータ）"""
import sys, json
from multiprocessing import Pool
import numpy as np
import pandas as pd
from scipy import stats
from common import RES, DATA, SERIES, SEED
from dfm import load, vintage, fit_nowcast, ar_nowcast, mean_nowcast

np.random.seed(SEED)
P, G = load()
ALL = [s[0] for s in SERIES]
COIN = [s[0] for s in SERIES if s[5] == "一致"]
NOFIN = [c for c in ALL if c not in ("日経商品指数", "マネーストック（前年比）", "株価（TOPIX）", "長期金利")]
VNAMES = ["1か月目", "2か月目", "3か月目", "翌月"]
EVAL_Q = pd.period_range("2008Q1", "2026Q2", freq="Q")
COVID_Q = pd.period_range("2020Q1", "2021Q2", freq="Q")


def one(args):
    q, vi, cols, k, mask = args
    V = q.asfreq("M", how="start") + vi  # vi=0..3 → 1か月目末..翌月末
    z, gv = vintage(P, G, V, cols, mask)
    try:
        dfm, _ = fit_nowcast(z, gv, q, k=k)
    except Exception as e:
        dfm = np.nan
    ar, h = ar_nowcast(gv, q)
    return dict(q=str(q), vint=VNAMES[vi], dfm=dfm, ar=ar, ar_h=h, mean=mean_nowcast(gv), actual=float(G.get(q, np.nan)))


def run(name, cols, k=1, mask=None, quarters=EVAL_Q):
    jobs = [(q, vi, cols, k, mask) for q in quarters for vi in range(4)]
    with Pool(2) as pool:
        out = pool.map(one, jobs)
    df = pd.DataFrame(out)
    df.to_csv(RES / f"nowcast_{name}.csv", index=False)
    return df


def dm(e1, e2, h=1):
    d = e1 ** 2 - e2 ** 2
    d = d[~np.isnan(d)]
    n = len(d)
    gam = [np.mean((d[:n - l] - d.mean()) * (d[l:] - d.mean())) for l in range(h)]
    var = (gam[0] + 2 * sum(gam[1:])) / n
    st = d.mean() / np.sqrt(var)
    st *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(st), float(2 * stats.t.sf(abs(st), n - 1))


def summarize(df, label, exclude_covid=False):
    d = df.copy()
    if exclude_covid:
        d = d[~d["q"].isin([str(q) for q in COVID_Q])]
    rows = []
    for v in VNAMES:
        x = d[d.vint == v]
        e_d, e_a, e_m = x.dfm - x.actual, x.ar - x.actual, x["mean"] - x.actual
        st, p = dm(e_d.values, e_a.values)
        rows.append(dict(設定=label, 時点=v, n=int(e_d.notna().sum()),
                         RMSE_DFM=np.sqrt(np.nanmean(e_d ** 2)), RMSE_AR=np.sqrt(np.nanmean(e_a ** 2)),
                         RMSE_平均=np.sqrt(np.nanmean(e_m ** 2)), MAE_DFM=np.nanmean(abs(e_d)), MAE_AR=np.nanmean(abs(e_a)),
                         比_DFM対AR=np.sqrt(np.nanmean(e_d ** 2)) / np.sqrt(np.nanmean(e_a ** 2)),
                         符号一致_DFM=np.mean(np.sign(x.dfm) == np.sign(x.actual)),
                         符号一致_AR=np.mean(np.sign(x.ar) == np.sign(x.actual)),
                         DM統計量=st, DM_p=p))
    return pd.DataFrame(rows)


def full_sample():
    z, gv = vintage(P, G, P.index.max(), ALL)
    nc, res = fit_nowcast(z, gv, "2026Q3", k=1)
    f = res.factors.smoothed.iloc[:, 0]
    f.index = f.index.astype(str)
    # 因子の向き：鉱工業生産の負荷量が正になるように
    lo = {c: float(res.params[f"loading.0->{c}"]) for c in ALL}
    lo["GDP"] = float(res.params["loading.0->GDP"])
    sign = 1 if lo["鉱工業生産"] > 0 else -1
    f = f * sign
    lo = {k: v * sign for k, v in lo.items()}
    pd.DataFrame({"factor": f}).to_csv(RES / "factor_full.csv", index_label="month")
    pd.Series(lo).to_csv(RES / "loadings_full.csv", header=["loading"])
    # 景気動向指数（一致）の前月比との相関
    lev = pd.read_csv(DATA / "raw" / "f13_monthly.csv", parse_dates=["month"]).set_index("month")
    ci = 100 * np.log(lev["ci_coin"]).diff()
    ci.index = ci.index.to_period("M").astype(str)
    j = pd.concat([f.rename("f"), ci.rename("ci")], axis=1).dropna()
    j3 = j.rolling(3).mean().dropna()
    # 後退期（山の翌月〜谷）
    cyc = pd.read_csv(DATA / "raw" / "cycle_dates.csv")
    rec = pd.Series(False, index=pd.period_range("1994-01", P.index.max(), freq="M"))
    peaks = cyc[cyc.type == "peak"].month.tolist()
    troughs = cyc[cyc.type == "trough"].month.tolist()
    for pk in peaks:
        tr = [t for t in troughs if t > pk]
        if tr:
            rec.loc[pd.Period(pk, "M") + 1: pd.Period(tr[0], "M")] = True
    rec.index = rec.index.astype(str)
    f3 = f.rolling(3).mean()
    jj = pd.concat([f3.rename("f3"), rec.rename("rec")], axis=1).dropna(); jj["rec"] = jj["rec"].astype(bool)
    out = dict(
        corr_factor_ci=float(j.corr().iloc[0, 1]), corr_factor_ci_3m=float(j3.corr().iloc[0, 1]),
        recession_months=int(jj.rec.sum()), share_neg_in_recession=float((jj[jj.rec].f3 < 0).mean()),
        share_neg_in_expansion=float((jj[~jj.rec].f3 < 0).mean()),
        mean_f3_recession=float(jj[jj.rec].f3.mean()), mean_f3_expansion=float(jj[~jj.rec].f3.mean()),
        nowcast_2026Q3_full=nc, llf=float(res.llf),
    )
    # 四半期ごとに因子の3か月平均と GDP の相関
    fq = f.copy(); fq.index = pd.PeriodIndex(fq.index, freq="M").asfreq("Q")
    fq = fq.groupby(level=0).mean()
    jq = pd.concat([fq.rename("f"), G.rename("g")], axis=1).dropna()
    out["corr_factor_gdp_q"] = float(jq.corr().iloc[0, 1])
    jq2 = jq[~jq.index.isin(COVID_Q)]
    out["corr_factor_gdp_q_excovid"] = float(jq2.corr().iloc[0, 1])
    rec.to_csv(RES / "recession_months.csv", header=["recession"], index_label="month")
    return out


def live_updates():
    """2026Q3 を、7月末〜9月末（実際は8月末までのデータ）の各時点で推定"""
    rows = []
    for V in ["2026-07", "2026-08"]:
        z, gv = vintage(P, G, V, ALL)
        v, _ = fit_nowcast(z, gv, "2026Q3")
        ar, h = ar_nowcast(gv, "2026Q3")
        rows.append(dict(時点=V + "末", DFM=v, AR=ar))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    RES.mkdir(exist_ok=True)
    info = full_sample()
    print(json.dumps(info, ensure_ascii=False, indent=1))
    base = run("base", ALL) if not (RES / "nowcast_base.csv").exists() or "--rerun" in sys.argv else pd.read_csv(RES / "nowcast_base.csv")
    print(summarize(base, "base").round(3).to_string(), flush=True)
    if "--base-only" in sys.argv: sys.exit()
    tabs = [summarize(base, "基本（20系列・因子1）"), summarize(base, "基本・コロナ期を除いて評価", exclude_covid=True)]
    def cached(name, cols, **kw):
        f = RES / f"nowcast_{name}.csv"
        return pd.read_csv(f) if f.exists() and "--rerun" not in sys.argv else run(name, cols, **kw)
    for name, cols, kw, label in [("coin", COIN, {}, "一致系列だけ（10系列）"),
                                  ("nofin", NOFIN, {}, "金融の4系列を除く（16系列）"),
                                  ("k2", ALL, {"k": 2}, "因子2つ"),
                                  ("k3", ALL, {"k": 3}, "因子3つ"),
                                  ("maskcovid", ALL, {"mask": ("2020-03", "2020-12")}, "2020年3〜12月の月次を欠測にして推定")]:
        d = cached(name, cols, **kw)
        tabs.append(summarize(d, label))
        if name == "maskcovid":
            tabs.append(summarize(d, label + "・コロナ期を除いて評価", exclude_covid=True))
        print(label, "done", flush=True)
    tab = pd.concat(tabs)
    tab.to_csv(RES / "accuracy.csv", index=False, float_format="%.4f")
    live = live_updates()
    live.to_csv(RES / "nowcast_2026Q3.csv", index=False, float_format="%.3f")
    info["live"] = live.to_dict("records")
    (RES / "summary.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
    print(tab.round(3).to_string())
    print(live)
