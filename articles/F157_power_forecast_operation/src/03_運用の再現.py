"""03 運用の再現：毎日、翌日24時間の需要を予測する運用を1年分くり返し、再学習の間隔ごとに外れ方を比べる

- 予測する日 D の前日 D−1 の夜に、D の24時間を出す（F22 と同じ特徴量。気温は実測で代用）
- 再学習：しない（運用開始の前日までで1回）／四半期ごと／毎月／毎週／外れ方が悪化したら（監視ルール）
- 学習するデータは、その時点までに分かっている実績すべて（拡張ウィンドウ）。比べるために直近3年だけ（スライド）も
- 途中結果（学習の締め日ごとの予測）は CACHE に残し、止まってもやり直せるようにする
使い方：python 03_運用の再現.py <area> <運用開始日> <運用終了日> <run名...>
"""
import sys, pickle, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from common import F22DATA, RES, CACHE, SEED, LGB_FULL, LGB_LIGHT
from feat import make_features, ridge_matrix, LGB_FEATS

CACHE.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
AREA_FILE = {"tokyo": "hourly_tokyo.csv", "kansai": "hourly_kansai.csv"}
_D = {}


def load(area, noise=None):
    key = (area, noise)
    if key not in _D:
        raw = pd.read_csv(F22DATA / AREA_FILE[area], index_col="ts", parse_dates=True)
        shift = None
        if noise:  # 気温の予報誤差のかわりに、日ごとに N(0, noise) の誤差を足す（頑健性）
            days = pd.to_datetime(raw["date"]).drop_duplicates()
            rng = np.random.default_rng(SEED)
            shift = pd.Series(rng.normal(0, noise, len(days)), index=days.values)
        d = make_features(raw, tmean_shift=shift)
        _D[key] = d[d["lag168"].notna()]
    return _D[key]


def preds_from_cutoff(area, cutoff, end, model="light", window=None, noise=None):
    """cutoff（この日の0時より前）までで学習し、cutoff〜end の毎時を予測。キャッシュする"""
    tag = f"{area}_{model}_{pd.Timestamp(cutoff):%Y%m%d}_{pd.Timestamp(end):%Y%m%d}_{window or 'exp'}_{noise or 0}"
    f = CACHE / f"{tag}.pkl"
    if f.exists():
        return pickle.load(open(f, "rb"))
    d = load(area, noise)
    tr = d.index < cutoff
    if window:
        tr &= d.index >= pd.Timestamp(cutoff) - pd.DateOffset(years=window)
    te = (d.index >= cutoff) & (d.index <= pd.Timestamp(end) + pd.Timedelta(hours=23))
    t = time.time()
    if model == "ridge":
        X = ridge_matrix(d)
        m = make_pipeline(StandardScaler(), Ridge(alpha=3.0)).fit(X[tr], d.loc[tr, "demand"])
        p = pd.Series(m.predict(X[te]), index=d.index[te])
    else:
        prm = LGB_FULL if model == "full" else LGB_LIGHT
        m = lgb.LGBMRegressor(**prm).fit(d.loc[tr, LGB_FEATS], d.loc[tr, "demand"])
        p = pd.Series(m.predict(d.loc[te, LGB_FEATS]), index=d.index[te])
    pickle.dump(p, open(f, "wb"))
    print(f"  fit {tag} n={tr.sum()} {time.time()-t:.0f}s", flush=True)
    return p


def schedule(area, start, end, cutoffs, **kw):
    """再学習の日付の並び（最初は start）から、運用1年分の予測をつなぐ"""
    cutoffs = sorted(pd.Timestamp(c) for c in cutoffs)
    parts = []
    for i, c in enumerate(cutoffs):
        nxt = cutoffs[i + 1] if i + 1 < len(cutoffs) else pd.Timestamp(end) + pd.Timedelta(days=1)
        p = preds_from_cutoff(area, c, end, **kw)
        parts.append(p[(p.index >= c) & (p.index < nxt)])
    return pd.concat(parts)


