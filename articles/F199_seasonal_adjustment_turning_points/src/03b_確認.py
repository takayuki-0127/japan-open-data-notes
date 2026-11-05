"""頑健性：(1) 曜日の調整を入れた X-13、(2) データの終わりを切ったときの判定のずれ（あとから日付が動くか）、
(3) 推定期間を変えた X-13、(4) 判定が大きくずれた点は「ほぼ同じ高さの山が2つあった」のか。"""
import sys, pathlib, json, itertools
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, x13, stl, bb, match
import importlib.util
spec = importlib.util.spec_from_file_location("a", str(ROOT / "src" / "03_分析.py")); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

RES = ROOT / "results"
H = [6, 9, 12, 24]
KEYS = ["iip", "ship", "jobs", "unemp"]


def trunc_job(args):
    key, method, rdate, rtype, h = args
    nsa, pub = A.series_of(key)
    end = pd.Timestamp(rdate) + pd.DateOffset(months=h)
    s = nsa[:end]
    if method == "x11":
        x = x13(s, "x11")
    else:
        x = stl(s, 13)
    if x is None:
        return dict(series=key, method=method, ref=rdate, type=rtype, h=h, offset=None, failed=True)
    x = -x if key == "unemp" else x
    tp = bb(x)
    return dict(failed=False, series=key, method=method, ref=rdate, type=rtype, h=h, offset=match(tp, (pd.Timestamp(rdate), rtype)))


def td_job(key):
    nsa, pub = A.series_of(key)
    x = x13(nsa, "x11", td=True)
    return key, (-x if key == "unemp" else x)


def span_job(args):
    key, start = args
    nsa, pub = A.series_of(key)
    x = x13(nsa[start:], "x11")
    return key, start, (-x if key == "unemp" else x)


