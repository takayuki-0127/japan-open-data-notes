"""共通の設定（パス・フォント・指標の作り方・転換点の判定）"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 63

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 比べる「見方」
IND = ["前年比", "前月比", "3か月前比", "前年比の前月差"]
COL = {"前年比": "#d93025", "前月比": "#9aa0a6", "3か月前比": "#1a73e8", "前年比の前月差": "#e37400"}

# 系列：名前 → (変化の取り方, 良い向き)。"pct" は変化率（%）、"diff" は差（ポイント）。
# 良い向きが -1 のもの（失業率）は符号を逆にして「プラス＝良くなった」にそろえる。
SERIES = {
    "鉱工業生産": ("pct", 1),
    "就業者": ("pct", 1),
    "完全失業率": ("diff", -1),
    "有効求人倍率": ("diff", 1),
    "景気動向指数（CI一致）": ("pct", 1),
}


def change(s, lag, kind):
    if kind == "pct":
        return (s / s.shift(lag) - 1) * 100
    return s - s.shift(lag)


def indicators(nsa, sa, kind, sign=1):
    """4つの見方を作る。前年比と前年比の前月差は原数値（NSA）、ほかは季節調整値（SA）から。
    参考として「3か月平均の前月比」も作る（符号は3か月前比とほぼ同じになる）。
    NSA がない系列（CI）は前年比も SA から作る。符号は「プラス＝良くなった」にそろえる。"""
    base_yoy = nsa if nsa is not None and nsa.notna().sum() > 24 else sa
    ma3 = sa.rolling(3).mean()
    yoy = change(base_yoy, 12, kind)
    out = pd.DataFrame({
        "前年比": yoy,
        "前月比": change(sa, 1, kind),
        "3か月前比": change(sa, 3, kind),
        "前年比の前月差": yoy.diff(),
        "3か月平均の前月比": change(ma3, 1, kind),
    })
    return out * sign


def detect(sig, date, direction, k=2, before=0, after=24):
    """転換点 date のあと（before か月前から after か月後まで）で、
    sig が direction（-1：マイナス、+1：プラス）の向きに k か月続いた最初の月を返す。
    戻り値は「転換点から何か月後に分かったか」（見つからなければ NaN）。"""
    s = np.sign(sig.dropna())
    s = s[(s.index >= date - pd.DateOffset(months=before)) & (s.index <= date + pd.DateOffset(months=after))]
    run = 0
    for t, v in s.items():
        run = run + 1 if v == direction else 0
        if run >= k:
            return (t.year - date.year) * 12 + (t.month - date.month)
    return np.nan


def false_alarms(sig, phases, k=2, guard=6):
    """局面と逆の向きの「k か月続いたサイン」が、転換点から guard か月以上離れた月に何回出たか。
    phases: 月ごとの局面（+1 拡張、-1 後退）と、最寄りの転換点までの月数の列を持つ DataFrame。
    戻り値：(誤ったサインの回数, 数えた年数)"""
    d = pd.concat([np.sign(sig).rename("s"), phases], axis=1).dropna()
    n, run, prev_ok = 0, 0, False
    for _, r in d.iterrows():
        wrong = (r["s"] == -r["phase"]) and (r["dist"] >= guard)
        run = run + 1 if wrong else 0
        if run == k:
            n += 1
    return n, len(d) / 12


def cycle_table():
    c = pd.read_csv(RAW / "cycle_dates.csv")
    c["date"] = pd.to_datetime(c["month"] + "-01")
    return c[["type", "date"]]


def phase_frame(index):
    """月ごとの局面（山の翌月〜谷を後退＝-1、それ以外を拡張＝+1）と、最寄りの転換点までの月数"""
    c = cycle_table()
    ph = pd.Series(1.0, index=index)
    peaks = c[c.type == "peak"].date.tolist()
    troughs = c[c.type == "trough"].date.tolist()
    for p in peaks:
        nxt = [t for t in troughs if t > p]
        if nxt:
            ph[(index > p) & (index <= nxt[0])] = -1
    tp = c.date.values
    dist = pd.Series([np.min(np.abs((np.array(tp, dtype="datetime64[M]") - np.datetime64(t, "M")).astype(int))) for t in index],
                     index=index, dtype=float)
    return pd.DataFrame({"phase": ph, "dist": dist})
