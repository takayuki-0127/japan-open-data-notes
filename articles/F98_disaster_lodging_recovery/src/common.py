"""F98 共通：パス・事例の定義・推定の関数"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
RAW, DATA, RES, FIG = ROOT / "data/raw", ROOT / "data", ROOT / "results", ROOT / "figures"
SEED = 98

# 事例：開始月（その月から「事後」）、宿泊者数を見る県、公表情報にもとづく名前
EVENTS = {
    "E1": dict(name="熊本地震", start="2016-04", tr=["43熊本県", "44大分県"]),
    "E2": dict(name="平成30年7月豪雨", start="2018-07", tr=["33岡山県", "34広島県", "38愛媛県"]),
    "E3": dict(name="北海道胆振東部地震", start="2018-09", tr=["01北海道"]),
    "E4": dict(name="能登半島地震", start="2024-01", tr=["17石川県"], seas=("2017-01", "2019-12")),
}
EXTRA = {  # 頑健性：事例を増やす
    "E5": dict(name="平成29年7月九州北部豪雨", start="2017-07", tr=["40福岡県", "44大分県"]),
}
# 対照から外す、ほかの大きな出来事（新幹線の開業）：開始月と県
OTHER = [("2015-03", ["15新潟県", "16富山県", "17石川県", "20長野県"]),
         ("2016-03", ["01北海道", "02青森県"]),
         ("2024-03", ["17石川県", "18福井県"])]
COVID_END = "2020-01"   # コロナ前の事例は 2020年1月までで切る
PRE, H = 24, 16          # 事前24か月、事後16か月（k=0..16）


def load(series="japanese"):
    d = pd.read_csv(DATA / "panel.csv", parse_dates=["date"])
    y = d.pivot(index="date", columns="pref", values=series)
    return np.log(y)


def adj_map():
    p = pd.read_csv(RAW / "pairs.csv")
    names = pd.read_csv(DATA / "panel.csv", usecols=["pref"]).pref.unique()
    code = {int(n[:2]): n for n in names}
    a = {}
    for r in p[p.adj == 1].itertuples():
        a.setdefault(code[r.o], set()).add(code[r.d])
    return a


def window(ev, pre=PRE, h=H):
    t0 = pd.Timestamp(ev["start"])
    lo, hi = t0 - pd.DateOffset(months=pre), t0 + pd.DateOffset(months=h)
    if t0 < pd.Timestamp("2020-01-01"):
        hi = min(hi, pd.Timestamp(COVID_END))
    return t0, lo, hi


def donors(ev, cols, pre=PRE, h=H, drop_adj=True, extra_drop=()):
    """対照：事例の県・隣の県・同じ期間にほかの災害や新幹線の開業があった県を除く"""
    t0, lo, hi = window(ev, pre, h)
    out = set(ev["tr"]) | set(extra_drop)
    if drop_adj:
        A = adj_map()
        for p in ev["tr"]:
            out |= A.get(p, set())
    for e in list(EVENTS.values()) + list(EXTRA.values()):
        if lo <= pd.Timestamp(e["start"]) <= hi:
            out |= set(e["tr"])
    for s, ps in OTHER:
        if lo <= pd.Timestamp(s) <= hi:
            out |= set(ps)
    return [c for c in cols if c not in out and c != "全国"]


def deseason(y, t0, lo, seas=None):
    """事前期間の同じ月の平均を引く（県ごと）。seas=(始,終) なら、その期間の同じ月の平均を引く
    （能登半島地震は事前が2023年の12か月しかなく、それで季節を引くと事前の差が全部0になるため、コロナ前の2017〜2019年の季節の形を使う）"""
    pre = y[(y.index >= lo) & (y.index < t0)] if seas is None else y[(y.index >= seas[0]) & (y.index <= seas[1])]
    m = pre.groupby(pre.index.month).mean()
    return y - m.loc[y.index.month].values


def _simplex(f, n):
    r = minimize(f, np.full(n, 1 / n), method="SLSQP", bounds=[(0, 1)] * n,
                 constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(r.x, 0, None)
    return w / w.sum()


def effect(y, tr, dn, t0, lo, hi, how="mean", seas=None):
    """k（開始月からの月数）ごとの差。tr はリスト（平均をとる）。how: mean=対照の単純平均, scm=合成コントロール"""
    s = deseason(y, t0, lo, seas)
    s = s[(s.index >= lo) & (s.index <= hi)]
    x1 = s[tr].mean(axis=1)
    if how == "scm":
        pre = s.index < t0
        X0 = s.loc[pre, dn].values
        w = _simplex(lambda w: ((x1[pre].values - X0 @ w) ** 2).sum(), len(dn))
        x0 = pd.Series(s[dn].values @ w, s.index)
    else:
        x0 = s[dn].mean(axis=1)
    g = x1 - x0
    g = g - g[g.index < t0].mean()
    k = ((g.index.year - t0.year) * 12 + g.index.month - t0.month)
    return pd.Series(g.values, index=k)


def placebo(y, ntr, dn, t0, lo, hi, how="mean", draws=400, seed=SEED, seas=None):
    """対照の県から ntr 県を選んで「被災した」とみなす（ntr=1 は全県1つずつ）"""
    rng = np.random.default_rng(seed)
    out = []
    if ntr == 1:
        sets = [[c] for c in dn]
    else:
        sets = [list(rng.choice(dn, ntr, replace=False)) for _ in range(draws)]
    for st in sets:
        rest = [c for c in dn if c not in st]
        out.append(effect(y, st, rest, t0, lo, hi, how, seas))
    return pd.concat(out, axis=1)


def recovery(e, thr=0.05, run=3, band=None):
    """開始月以降で、差が -thr 以上（band があれば帯の下限以上）に run か月続けて戻った最初の k"""
    post = e[e.index >= 0]
    lim = (-thr if band is None else band.reindex(post.index))
    ok = (post >= lim).values
    for i in range(len(ok) - run + 1):
        if ok[i:i + run].all():
            return int(post.index[i])
    return None
