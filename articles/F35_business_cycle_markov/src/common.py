"""共通の設定（パス・フォント・乱数の種・景気基準日付の読み込み）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # 結果を毎回同じにするため1スレッドで計算する
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
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110


def cycle_dates():
    """景気基準日付（山・谷）を読み、山の翌月〜谷を後退期とする月次の 0/1 を返す"""
    c = pd.read_csv(RAW / "cycle_dates.csv")
    c["month"] = pd.to_datetime(c["month"])
    return c


def recession_flag(index):
    c = cycle_dates()
    flag = pd.Series(0, index=index)
    peaks = c[c.type == "peak"].month.tolist()
    troughs = c[c.type == "trough"].month.tolist()
    for p in peaks:
        t = [x for x in troughs if x > p]
        end = t[0] if t else index.max()
        flag[(index > p) & (index <= end)] = 1
    return flag


def episodes(flag):
    """0/1 の列から、1 が続く区間（開始月, 終了月）の一覧を返す"""
    out, start = [], None
    prev = 0
    for m, v in flag.items():
        if v and not prev:
            start = m
        if not v and prev:
            out.append((start, last))
        prev, last = v, m
    if prev:
        out.append((start, last))
    return out
