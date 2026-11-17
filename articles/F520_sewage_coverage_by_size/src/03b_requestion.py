"""問い直し：小さな町の普及率が上がったのは、つながる人が増えたからか、それとも人口（分母）が減ったからか。
2019→2024年度の変化（pt）を「処理人口の増減の分」（2019年の人口で割る）と「人口が減った分」に分ける。2つの和は変化と一致する。
あわせて、処理人口の増減を処理の方式別に分ける。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(R / "rate_by_municipality.csv", dtype={"code": str})
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
w = d[d.year == 2019].merge(d[d.year == 2024], on="code", suffixes=("_19", "_24"))
rows = []
for s in LABELS:
    g = w[w.size_24 == s]
    P19, P24 = g.pop_19.sum(), g.pop_24.sum()
    S19, S24 = g.served_19.sum(), g.served_24.sum()
    total = 100 * (S24 / P24 - S19 / P19)
    served_eff = 100 * (S24 - S19) / P19
    pop_eff = 100 * S24 * (1 / P24 - 1 / P19)
    assert abs(total - served_eff - pop_eff) < 1e-9
    row = {"size": s, "change_pt": round(total, 2), "served_effect_pt": round(served_eff, 2), "pop_effect_pt": round(pop_eff, 2)}
    for c in ["public_sewer", "rural", "community_plant", "johkaso"]:
        row[f"{c}_effect_pt"] = round(100 * (g[f"{c}_24"].sum() - g[f"{c}_19"].sum()) / P19, 2)
    rows.append(row)
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_decomposition.csv", index=False)
s = t.set_index("size")
small = s.loc["5千人未満"]
out = {"question": "小さな町の普及率の上昇は、人口（分母）の減少によるものか",
       "small": {k: float(v) for k, v in small.items()},
       "small_pop_share_of_change_pct": round(float(100 * small.pop_effect_pt / small.change_pt), 1),
       "answer": "人口が減った分だけで上昇を上回る（処理人口そのものは減っている）" if small.served_effect_pt < 0 else "処理人口の増加も効いている"}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t.to_string()); print(out)
