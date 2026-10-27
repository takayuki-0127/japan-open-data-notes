"""F38 共通：産業連関表（統合中分類）を読み、行列を作る。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)

IDS = {"2020": "000040187026", "2015": "000031839447"}
UNIT = {"2020": 1.0, "2015": 1e-3}   # 十億円にそろえる（2020は十億円、2015は百万円）


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load_table(year="2020"):
    """取引基本表（生産者価格評価、統合中分類）を辞書で返す。単位は十億円。"""
    d = json.load(open(RAW / "f38_io.json", encoding="utf-8"))[IDS[year]]
    a = list(d.values())[0]
    codes = a[1]; names = a[2]
    col = {}
    for j, (c, n) in enumerate(zip(codes, names)):
        if n:
            col[str(n)] = j
    endo_cols = [j for j, c in enumerate(codes) if c and str(c).isdigit() and len(str(c)) == 3 and str(c) < "700"]
    rows = {str(r[0]): r for r in a[3:] if r and r[0]}
    sec = [str(codes[j]) for j in endo_cols]
    nm = [str(names[j]) for j in endo_cols]
    u = UNIT[year]
    Z = np.array([[_num(rows[s][j]) for j in endo_cols] for s in sec]) * u
    X = np.array([_num(rows["970"][j]) for j in endo_cols]) * u
    W = np.array([_num(rows["911"][j]) for j in endo_cols]) * u
    VA = np.array([_num(rows["960"][j]) for j in endo_cols]) * u

    def fcol(name):
        j = col[name]
        return np.array([_num(rows[s][j]) for s in sec]) * u

    hh = fcol("民間消費支出")
    dom = fcol("国内需要合計")
    imp = -fcol("（控除）輸入計")
    exp_ = fcol("輸出計")
    return dict(sec=sec, name=nm, Z=Z, X=X, W=W, VA=VA, hh=hh, dom=dom, imp=imp, exp=exp_, year=year)


def matrices(t):
    X = t["X"]
    A = t["Z"] / np.where(X > 0, X, 1)[None, :]
    m = np.where(t["dom"] > 0, t["imp"] / t["dom"], 0)
    m = np.clip(m, 0, 1)
    n = len(X)
    I = np.eye(n)
    M = np.diag(m)
    B = np.linalg.inv(I - (I - M) @ A)      # 競争輸入型
    B0 = np.linalg.inv(I - A)               # 輸入を考えない（閉鎖型）
    w = t["W"] / np.where(X > 0, X, 1)
    v = t["VA"] / np.where(X > 0, X, 1)
    hh = t["hh"].copy()
    hh[t["sec"].index("553")] = 0.0   # 帰属家賃は2次波及の消費に入れない
    hh = np.clip(hh, 0, None); h = hh / hh.sum()
    return dict(A=A, m=m, M=M, B=B, B0=B0, w=w, v=v, h=h, I=I)


def employment_coef(t):
    """雇用表（2020、統合中分類）から 従業者数／国内生産額（人／十億円）。"""
    d = json.load(open(RAW / "f38_io.json", encoding="utf-8"))["000040187066"]
    a = list(d.values())[0]
    L = {str(r[0]): float(r[2]) for r in a if r and r[0] and str(r[0]).isdigit() and isinstance(r[2], (int, float))}
    return np.array([L.get(s, 0.0) for s in t["sec"]]) / np.where(t["X"] > 0, t["X"], 1)


def purchaser_shares(t):
    """家計消費で、購入者価格に占める生産者価格の割合と、マージンの商業・運輸への分け方（2020）。"""
    d = json.load(open(RAW / "f38_io_purch.json", encoding="utf-8"))["000040187031"]
    a = list(d.values())[0]
    codes = a[1]; names = a[2]
    col = {str(n): j for j, n in enumerate(names) if n}
    rows = {str(r[0]): r for r in a[3:] if r and r[0]}
    out = {}
    for i, s in enumerate(t["sec"]):
        r = rows.get(s)
        if r is None:
            continue
        hp = _num(r[col["民間消費支出"]])
        cm = _num(r[col["商業マージン"]]); fr = _num(r[col["貨物運賃"]])
        prod = t["hh"][i] / UNIT[t["year"]] if t["year"] != "2020" else t["hh"][i]
        out[s] = dict(purch=hp, prod=t["hh"][i], cm=cm, fr=fr)
    return out
