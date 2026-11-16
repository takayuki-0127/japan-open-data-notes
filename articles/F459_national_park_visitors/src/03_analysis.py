"""国立公園の利用者数の推移、公園をそろえた比較、2019→2024年の公園別、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
t = pd.read_csv(ROOT / "data" / "totals.csv").set_index("year")
p = pd.read_csv(ROOT / "data" / "parks.csv")
# 1991年からある公園に、名前の変更・分割をまとめ直す
MAP = {"三陸復興(陸中海岸)": "三陸復興", "三陸復興": "三陸復興", "西表": "西表(石垣)", "西表石垣": "西表(石垣)", "阿寒": "阿寒(摩周)", "阿寒摩周": "阿寒(摩周)",
       "霧島屋久": "霧島屋久(錦江湾・屋久島)", "霧島錦江湾": "霧島屋久(錦江湾・屋久島)", "屋久島": "霧島屋久(錦江湾・屋久島)", "尾瀬": "日光(尾瀬)", "日光": "日光(尾瀬)"}
p["park_name"] = p.park.str.replace("※", "", regex=False)
p["group"] = p.park_name.map(lambda x: MAP.get(x, x))
base = set(p[p.year == 1991].group)
q = p[p.group.isin(base)].groupby(["group", "year"]).users_10k.sum(min_count=1).unstack("year")
order = p[p.year == 1991].drop_duplicates("group").sort_values("no").group.tolist()
q = q.loc[order]
q.to_csv(R / "fixed_parks_10k.csv", float_format="%.1f")
fixed = q.sum()
npu = t.np_users / 1e4  # 万人
avg = lambda s, ys: float(s.loc[ys].mean())
main = {"np_peak_year": int(npu.idxmax()), "np_peak": round(float(npu.max())), "np_2024": round(float(npu.loc[2024])), "np_2019": round(float(npu.loc[2019])),
        "np_1991": round(float(npu.loc[1991])), "np_2020": round(float(npu.loc[2020])),
        "np_pct_peak_2024": round(float(npu.loc[2024] / npu.max() * 100 - 100), 1), "np_pct_2019_2024": round(float(npu.loc[2024] / npu.loc[2019] * 100 - 100), 1),
        "np_pct_1991_2024": round(float(npu.loc[2024] / npu.loc[1991] * 100 - 100), 1),
        "parks_1991": int(t.loc[1991, "np_n"]), "parks_2024": int(t.loc[2024, "np_n"]), "n_fixed": len(q),
        "fixed_1991": round(float(fixed.loc[1991])), "fixed_2024": round(float(fixed.loc[2024])), "fixed_2019": round(float(fixed.loc[2019])),
        "fixed_pct_1991_2024": round(float(fixed.loc[2024] / fixed.loc[1991] * 100 - 100), 1),
        "new_parks_2024": round(float(npu.loc[2024] - fixed.loc[2024]))}
d19 = (q[2024] / q[2019] - 1) * 100
main["n_fixed_down_2019_2024"] = int((d19 < 0).sum())
main["park_change_2019_2024"] = {k: round(float(v), 1) for k, v in d19.items()}
pd.DataFrame({"users_2019": q[2019], "users_2024": q[2024], "pct": d19}).to_csv(R / "fixed_parks_2019_2024.csv", float_format="%.2f")
main["hypotheses"] = {"H1": "支持" if main["np_pct_peak_2024"] <= -10 else "外れ", "H2": "支持" if main["fixed_pct_1991_2024"] < main["np_pct_1991_2024"] else "外れ",
                      "H3": "支持" if main["np_pct_2019_2024"] <= -5 else "外れ", "H4": "支持" if main["n_fixed_down_2019_2024"] > len(q) / 2 else "外れ"}
A, B = [1990, 1991, 1992, 1993, 1994], [2022, 2023, 2024]
rb = [dict(check="国立公園：1990〜94年平均→2022〜24年平均", value=round((avg(npu, B) / avg(npu, A) - 1) * 100, 1), unit="%"),
      dict(check="国立公園：1990〜94年平均→2023〜24年平均（コロナの戻りの途中の2022年を除く）", value=round((avg(npu, [2023, 2024]) / avg(npu, A) - 1) * 100, 1), unit="%"),
      dict(check="国定公園：いちばん多い年→2024年", value=round(float(t.qnp_users.loc[2024] / t.qnp_users.max() * 100 - 100), 1), unit="%"),
      dict(check="都道府県立自然公園：いちばん多い年→2024年", value=round(float(t.pref_users.loc[2024] / t.pref_users.max() * 100 - 100), 1), unit="%"),
      dict(check="そろえた公園から西表(石垣)を除く 1991→2024年", value=round(float(q.drop("西表(石垣)")[2024].sum() / q.drop("西表(石垣)")[1991].sum() * 100 - 100), 1), unit="%"),
      dict(check="2024年の代わりに2023年：国立公園 2019→2023年", value=round(float(npu.loc[2023] / npu.loc[2019] * 100 - 100), 1), unit="%"),
      dict(check="そろえた公園で2023年が2019年を下回った数", value=int((q[2023] < q[2019]).sum()), unit=f"/{len(q)}")]
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {x.check: x.value for x in rbd.itertuples()}
main["qnp_peak_year"] = int(t.qnp_users.idxmax()); main["pref_peak_year"] = int(t.pref_users.idxmax())
pd.DataFrame({"np_10k": npu, "fixed_10k": fixed.reindex(npu.index), "np_n": t.np_n, "qnp_10k": t.qnp_users / 1e4, "pref_10k": t.pref_users / 1e4}).to_csv(R / "series.csv", float_format="%.1f")
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in main.items() if k != "park_change_2019_2024"}, ensure_ascii=False, indent=1)); print(rbd.to_string()); print(d19.round(1).to_string())
