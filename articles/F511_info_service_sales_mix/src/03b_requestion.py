"""問い直し（結果を見てから足した）：受注ソフトウェアの中身は、SI（システムをまとめて作る仕事）へ移ったのか。
あわせて、2020年にプロダクツの割合が高くなった理由（ゲームソフト）を確かめる。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "annual.csv")
x = d[d.period_type == "年"]
v = x.pivot(index="year", columns="item", values="value")
idx = pd.read_csv(R / "index_2000_100.csv", index_col=0)
sh = pd.read_csv(R / "share_by_year.csv", index_col=0)


def r(z, k=1):
    return round(float(z), k)


si_in_custom = (100 * v.custom_si / v.custom).loc[2000:]
si_in_custom_idx = (si_in_custom[2000] * idx.custom_si / idx.custom)
t = pd.DataFrame({"si_in_custom_pct": si_in_custom.round(4), "si_in_custom_from_index_pct": si_in_custom_idx.round(4),
                  "products_share": sh.products.loc[2000:], "products_ex_game_share": sh.products_ex_game.loc[2000:],
                  "game_share": sh.products_game.loc[2000:]})
t.to_csv(R / "requestion_table.csv")
Y1 = int(v.index.max())
res = {
    "si_in_custom_2000": r(si_in_custom[2000]), "si_in_custom_last": r(si_in_custom[Y1]),
    "si_in_custom_from_index_last": r(si_in_custom_idx[Y1]),
    "custom_ex_si_share_2000": r(sh.custom_ex_si[2000]), "custom_ex_si_share_last": r(sh.custom_ex_si[Y1]),
    "products_peak_year": int(sh.products.loc[2000:].idxmax()), "products_peak_share": r(sh.products.loc[2000:].max()),
    "game_share_at_products_peak": r(sh.products_game[int(sh.products.loc[2000:].idxmax())]),
    "products_ex_game_at_peak": r(sh.products_ex_game[int(sh.products.loc[2000:].idxmax())]),
    "products_ex_game_2000": r(sh.products_ex_game[2000]), "products_ex_game_last": r(sh.products_ex_game[Y1]),
    "products_ex_game_range": [r(sh.products_ex_game.loc[2000:].min()), r(sh.products_ex_game.loc[2000:].max())],
}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
