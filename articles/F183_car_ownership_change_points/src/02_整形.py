# data/raw の JSON（AIRIA の県別表、全国の長期表、全国軽自動車協会連合会の軽四輪の表）を整形して CSV にする
import json, pandas as pd
nat = json.load(open("data/raw/national.json"))
pd.DataFrame([{"year": int(y), "rate": v[0], "cars": v[1], "hh": v[2]} for y, v in nat.items()]).to_csv("data/national.csv", index=False)
pr = json.load(open("data/raw/pref_raw.json"))
rows = [{"year": int(y), "pref": p, "cars": v[0], "hh": v[1], "rate": v[2]} for y, d in pr.items() for p, v in d.items()]
pd.DataFrame(rows).sort_values(["pref", "year"]).to_csv("data/pref_panel.csv", index=False)
kei = json.load(open("data/raw/kei.json"))
rows = []
for k, d in kei.items():
    y, m = map(int, k.split("-"))
    for p, v in d.items():
        rows.append({"key": k, "year": y, "month": m, "pref": p, "kei": v[0], "hh": v[1]})
pd.DataFrame(rows).sort_values(["pref", "year", "month"]).to_csv("data/kei_panel.csv", index=False)
n = pd.read_csv("data/national.csv").set_index("year"); p = pd.DataFrame(pd.read_csv("data/pref_panel.csv"))
chk = p.groupby("year").agg(cars=("cars", "sum"), hh=("hh", "sum"), n=("pref", "size"))
chk["nat_cars_table"] = n.cars; chk["ratio_cars"] = chk.cars / chk.nat_cars_table
chk.to_csv("results/check_sum_vs_national.csv"); print(chk.round(4))
