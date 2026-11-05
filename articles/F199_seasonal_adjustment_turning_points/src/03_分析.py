"""季節調整の方法（公表値・X-13 の X-11 法／SEATS・STL・移動平均・前年比）ごとに山谷を判定し、
景気基準日付との差と、方法どうしのずれを比べる。"""
import sys, pathlib, json, itertools
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, x13, stl, yoy, ma12, bb, match

np.random.seed(199)
D = ROOT / "data"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)
df = pd.read_csv(D / "series_nsa_sa.csv", parse_dates=["date"])
ref = pd.read_csv(D / "raw" / "cycle_dates.csv")
ref["date"] = pd.to_datetime(ref.month + "-01")
NAMES = {"iip": "鉱工業生産", "ship": "鉱工業出荷", "jobs": "有効求人倍率", "emp": "就業者", "unemp": "完全失業率（逆）"}
RATE = {"jobs", "unemp"}
METHODS = ["pub", "x11", "seats", "x11_noout", "stl7", "stl13", "stl35", "ma12", "yoy"]
MLAB = {"pub": "公表の季節調整値", "x11": "X-13（X-11法）", "seats": "X-13（SEATS）", "x11_noout": "X-13（X-11法・外れ値処理なし）",
        "stl7": "STL（季節の窓7）", "stl13": "STL（季節の窓13）", "stl35": "STL（季節の窓35）", "ma12": "2×12移動平均", "yoy": "前年比"}
RULES = {"base": dict(), "w3": dict(w=3), "w7": dict(w=7), "ph9": dict(min_phase=9), "sm3": dict(smooth=3)}
SA4 = ["pub", "x11", "seats", "stl13"]


def make(key, s_nsa, s_pub, method):
    sign = -1 if key == "unemp" else 1
    if method == "pub":
        x = s_pub
    elif method in ("x11", "seats", "x11_noout"):
        x = x13(s_nsa, "x11" if method != "seats" else "seats", outlier=(method != "x11_noout"))
    elif method.startswith("stl"):
        x = stl(s_nsa, seasonal=int(method[3:]))
    elif method == "ma12":
        x = ma12(s_nsa)
    elif method == "yoy":
        x = (s_nsa - s_nsa.shift(12)) if key in RATE else yoy(s_nsa)
    return sign * x


def series_of(key):
    g = df[df.key == key].set_index("date")
    return g.nsa, g.sa_pub


def sa_job(args):
    key, method = args
    nsa, pub = series_of(key)
    return key, method, make(key, nsa, pub, method)


def refs_in(x):
    lo, hi = x.dropna().index[0] + pd.DateOffset(months=12), x.dropna().index[-1] - pd.DateOffset(months=12)
    r = ref[(ref.date >= lo) & (ref.date <= hi)]
    return list(zip(r.date, r.type))


def months(a, b):
    return (a.year - b.year) * 12 + a.month - b.month


