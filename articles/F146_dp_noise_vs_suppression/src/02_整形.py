"""02 整形：F61（検診・死亡）と F20（出生率の回帰）の集計表から、この記事で使う列だけを取り出す"""
import numpy as np
import pandas as pd
from common import RAW, DATA

# 1) 検診（大腸がん・肺がん、国保40〜69歳、1,656市区町村×4年度）
s = pd.read_csv(RAW / "f61_screening.csv", dtype={"code": str})
s = s[["code", "pref", "year", "n_colon", "y_colon", "n_lung", "y_lung"]].dropna()
s.to_csv(DATA / "screening.csv", index=False)

# 2) 死亡（2018〜22年、1,887地域）。期待死亡数 E は公表の人口から計算される値として、ノイズを入れない
m = pd.read_csv(RAW / "f61_smr.csv", dtype={"code": str})
m = m[["code", "pref", "O_all", "E_all", "O_heart", "E_heart", "O_stroke", "E_stroke"]]
m.to_csv(DATA / "deaths.csv", index=False)

# 3) 出生率の回帰（F20 と同じ説明変数）。人数の列（総人口・15〜39歳女性の数）を作る
f = pd.read_csv(RAW / "f20_municipal_2018_22.csv", dtype={"code": str, "pref": str})
X = ["young_f", "income", "commute_out", "nursery", "tertiary", "density"]
f = f[f["pop"] > 0].replace([np.inf, -np.inf], np.nan).dropna(subset=["tfr"] + X)
f["n_young_f"] = f["young_f"] / 100 * f["pop"]          # 15〜39歳女性の数
f["area"] = f["pop"] / np.exp(f["density"])              # 可住地面積（人口÷密度で戻す。公表値として扱う）
f[["code", "pref", "tfr", "pop", "n_young_f", "area"] + X].to_csv(DATA / "tfr_reg.csv", index=False)

print(len(s), len(m), len(f))
