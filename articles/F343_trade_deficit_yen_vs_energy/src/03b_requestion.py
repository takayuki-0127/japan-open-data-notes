"""問い直し（結果を見てから足した）。
Q：燃料以外の輸入にも円安の分が大きく出た。では輸出の円安の分を差し引くと、円安は貿易収支をどれだけ動かしたのか。
   輸出・輸入それぞれを「円ベース÷契約通貨ベース」の物価指数の比（為替の換算の分）と、それ以外に分ける（LMDI）。
   契約通貨での値段が為替に反応しない、という強い仮定の上の近似。
結果は results/requestion.json と results/requestion_fx_net.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
tot = pd.read_csv(D / "trade_totals.csv").set_index("year")
fx = pd.read_csv(D / "boj_annual.csv").set_index("year")
CHO = 1e9


def L(a, b):
    return (b - a) / np.log(b / a)


def fxpart(y0, y1):
    X0, X1 = tot.loc[y0, "exports_kyen"], tot.loc[y1, "exports_kyen"]
    M0, M1 = tot.loc[y0, "imports_kyen"], tot.loc[y1, "imports_kyen"]
    ex0 = fx.loc[y0, "PRCG20_2400000000"] / fx.loc[y0, "PRCG20_2300000000"]; ex1 = fx.loc[y1, "PRCG20_2400000000"] / fx.loc[y1, "PRCG20_2300000000"]
    im0 = fx.loc[y0, "PRCG20_2600000000"] / fx.loc[y0, "PRCG20_2500000000"]; im1 = fx.loc[y1, "PRCG20_2600000000"] / fx.loc[y1, "PRCG20_2500000000"]
    xfx = L(X0, X1) * np.log(ex1 / ex0) / CHO
    mfx = L(M0, M1) * np.log(im1 / im0) / CHO
    return {"y0": y0, "y1": y1, "d_exports_tyen": round((X1 - X0) / CHO, 2), "d_imports_tyen": round((M1 - M0) / CHO, 2),
            "exports_fx_part_tyen": round(xfx, 2), "imports_fx_part_tyen": round(mfx, 2), "net_fx_on_balance_tyen": round(xfx - mfx, 2),
            "d_balance_tyen": round(((X1 - M1) - (X0 - M0)) / CHO, 2), "d_balance_ex_fx_tyen": round(((X1 - M1) - (X0 - M0)) / CHO - (xfx - mfx), 2),
            "export_fx_ratio_change_pct": round(100 * (ex1 / ex0 - 1), 1), "import_fx_ratio_change_pct": round(100 * (im1 / im0 - 1), 1)}


rows = [fxpart(a, b) for a, b in [(2020, 2022), (2020, 2025), (2019, 2022), (2021, 2022), (2022, 2025)]]
df = pd.DataFrame(rows)
df.to_csv(R / "requestion_fx_net.csv", index=False)
out = {f"{r['y0']}_{r['y1']}": r for r in rows}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(df.to_string())
