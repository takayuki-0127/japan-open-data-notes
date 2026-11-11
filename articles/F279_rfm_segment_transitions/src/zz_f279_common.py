"""共通：RFM の点数と区分、時点ごとの表を作る。"""
import pathlib, numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
SEGS = ["Champions", "Loyal", "Potential loyalist", "New", "Promising", "Need attention",
        "About to sleep", "At risk", "Can't lose", "Hibernating"]
JA = {"Champions": "最優良", "Loyal": "常連", "Potential loyalist": "常連候補", "New": "新規",
      "Promising": "見込み", "Need attention": "要注意", "About to sleep": "休眠寸前",
      "At risk": "離れかけ", "Can't lose": "失えない", "Hibernating": "休眠"}
SNAPS = pd.date_range("2010-12-01", "2011-06-01", freq="MS")

def load(gross=False):
    inv = pd.read_csv(ROOT / "data" / "processed" / "invoices.csv.gz", parse_dates=["date"])
    if gross: inv = inv[~inv["cancel"]]
    return inv

def segment(r, f):
    """計画の表を、書いた順に最初に当てはまる区分で割り当てる（表に重なりがあったため）。"""
    if r >= 4 and f >= 4: return "Champions"
    if r >= 3 and f >= 3: return "Loyal"
    if r >= 4 and f in (2, 3): return "Potential loyalist"
    if r == 5 and f == 1: return "New"
    if r == 4 and f == 1: return "Promising"
    if r == 3 and f in (2, 3): return "Need attention"
    if r == 3 and f == 1: return "About to sleep"
    if r <= 2 and f in (3, 4): return "At risk"
    if r <= 2 and f == 5: return "Can't lose"
    return "Hibernating"

def q5(x, ascending=True):
    """五分位の点（1〜5）。同じ値は顧客IDの順で並べてから分ける（決まった順にするため）。"""
    rk = x.rank(method="first", ascending=ascending)
    return pd.qcut(rk, 5, labels=[1, 2, 3, 4, 5]).astype(int)

def fixed_scores(R, F):
    r = pd.cut(R, [-1, 30, 90, 180, 270, 10**6], labels=[5, 4, 3, 2, 1]).astype(int)
    f = pd.cut(F, [0, 1, 2, 4, 8, 10**6], labels=[1, 2, 3, 4, 5]).astype(int)
    return r, f

def snapshot(inv, t, back=12, fwd=6, fixed=False, uk=False, drop_top=False):
    t = pd.Timestamp(t)
    past = inv[(inv["date"] >= t - pd.DateOffset(months=back)) & (inv["date"] < t)]
    fut = inv[(inv["date"] >= t) & (inv["date"] < t + pd.DateOffset(months=fwd))]
    buys = past[~past["cancel"]]
    g = buys.groupby("cust").agg(last=("date", "max"), F=("Invoice", "nunique"), country=("country", "last"))
    g["M"] = past.groupby("cust")["amount"].sum().reindex(g.index).fillna(0)
    g["R"] = (t - g["last"]).dt.days
    if uk: g = g[g["country"] == "United Kingdom"]
    if drop_top: g = g[g["M"] < g["M"].quantile(0.99)]
    g = g.sort_index()
    if fixed:
        g["r"], g["f"] = fixed_scores(g["R"], g["F"])
        g["m"] = q5(g["M"])
    else:
        g["r"] = q5(g["R"], ascending=False); g["f"] = q5(g["F"]); g["m"] = q5(g["M"])
    g["seg"] = [segment(a, b) for a, b in zip(g["r"], g["f"])]
    fb = fut[~fut["cancel"]]
    g["rebuy"] = g.index.isin(fb["cust"].unique())
    g["fut"] = fut.groupby("cust")["amount"].sum().reindex(g.index).fillna(0)
    g["t"] = t
    return g

def capture(g, score, frac=0.2):
    n = int(np.ceil(frac * len(g)))
    tot = g["fut"].sum()
    top = g.sort_values(score, ascending=False, kind="mergesort").head(n)
    return top["fut"].sum() / tot
