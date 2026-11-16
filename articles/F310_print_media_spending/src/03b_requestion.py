"""問い直し（結果を見てから足した）：
書籍は、どの年齢でも減り方が小さい（−12〜−26、70歳以上を除く）のに、平均では −34 だった。
平均の減りのうち、世帯主の年齢の構成が変わった分（年齢の高い世帯が増えた分）はどれだけか。
世帯数分布（抽出率調整）を重みにして、年齢の重みを2002〜04年に固定した平均と比べる（名目）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "print_by_age.csv")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
r3 = lambda x: round(float(x), 3)
W = d[d.item == "hh_weight"].pivot(index="year", columns="age", values="amount")[AG]
W = W.div(W.sum(axis=1), axis=0)
S, E = [2002, 2003, 2004], [2023, 2024, 2025]
out = {"weights_start": {a: r3(100 * W.loc[S, a].mean()) for a in AG}, "weights_end": {a: r3(100 * W.loc[E, a].mean()) for a in AG}}
rows = []
for k in ["print_total", "newspaper", "magazine", "books"]:
    X = d[d.item == k].pivot(index="year", columns="age", values="amount")
    w0, w1 = W.loc[S].mean(), W.loc[E].mean()
    x0, x1 = X.loc[S, AG].mean(), X.loc[E, AG].mean()
    pub0, pub1 = X.loc[S, "平均"].mean(), X.loc[E, "平均"].mean()
    agg0, agg1 = float((w0 * x0).sum()), float((w1 * x1).sum())
    fixed1 = float((w0 * x1).sum())
    rows.append(dict(item=k, published_change=r3(100 * np.log(pub1 / pub0)), rebuilt_change=r3(100 * np.log(agg1 / agg0)),
                     fixed_weight_change=r3(100 * np.log(fixed1 / agg0)), composition_part=r3(100 * np.log(agg1 / fixed1))))
t = pd.DataFrame(rows); t.to_csv(RES / "requestion_composition.csv", index=False)
out["items"] = {r.item: dict(published=r.published_change, rebuilt=r.rebuilt_change, fixed_weight=r.fixed_weight_change, composition=r.composition_part) for r in t.itertuples()}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