def triggered(area, start, end, mape_thr=2.0, bias_thr=1.0, min_gap=14, **kw):
    """監視ルール：直近14日の MAPE が mape_thr% を超えるか、直近7日の平均のずれ（符号つき）が ±bias_thr% を
    超えたら、その日の夜に学習し直す（前回から min_gap 日たっていること）。実績はその日の23時まで分かっている"""
    d = load(area, kw.get("noise"))
    days = pd.date_range(start, end)
    cur = pd.Timestamp(start); last = cur
    cut = [cur]
    p = preds_from_cutoff(area, cur, end, **kw)
    out, ape, bias = [], [], []
    for day in days:
        if day > cur and day == last:
            p = preds_from_cutoff(area, day, end, **kw)
        ph = p[(p.index >= day) & (p.index < day + pd.Timedelta(days=1))]
        a = d.loc[ph.index, "demand"]
        out.append(ph)
        ape.append(100 * ((ph - a).abs() / a).mean()); bias.append(100 * ((ph - a) / a).mean())
        since = (day - cut[-1]).days + 1
        if since >= min_gap and (np.mean(ape[-14:]) > mape_thr or abs(np.mean(bias[-7:])) > bias_thr):
            nxt = day + pd.Timedelta(days=1)
            if nxt <= pd.Timestamp(end):
                cut.append(nxt); last = nxt; cur = cut[0]
    return pd.concat(out), cut


def runs(area, start, end, which):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    month_starts = list(pd.date_range(start, end, freq="MS"))
    if start not in month_starts:
        month_starts = [start] + month_starts
    R, meta = {}, {}
    if "fixed" in which:
        R["固定（開始前に1回）"] = schedule(area, start, end, [start]); meta["固定（開始前に1回）"] = 1
    if "full" in which:
        R["固定・F22 と同じ設定（木900本）"] = schedule(area, start, end, [start], model="full"); meta["固定・F22 と同じ設定（木900本）"] = 1
    if "quarter" in which:
        cs = month_starts[::3]; R["四半期ごと"] = schedule(area, start, end, cs); meta["四半期ごと"] = len(cs)
    if "month" in which:
        R["毎月"] = schedule(area, start, end, month_starts); meta["毎月"] = len(month_starts)
    if "week" in which:
        cs = list(pd.date_range(start, end, freq="7D")); R["毎週"] = schedule(area, start, end, cs); meta["毎週"] = len(cs)
    if "trigger" in which:
        p, cut = triggered(area, start, end); R["監視ルールで"] = p; meta["監視ルールで"] = len(cut)
        meta["_trigger_dates"] = [str(c.date()) for c in cut]
    if "trigger_alt" in which:
        for mt, bt, lab in [(1.5, 0.75, "監視ルール（厳しめ）"), (2.5, 1.5, "監視ルール（ゆるめ）")]:
            p, cut = triggered(area, start, end, mape_thr=mt, bias_thr=bt); R[lab] = p; meta[lab] = len(cut)
            meta[f"_{lab}_dates"] = [str(c.date()) for c in cut]
    if "slide" in which:
        R["毎月・直近3年だけで学習"] = schedule(area, start, end, month_starts, window=3); meta["毎月・直近3年だけで学習"] = len(month_starts)
    if "age" in which:
        for k in (1, 2, 3):
            c = start - pd.DateOffset(years=k)
            R[f"固定・{k}年前に学習したまま"] = preds_from_cutoff(area, c, end).loc[start:]
            meta[f"固定・{k}年前に学習したまま"] = 1
    if "ridge" in which:
        R["線形回帰・固定"] = schedule(area, start, end, [start], model="ridge"); meta["線形回帰・固定"] = 1
        cs = list(pd.date_range(start, end, freq="D"))
        R["線形回帰・毎日"] = schedule(area, start, end, cs, model="ridge"); meta["線形回帰・毎日"] = len(cs)
    if "noise" in which:
        R["固定（気温に誤差）"] = schedule(area, start, end, [start], noise=1.5); meta["固定（気温に誤差）"] = 1
        R["毎月（気温に誤差）"] = schedule(area, start, end, month_starts, noise=1.5); meta["毎月（気温に誤差）"] = len(month_starts)
    d = load(area)
    idx = R[next(iter(R))].index
    P = pd.DataFrame({k: v.reindex(idx) for k, v in R.items()})
    P.insert(0, "1週間前の同じ時刻", d.loc[idx, "lag168"])
    P.insert(0, "actual", d.loc[idx, "demand"])
    return P, meta


if __name__ == "__main__":
    area, start, end, name = sys.argv[1:5]
    which = sys.argv[5:]
    P, meta = runs(area, start, end, which)
    P.to_csv(RES / f"pred_{name}.csv.gz", compression="gzip")
    pickle.dump(meta, open(CACHE / f"meta_{name}.pkl", "wb"))
    import json; json.dump(meta, open(RES / f"retrain_{name}.json", "w"), ensure_ascii=False, indent=1)
    a = P["actual"]
    for c in P.columns[1:]:
        print(f"{c:24s} MAPE {100*((P[c]-a).abs()/a).mean():.3f}%  回数 {meta.get(c, '-')}")
