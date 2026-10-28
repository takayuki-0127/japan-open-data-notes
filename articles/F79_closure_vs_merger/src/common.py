from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110


import numpy as np, pandas as pd
H = np.arange(0, 11.01, 0.25)

def aj(T, cause, grid=H):
    """Aalen–Johansen: 2つのイベント（1,2）の CIF と全体の生存を grid 上で返す"""
    t = np.round(T * 365.25).astype(int)
    df = pd.DataFrame({"t": t, "c": cause})
    g = df.groupby("t").c.agg([("n", "size"), ("e1", lambda x: (x == 1).sum()), ("e2", lambda x: (x == 2).sum())])
    g = g.sort_index()
    at_risk = g.n[::-1].cumsum()[::-1]
    S_prev = np.concatenate([[1.0], np.cumprod(1 - (g.e1 + g.e2) / at_risk)[:-1]])
    F1 = np.cumsum(S_prev * g.e1 / at_risk); F2 = np.cumsum(S_prev * g.e2 / at_risk)
    S = np.cumprod(1 - (g.e1 + g.e2) / at_risk)
    KM1 = 1 - np.cumprod(1 - g.e1 / at_risk)   # 合併を打ち切りとみなした 1−KM
    days = g.index.values
    res = {}
    for name, arr in [("F1", F1), ("F2", F2), ("S", S), ("KM1", KM1)]:
        arr = np.asarray(arr)
        idx = np.searchsorted(days, np.round(grid * 365.25), side="right") - 1
        res[name] = np.where(idx >= 0, arr[np.clip(idx, 0, None)], 0.0)
    return pd.DataFrame(res, index=grid)

