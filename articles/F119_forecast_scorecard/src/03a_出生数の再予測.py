"""F55 の 2026年予測（2016〜25年で学習した BSTS と SARIMA）を月ごとに出し直し、2026年1〜5月の概数と比べる

F55 の src/common.py をそのまま使う（同じ設定・同じ乱数の種）。結果は results/births_2026_sims.npz に保存。
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
F55 = ROOT.parent / "F55_births_bsts" / "src"
sys.path.insert(0, str(F55))
from common import monthly, fit_bsts, sim_bsts, sim_sarima, future_index, days_in  # noqa: E402

d = monthly()
y = d.loc["2016":"2025", "y"]
idx = future_index(y.index[-1], 12)
p = fit_bsts(y, draws=2500, tune=2000)          # F55 の C_main と同じ設定
sb = np.exp(sim_bsts(p, 12)) * days_in(idx)[:, None]
ss = np.exp(sim_sarima(y, 12)) * days_in(idx)[:, None]
np.savez_compressed(ROOT / "results" / "births_2026_sims.npz", bsts=sb.astype("float32"), sarima=ss.astype("float32"),
                    months=np.array([str(i)[:7] for i in idx]), rhat=p["rhat_max"])
print("rhat", p["rhat_max"], "BSTS 1-5月の中央値", np.median(sb[:5].sum(0)), "SARIMA", np.median(ss[:5].sum(0)))
