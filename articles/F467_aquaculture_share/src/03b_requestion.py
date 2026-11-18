"""問い直し（結果を見てから足した）：2004年以降に海面養殖の産出額が増えたのは、量が増えたからか、1kg あたりの額が上がったからか。
品目群ごとに、産出額の対数の変化を、量の対数の変化と1kg あたり産出額の対数の変化に分ける（足すと一致）。"""
import json, pathlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT

RES = ROOT / "results"; D = ROOT / "data"
L = pd.read_csv(D / "volume_long.csv").set_index("year")
M = pd.read_csv(D / "value_long.csv").set_index("year")
END = int(M.index.max())
GRP = {"魚類": ["ma_fish"], "貝類": ["ma_shell"], "海藻類": ["ma_seaweed"], "海面養殖の計（真珠を除く）": ["ma_fish", "ma_shell", "ma_seaweed", "ma_kuruma", "ma_hoya", "ma_otherani"]}
rows = []
for a, b in [(2004, END), (2004, 2014), (2014, END)]:
    for g, cols in GRP.items():
        v0, v1 = M.loc[a, cols].sum(), M.loc[b, cols].sum()
        q0, q1 = L.loc[a, cols].sum(), L.loc[b, cols].sum()
        p0, p1 = v0 / (q0 * 1000), v1 / (q1 * 1000)
        rows.append({"from": a, "to": b, "group": g, "val_ratio": round(v1 / v0, 4), "vol_ratio": round(q1 / q0, 4), "yen_per_kg_from": round(p0, 1),
                     "yen_per_kg_to": round(p1, 1), "price_ratio": round(p1 / p0, 4),
                     "dlog_val": round(np.log(v1 / v0), 4), "dlog_vol": round(np.log(q1 / q0), 4), "dlog_price": round(np.log(p1 / p0), 4)})
df = pd.DataFrame(rows)
df.to_csv(RES / "requestion_value_split.csv", index=False)
out = {"rows": rows}
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); print(df.to_string())