if __name__ == "__main__":
    SA = pd.read_csv(RES / "sa_series.csv", index_col=0, parse_dates=True)
    full = pd.read_csv(RES / "match_to_reference.csv")
    full = full[full.rule == "base"]
    out = {}
    # (1) 曜日の調整
    with ProcessPoolExecutor(2) as ex:
        tds = list(ex.map(td_job, A.NAMES))
    rows = []
    for k, x in tds:
        tp = bb(x)
        for rd, rt in A.refs_in(SA[f"{k}|pub"]):
            rows.append(dict(series=k, ref=rd.strftime("%Y-%m"), type=rt, offset=match(tp, (rd, rt))))
    td = pd.DataFrame(rows)
    m = td.merge(full[full.method == "pub"][["series", "ref", "offset"]], on=["series", "ref"], suffixes=("_td", "_pub")).dropna()
    m2 = td.merge(full[full.method == "x11"][["series", "ref", "offset"]], on=["series", "ref"], suffixes=("_td", "_x11")).dropna()
    out["td"] = dict(n=len(m), same_as_pub=float((m.offset_td == m.offset_pub).mean()), within1_pub=float(((m.offset_td - m.offset_pub).abs() <= 1).mean()),
                     within3_pub=float(((m.offset_td - m.offset_pub).abs() <= 3).mean()), same_as_x11=float((m2.offset_td == m2.offset_x11).mean()))
    td.to_csv(RES / "check_tradingday.csv", index=False)

    # (2) データの終わりを切る
    jobs = []
    for k in KEYS:
        s = SA[f"{k}|pub"].dropna()
        for rd, rt in A.refs_in(SA[f"{k}|pub"]):
            if rd + pd.DateOffset(months=24) <= s.index[-1] and rd >= s.index[0] + pd.DateOffset(months=60):
                for meth in ["x11", "stl13"]:
                    for h in H:
                        jobs.append((k, meth, rd.strftime("%Y-%m-%d"), rt, h))
    with ProcessPoolExecutor(2) as ex:
        tr = pd.DataFrame(list(ex.map(trunc_job, jobs)))
    tr["ref"] = tr.ref.str[:7]
    tr = tr.merge(full[["series", "method", "ref", "offset"]].rename(columns={"offset": "final"}), on=["series", "method", "ref"])
    tr.to_csv(RES / "check_endpoint.csv", index=False)
    g = []
    for (meth, h), d in tr.groupby(["method", "h"]):
        d = d[d.final.notna() & ~d.failed]
        found = d.offset.notna()
        g.append(dict(method=meth, h=h, n=len(d), found=float(found.mean()), same_as_final=float((d.offset == d.final).mean()),
                      within1=float(((d.offset - d.final).abs() <= 1).mean()), moved_gt3=float(((d.offset - d.final).abs() > 3).mean())))
    out["endpoint"] = g
    pd.DataFrame(g).to_csv(RES / "check_endpoint_summary.csv", index=False)

    # (3) 推定期間（鉱工業2系列：1978年〜／1990年〜／2000年〜）
    sj = [(k, st) for k in ["iip", "ship"] for st in ["1990-01-01", "2000-01-01"]]
    with ProcessPoolExecutor(2) as ex:
        sp = list(ex.map(span_job, sj))
    rows = []
    for k, st, x in sp:
        tp = bb(x)
        for rd, rt in A.refs_in(x):
            f = full[(full.series == k) & (full.method == "x11") & (full.ref == rd.strftime("%Y-%m"))].offset
            rows.append(dict(series=k, start=st[:4], ref=rd.strftime("%Y-%m"), type=rt, offset=match(tp, (rd, rt)), full=f.iloc[0] if len(f) else np.nan))
    spn = pd.DataFrame(rows); spn.to_csv(RES / "check_span.csv", index=False)
    d = spn.dropna()
    out["span"] = dict(n=len(d), same=float((d.offset == d.full).mean()), within1=float(((d.offset - d.full).abs() <= 1).mean()), moved_gt3=float(((d.offset - d.full).abs() > 3).mean()))

    # (4) ほぼ同じ高さの山（谷）があったか：公表値で、判定月から4か月以上離れた ±12か月の中の2番目の候補との差（%）
    spr = pd.read_csv(RES / "spread_by_reference_point.csv")
    pubo = full[full.method == "pub"].set_index(["series", "ref"]).offset
    rows = []
    for _, r in spr.iterrows():
        k = r.series
        x = SA[f"{k}|pub"].dropna()
        lvl = x.abs()
        rd = pd.Timestamp(r.ref + "-01")
        o = pubo.get((k, r.ref), np.nan)
        if pd.isna(o):
            continue
        dt = rd + pd.DateOffset(months=int(o))
        w = x[rd - pd.DateOffset(months=12): rd + pd.DateOffset(months=12)]
        far = w[(abs((w.index.year - dt.year) * 12 + w.index.month - dt.month) >= 4)]
        if far.empty or dt not in x.index:
            continue
        if r.type == "peak":
            gap = (x[dt] - far.max()) / lvl[dt] * 100
        else:
            gap = (far.min() - x[dt]) / lvl[dt] * 100
        rows.append(dict(series=k, ref=r.ref, type=r.type, spread=r.spread, gap_pct=gap))
    gp = pd.DataFrame(rows); gp.to_csv(RES / "check_near_tie.csv", index=False)
    # 方法どうしの季節調整値の差の大きさ（月ごとの |log 公表 − log X-11| の中央値, %）
    diffs = {}
    for k in A.NAMES:
        a, b, c = SA[f"{k}|pub"].abs(), SA[f"{k}|x11"].abs(), SA[f"{k}|stl13"].abs()
        diffs[k] = dict(pub_x11=float((np.log(a) - np.log(b)).abs().median() * 100), pub_stl13=float((np.log(a) - np.log(c)).abs().median() * 100))
    from scipy.stats import mannwhitneyu, spearmanr
    big, small = gp[gp.spread > 3].gap_pct, gp[gp.spread <= 1].gap_pct
    out["near_tie"] = dict(n=len(gp), big_n=len(big), big_median_gap=float(big.median()), small_n=len(small), small_median_gap=float(small.median()),
                           mw_p=float(mannwhitneyu(big, small, alternative="less").pvalue), spearman=float(spearmanr(gp.spread, gp.gap_pct)[0]),
                           big_share_gap_lt1=float((big < 1).mean()), small_share_gap_lt1=float((small < 1).mean()), sa_diff=diffs)
    json.dump(out, open(RES / "robustness.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
