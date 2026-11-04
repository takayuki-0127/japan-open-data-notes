"""F65・F114・F80 のデータ（コミット 111c020 で固定）から、分析用の表を作る"""
import numpy as np
import pandas as pd
from common import DATA, EXCLUDE_PREFIX, EXCLUDE_CODES

f65 = pd.read_csv(DATA / "f65_pref_panel.csv")
f114 = pd.read_csv(DATA / "f114_pref_2024.csv").rename(columns={"pref": "pref_code"})
names = f65[["pref_code", "pref"]]

# 回帰A（F114）：対数の物価地域差指数 ～ 対数の所得（課税対象所得÷納税義務者数、2024年）
a = f114[["pref_code", "inc", "price"]].merge(names, on="pref_code")
a["ln_inc"], a["ln_price"] = np.log(a.inc), np.log(a.price / 100)

# 回帰B（F65）：平均寿命（2015年、男女） ～ 医師数（2010年）、調整なし／DAG の最小セット＋気温・失業
cols = ["pref_code", "doctors", "did", "income", "univ_grad", "aged65", "temp", "unemp", "e0_m_2015", "e0_f_2015"]
b = f65[cols].copy()
master = a[["pref_code", "pref", "ln_inc", "ln_price"]].merge(b, on="pref_code")
assert len(master) == 47 and master.notna().all().all()
master.to_csv(DATA / "pref_master.csv", index=False)

# F80 の100指標から、扱わない題材を除いた指標
ch = pd.read_csv(DATA / "f80_chosen_100.csv")
meta = pd.read_csv(DATA / "f80_indicator_meta.csv")
keep = [c for c in ch.code if not c.startswith(EXCLUDE_PREFIX) and c not in EXCLUDE_CODES]
ind = pd.read_csv(DATA / "f80_indicators_2026.csv")[["pref_code"] + keep]
assert ind.notna().all().all(), ind.isna().sum()[ind.isna().sum() > 0]
ind.to_csv(DATA / "f80_sweep_indicators.csv", index=False)
meta[meta.code.isin(keep)].to_csv(DATA / "f80_sweep_meta.csv", index=False)
print("master", master.shape, "sweep indicators", len(keep), "pairs", len(keep) * (len(keep) - 1) // 2)
