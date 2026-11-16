"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "koyouhoken_by_industry.csv")
NAMES = d[d.fy == d.fy.max()].set_index("code").name.to_dict()
N = d.pivot(index="fy", columns="code", values="new"); C = d.pivot(index="fy", columns="code", values="closed"); S = d.pivot(index="fy", columns="code", values="stock_end")
Y = list(range(2018, 2026))
IND = [c for c in N.columns if c not in ("TOTAL", "Ｓ", "Ｔ")]
rate = 100 * N.loc[Y] / S.shift(1).loc[Y]
crate = 100 * C.loc[Y] / S.shift(1).loc[Y]
rate.round(4).to_csv(RES / "startup_rate_by_industry.csv"); crate.round(4).to_csv(RES / "closure_rate_by_industry.csv")
out = {"rate_by_fy": {int(y): r3(rate.loc[y, "TOTAL"]) for y in Y}, "closure_by_fy": {int(y): r3(crate.loc[y, "TOTAL"]) for y in Y}}
out["H1"] = dict(mean=r3(rate.loc[Y, "TOTAL"].mean()), min=r3(rate.loc[Y, "TOTAL"].min()), max=r3(rate.loc[Y, "TOTAL"].max()))
out["H1_verdict"] = "支持" if out["H1"]["mean"] < 5 else "外れ"
ind_mean = rate[IND].mean().sort_values(ascending=False)
out["industry_mean_rate"] = {f"{c} {NAMES[c]}": r3(v) for c, v in ind_mean.items()}
out["H2"] = dict(top=f"{ind_mean.index[0]} {NAMES[ind_mean.index[0]]}", top_rate=r3(ind_mean.iloc[0]), construction=r3(ind_mean["Ｄ"]))
out["H2_verdict"] = "支持" if ind_mean.index[0] == "Ｄ" else "外れ"
ex = 100 * (N.loc[Y, "TOTAL"] - N.loc[Y, "Ｄ"]) / (S.shift(1).loc[Y, "TOTAL"] - S.shift(1).loc[Y, "Ｄ"])
out["H3"] = dict(ex_construction_mean=r3(ex.mean()), diff=r3(ex.mean() - rate.loc[Y, "TOTAL"].mean()))
out["H3_verdict"] = "支持" if out["H3"]["diff"] <= -0.3 else "外れ"
eq = rate.loc[Y, IND].mean(axis=1)
out["H4"] = dict(equal_weight_mean=r3(eq.mean()), actual_mean=r3(rate.loc[Y, "TOTAL"].mean()), diff=r3(eq.mean() - rate.loc[Y, "TOTAL"].mean()))
out["H4_verdict"] = "支持" if abs(out["H4"]["diff"]) >= 0.5 else "外れ"
avgden = 100 * N.loc[Y, "TOTAL"] / ((S.shift(1).loc[Y, "TOTAL"] + S.loc[Y, "TOTAL"]) / 2)
w = S.loc[2017, IND] / S.loc[2017, IND].sum()
fixed = (rate.loc[Y, IND] * w).sum(axis=1)
noncov = [y for y in Y if y not in (2020, 2021)]
rob = [dict(spec="R1 分母を年度の初めと終わりの平均に", mean=r3(avgden.mean())),
       dict(spec="R2 令和2・3年度を除く", mean=r3(rate.loc[noncov, "TOTAL"].mean())),
       dict(spec="R3 産業の構成を平成29年度末に固定", mean=r3(fixed.mean()), diff_from_actual=r3(fixed.mean() - rate.loc[Y, "TOTAL"].mean())),
       dict(spec="R4 純増の率（開業率−廃業率）", mean=r3((rate.loc[Y, "TOTAL"] - crate.loc[Y, "TOTAL"]).mean())),
       dict(spec="R5 任意適用を分子から除く", mean=r3((100 * (N.loc[Y, "TOTAL"] - d[d.code == "TOTAL"].set_index("fy").new_voluntary.loc[Y]) / S.shift(1).loc[Y, "TOTAL"]).mean()))]
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(N[["TOTAL", "Ｄ", "Ｍ", "Ｉ"]].to_string())
