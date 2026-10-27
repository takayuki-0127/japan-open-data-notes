"""品目×都市の表を作る。全国の値との比（全国=1）にそろえる。"""
import json
import numpy as np
import pandas as pd
from common import RAW, DATA, AGG, EXCLUDE, CITIES

# 2013〜2015年と名前が違う品目（同じ品目として扱う）
RENAME_OLD = {"スパゲッティ": "パスタ", "魚介加工品のその他": "他の魚介加工品のその他",
              "他の野菜・海藻の佃煮": "他の野菜・海藻のつくだ煮"}

d = pd.read_csv(RAW / "f47_kakei_rank.csv", encoding="utf-8-sig")
d = d[d.sheet != "食料以外"]
d.loc[d.period == "2013-2015", "item"] = d.loc[d.period == "2013-2015", "item"].replace(RENAME_OLD)
d = d[~d.item.isin(AGG | EXCLUDE)]
info = {}
for p, g in d.groupby("period"):
    w = g.pivot_table(index="item", columns="city", values="yen", aggfunc="first")
    # 品目の並びは元の表の順
    order = list(dict.fromkeys(g["item"]))
    grp = g.drop_duplicates("item").set_index("item")["sheet"]
    w = w.loc[order]
    nat = w["全国"]
    assert set(CITIES) <= set(w.columns), set(CITIES) - set(w.columns)
    ratio = w[CITIES].div(nat, axis=0)
    out = ratio.copy()
    out.insert(0, "全国_円", nat)
    out.insert(0, "分類", grp.loc[order])
    tag = p.replace("-", "_")
    out.to_csv(DATA / f"ratio_{tag}.csv", encoding="utf-8-sig")
    info[p] = dict(items=int(len(w)), items_other=int(sum(i.startswith("他の") for i in order)),
                   cities=len(CITIES), min_ratio=float(ratio.min().min()), max_ratio=float(ratio.max().max()))
json.dump(info, open(DATA / "shape.json", "w"), ensure_ascii=False, indent=1)
print(info)
