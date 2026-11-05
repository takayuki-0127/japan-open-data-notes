"""季節調整（X-13・STL など）と、山谷の判定（Bry–Boschan を簡略にしたもの）の共通関数。"""
import os, subprocess, tempfile, pathlib
import numpy as np, pandas as pd
from statsmodels.tsa.seasonal import STL

ROOT = pathlib.Path(__file__).resolve().parent.parent
X13 = os.environ.get("X13PATH", "x13as")


def _read_x13(path):
    vals = []
    for line in open(path, encoding="latin-1").read().splitlines()[2:]:
        p = line.split()
        if len(p) >= 2:
            vals.append(float(p[1]))
    return np.array(vals)


def x13(s, mode="x11", outlier=True, log=True, td=False):
    """s: 月次の pd.Series（DatetimeIndex）。X-13ARIMA-SEATS で季節調整値を返す。"""
    s = s.dropna()
    st = s.index[0]
    vals = [f"{v:.6f}" for v in s.values]
    data = "\n".join(" ".join(vals[i:i + 8]) for i in range(0, len(vals), 8))
    spec = [f"series{{ start={st.year}.{st.month:02d} period=12\n data=(\n{data}\n) }}",
            "transform{ function=%s }" % ("log" if log else "none"),
            "automdl{ }"]
    if td:
        spec.append("regression{ variables=(td) }")
    if outlier:
        spec.append("outlier{ }")
    if mode == "x11":
        spec.append("x11{ save=(d11) }")
        ext = "d11"
    else:
        spec.append("seats{ save=(s11) }")
        ext = "s11"
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "s.spc"
        f.write_text("\n".join(spec))
        subprocess.run([X13, str(f.with_suffix(""))], cwd=d, capture_output=True, check=False)
        out = pathlib.Path(d) / f"s.{ext}"
        if not out.exists():
            return None
        v = _read_x13(out)
    return pd.Series(v[: len(s)], index=s.index)


def stl(s, seasonal=13, log=True):
    s = s.dropna()
    y = np.log(s) if log else s
    r = STL(y, period=12, seasonal=seasonal, robust=True).fit()
    sa = y - r.seasonal
    return np.exp(sa) if log else sa


def yoy(s):
    s = s.dropna()
    return (np.log(s) - np.log(s.shift(12))) * 100


def ma12(s):
    s = s.dropna()
    return s.rolling(12, center=True).mean().rolling(2).mean().shift(-1)


def bb(x, w=5, min_phase=6, min_cycle=15, end=6, smooth=0):
    """簡略版 Bry–Boschan。x: 上＝良い向きの月次系列。戻り値: [(Timestamp, 'peak'|'trough'), ...]"""
    x = x.dropna()
    if smooth:
        x = x.rolling(smooth, center=True).mean().dropna()
    v = x.values
    n = len(v)
    cand = []
    for i in range(w, n - w):
        win = v[i - w: i + w + 1]
        if v[i] == win.max():
            cand.append([i, "peak"])
        elif v[i] == win.min():
            cand.append([i, "trough"])
    # 交互にする（同じ種類が続いたら、より高い山・より低い谷を残す）
    def alternate(c):
        out = []
        for i, t in c:
            if out and out[-1][1] == t:
                j = out[-1][0]
                if (t == "peak" and v[i] > v[j]) or (t == "trough" and v[i] < v[j]):
                    out[-1] = [i, t]
            else:
                out.append([i, t])
        return out
    c = alternate(cand)
    # 端の近くは除く
    c = [p for p in c if end <= p[0] <= n - 1 - end]
    c = alternate(c)
    # 短すぎる局面・循環を除く（いちばん短いものから1つずつ）
    while len(c) > 2:
        c = alternate(c)
        ph = [(c[k + 1][0] - c[k][0], k) for k in range(len(c) - 1)]
        m, k = min(ph)
        if m < min_phase:
            # 短い局面の両端のどちらを消すかは、消したあとの振れ幅の合計が大きく残る方にする
            def swing(cc):
                cc = alternate(cc)
                return sum(abs(v[cc[q + 1][0]] - v[cc[q][0]]) for q in range(len(cc) - 1))
            opt = [c[:k] + c[k + 1:], c[:k + 1] + c[k + 2:], c[:k] + c[k + 2:]]
            c = max(opt, key=swing)
            continue
        cy = [(c[k + 2][0] - c[k][0], k) for k in range(len(c) - 2)]
        if not cy:
            break
        m, k = min(cy)
        if m < min_cycle:
            i, j = c[k][0], c[k + 2][0]
            t = c[k][1]
            weaker = k if ((t == "peak" and v[i] < v[j]) or (t == "trough" and v[i] > v[j])) else k + 2
            del c[weaker]
            continue
        break
    c = alternate(c)
    return [(x.index[i], t) for i, t in c]


def match(turns, ref, window=12):
    """基準日付 ref (Timestamp, type) に対し、同じ種類で ±window か月以内のいちばん近い点との差（か月）。"""
    best = None
    for d, t in turns:
        if t != ref[1]:
            continue
        diff = (d.year - ref[0].year) * 12 + d.month - ref[0].month
        if abs(diff) <= window and (best is None or abs(diff) < abs(best)):
            best = diff
    return best