if __name__ == "__main__":
    jobs = list(itertools.product(NAMES, METHODS))
    with ProcessPoolExecutor(2) as ex:
        out = list(ex.map(sa_job, jobs))
    SA = {(k, m): s for k, m, s in out}
    wide = pd.DataFrame({f"{k}|{m}": s for (k, m), s in SA.items()})
    wide.to_csv(RES / "sa_series.csv", float_format="%.5f")

    turns, rows = [], []
    for (k, m), s in SA.items():
        for rn, rp in RULES.items():
            tp = bb(s, **rp)
            for d, t in tp:
                turns.append(dict(series=k, method=m, rule=rn, date=d.strftime("%Y-%m"), type=t))
            # 基準日付に対応しない点（±12か月に同じ種類の基準日付がない点）
            rr = refs_in(SA[(k, "pub")])
            for rd, rt in rr:
                rows.append(dict(series=k, method=m, rule=rn, ref=rd.strftime("%Y-%m"), type=rt, offset=match(tp, (rd, rt))))
    turns = pd.DataFrame(turns); turns.to_csv(RES / "turning_points_all.csv", index=False)
    mt = pd.DataFrame(rows); mt.to_csv(RES / "match_to_reference.csv", index=False)

    # 方法ごとのまとめ（基本ルール）
    base = mt[mt.rule == "base"].copy()
    pubo = base[base.method == "pub"].set_index(["series", "ref"]).offset
    summ = []
    for m in METHODS:
        b = base[base.method == m].set_index(["series", "ref"])
        o = b.offset
        both = pd.concat([o, pubo], axis=1, keys=["m", "p"]).dropna()
        dif = both.m - both.p
        tp = turns[(turns.method == m) & (turns.rule == "base")]
        n_extra = 0; years = 0
        for k in NAMES:
            s = SA[(k, m)].dropna(); years += len(s) / 12
            rr = refs_in(SA[(k, "pub")])
            for _, r in tp[tp.series == k].iterrows():
                d = pd.Timestamp(r.date + "-01")
                if not any(t == r.type and abs(months(d, rd)) <= 12 for rd, t in rr):
                    if s.index[0] + pd.DateOffset(months=12) <= d <= s.index[-1] - pd.DateOffset(months=12):
                        n_extra += 1
        summ.append(dict(method=m, label=MLAB[m], refs=len(o), matched=int(o.notna().sum()),
                         median_offset=float(o.median()), mae=float(o.abs().mean()),
                         peak_median=float(b[b.type == "peak"].offset.median()), trough_median=float(b[b.type == "trough"].offset.median()),
                         same_as_pub=float((dif == 0).mean()) if m != "pub" else 1.0,
                         within1_pub=float((dif.abs() <= 1).mean()) if m != "pub" else 1.0,
                         within3_pub=float((dif.abs() <= 3).mean()) if m != "pub" else 1.0,
                         n_vs_pub=int(len(dif)), mean_shift_vs_pub=float(dif.mean()) if len(dif) else np.nan,
                         extra_per10y=10 * n_extra / years))
    summ = pd.DataFrame(summ); summ.to_csv(RES / "summary_by_method.csv", index=False)

    # 季節調整4方法のずれの幅（基準日付ごと）と、判定ルール5通りのずれの幅
    def spread(sub, by):
        p = sub.pivot_table(index=["series", "ref", "type"], columns=by, values="offset")
        full = p.dropna()
        return (full.max(axis=1) - full.min(axis=1)), len(p), len(full)
    sp_m, n_m, nf_m = spread(base[base.method.isin(SA4)], "method")
    sp_r, n_r, nf_r = spread(mt[mt.method == "pub"], "rule")
    sp_r2, _, _ = spread(mt[mt.method == "x11"], "rule")
    def dist(sp):
        return dict(n=int(len(sp)), zero=float((sp == 0).mean()), le1=float((sp <= 1).mean()), le3=float((sp <= 3).mean()), gt3=float((sp > 3).mean()), median=float(sp.median()), max=float(sp.max()))
    spread_tab = pd.DataFrame({"季節調整4方法（基本ルール）": dist(sp_m), "判定ルール5通り（公表値）": dist(sp_r), "判定ルール5通り（X-11法）": dist(sp_r2)}).T
    spread_tab.to_csv(RES / "spread_methods_vs_rules.csv")
    sp_m.rename("spread").reset_index().to_csv(RES / "spread_by_reference_point.csv", index=False)

    # 前年比と公表値の差（同じ基準日付で両方が見つかったもの）
    both = base[base.method.isin(["pub", "yoy"])].pivot_table(index=["series", "ref", "type"], columns="method", values="offset").dropna()
    d = both.yoy - both.pub
    from scipy.stats import binomtest, wilcoxon
    yoyres = dict(n=int(len(d)), median=float(d.median()), mean=float(d.mean()), earlier=int((d < 0).sum()), later=int((d > 0).sum()), same=int((d == 0).sum()),
                  sign_p=float(binomtest(int((d < 0).sum()), int((d != 0).sum())).pvalue),
                  peak_median=float(d[d.index.get_level_values("type") == "peak"].median()), trough_median=float(d[d.index.get_level_values("type") == "trough"].median()))
    # 2×12移動平均と公表値
    both2 = base[base.method.isin(["pub", "ma12"])].pivot_table(index=["series", "ref", "type"], columns="method", values="offset").dropna()
    d2 = both2.ma12 - both2.pub
    yoyres["ma12_vs_pub_median"] = float(d2.median()); yoyres["ma12_vs_pub_n"] = int(len(d2)); yoyres["ma12_vs_pub_mae"] = float(d2.abs().mean())
    json.dump(yoyres, open(RES / "yoy_vs_pub.json", "w"), ensure_ascii=False, indent=1)

    # 系列ごと・基準日付ごとの判定月（基本ルール）
    wide_t = base.pivot_table(index=["series", "ref", "type"], columns="method", values="offset")[METHODS]
    wide_t.to_csv(RES / "offset_table_base.csv")
    print(summ.round(2).to_string()); print(spread_tab.round(2)); print(yoyres)

    # 方法どうし（2つずつ）の一致
    pw = []
    for a, b in itertools.combinations(["pub", "x11", "seats", "stl7", "stl13", "stl35"], 2):
        d = wide_t[[a, b]].dropna(); x = (d[a] - d[b]).abs()
        pw.append(dict(a=MLAB[a], b=MLAB[b], n=len(d), same=float((x == 0).mean()), within1=float((x <= 1).mean()), gt3=float((x > 3).mean())))
    pd.DataFrame(pw).to_csv(RES / "pairwise_agreement.csv", index=False)
