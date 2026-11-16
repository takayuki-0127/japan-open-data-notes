"""問い直し（結果を見てから足した）。
Q：2020→25年の減少は、どの年齢での出入り（同じ生まれ年の人数の増減）から来ているのか。
   60代で新たに加わる人（変化率が1を超える分）が減ったら、2035年の推計はどれだけ変わるのか。
結果は results/requestion.json と results/requestion_flows.csv。"""
import json, pathlib, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
spec = importlib.util.spec_from_file_location("core", pathlib.Path(__file__).with_name("core.py"))
core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
AGES = core.AGES

out = {}
flows = []
for k, ((y0, b0), (y1, b1)) in core.PERIODS.items():
    n0, n1 = core.vec(y0, b0), core.vec(y1, b1)
    # 同じ生まれ年の人数の増減：5年後の a+5〜a+9 歳 − いまの a〜a+4 歳
    for j in range(1, 15):
        if j < 14:
            f = n1[j] - n0[j - 1]
        else:
            f = n1[14] - (n0[13] + n0[14])
        flows.append({"period": k, "age_after": AGES[j], "flow": float(f)})
    flows.append({"period": k, "age_after": "15-19（新しく数えられる層）", "flow": float(n1[0])})
    flows.append({"period": k, "age_after": "（参考）5年前の総数", "flow": float(n0.sum())})
fl = pd.DataFrame(flows)
fl.to_csv(R / "requestion_flows.csv", index=False)


def band(age):
    if age.startswith("15-19"):
        return "15〜19歳（新しく数えられる層）"
    if age.startswith("（参考）"):
        return None
    lo = int(age.split("-")[0].replace("+", ""))
    if lo <= 49:
        return "20〜49歳"
    if lo <= 64:
        return "50〜64歳"
    if lo <= 74:
        return "65〜74歳"
    return "75歳以上"


fl["band"] = fl["age_after"].map(band)
summ = fl.dropna(subset=["band"]).groupby(["period", "band"])["flow"].sum().unstack()
tot = fl[fl.age_after == "（参考）5年前の総数"].set_index("period")["flow"]
summ["net"] = summ.sum(axis=1)
summ["start_total"] = tot
summ.to_csv(R / "requestion_flow_bands.csv")
out["flow_bands"] = {p: {k: round(float(v)) for k, v in row.items()} for p, row in summ.iterrows()}

# 60代の加わり（60-64、65-69 歳の変化率）を弱める感度
n25 = core.vec(2025, "個人経営体")
base = core.rates()["2020-25"]
sens = []
for lab, f6064, f6569 in [("主の推計", None, None), ("60〜64歳の率を1.0に", 1.0, None),
                          ("60〜69歳の率を1.0に", 1.0, 1.0), ("60〜64歳の率を2005→10年の値に", core.rates()["2005-10"][9], None)]:
    r = base.copy()
    if f6064 is not None:
        r[9] = f6064
    if f6569 is not None:
        r[10] = f6569
    n = n25.copy()
    for _ in range(2):
        n = core.step(n, r)
    m = core.metrics(n)
    sens.append({"case": lab, "rate_60_64": round(float(r[9]), 3), "rate_65_69": round(float(r[10]), 3),
                 **{k: round(v, 2) for k, v in m.items()}})
sens = pd.DataFrame(sens)
sens.to_csv(R / "requestion_sensitivity.csv", index=False)
out["sensitivity_2035"] = sens.set_index("case").to_dict(orient="index")
with open(R / "requestion.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(summ.round(0).to_string())
print(sens.to_string())
