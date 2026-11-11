"""F234 整形：分析に使うパネル（前年差・区分の変更の判定・重み・操作変数）を data/ に書き出す"""
from common import *
d = load_panel()
boj = load_boj_annual()
x = d.merge(boj[["year", "dl_imp_food", "dl_imp_energy", "dl_usdjpy"]], on="year", how="left")
x["E_food_narrow"] = x.name.isin(IMPORT_FOOD_NARROW).astype(int)
x["E_food_broad"] = x.name.isin(IMPORT_FOOD_BROAD).astype(int)
x["E_energy"] = x.name.isin(ENERGY).astype(int)
x.to_csv(DATA / "panel_diff.csv", index=False)
boj.to_csv(DATA / "boj_annual.csv", index=False)
print(x.shape, int(d["break"].sum()))
