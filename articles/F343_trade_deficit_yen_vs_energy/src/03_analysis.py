"""貿易収支の変化の分解と、燃料3品目の輸入額の LMDI 分解（数量・ドル建て単価・ドル円）。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
tot = pd.read_csv(D / "trade_totals.csv").set_index("year")
cm = pd.read_csv(D / "trade_by_commodity.csv", dtype={"code": str})
fx = pd.read_csv(D / "boj_annual.csv").set_index("year")
FUELS = {"30301": "原油", "3050103": "LNG", "30101": "石炭"}
CHO = 1e9  # 千円 → 兆円 は 1e9 で割る


def imp(code, y, col="value_kyen"):
    q = cm[(cm.flow == "輸入") & (cm.code == code) & (cm.year == y)]
    return float(q[col].iloc[0])


def r(x, k=2):
    return round(float(x), k)


def L(a, b):
    return (b - a) / np.log(b / a) if a != b else a


def lmdi_fuels(y0, y1, fxsrc="usd"):
    rows = []
    for code, name in FUELS.items():
        V0, V1 = imp(code, y0), imp(code, y1)
        Q0, Q1 = imp(code, y0, "qty"), imp(code, y1, "qty")
        if fxsrc == "usd":
            F0, F1 = fx.loc[y0, "FXERM07"], fx.loc[y1, "FXERM07"]
        else:  # 輸入物価指数 円ベース ÷ 契約通貨ベース
            F0 = fx.loc[y0, "PRCG20_2600000000"] / fx.loc[y0, "PRCG20_2500000000"]
            F1 = fx.loc[y1, "PRCG20_2600000000"] / fx.loc[y1, "PRCG20_2500000000"]
        P0, P1 = V0 / (Q0 * F0), V1 / (Q1 * F1)
        w = L(V0, V1)
        rows.append({"item": name, "V0_tyen": V0 / CHO, "V1_tyen": V1 / CHO, "dV_tyen": (V1 - V0) / CHO,
                     "qty_tyen": w * np.log(Q1 / Q0) / CHO, "price_tyen": w * np.log(P1 / P0) / CHO, "fx_tyen": w * np.log(F1 / F0) / CHO,
                     "qty_change_pct": 100 * (Q1 / Q0 - 1), "usd_price_change_pct": 100 * (P1 / P0 - 1), "fx_change_pct": 100 * (F1 / F0 - 1)})
    return pd.DataFrame(rows)


def sequential(y0, y1, order):
    """逐次の分解：order の順に要因を入れ替える（3品目の合計）。"""
    res = {"qty": 0.0, "price": 0.0, "fx": 0.0}
    for code in FUELS:
        V0, V1 = imp(code, y0), imp(code, y1)
        Q0, Q1 = imp(code, y0, "qty"), imp(code, y1, "qty")
        F0, F1 = fx.loc[y0, "FXERM07"], fx.loc[y1, "FXERM07"]
        P0, P1 = V0 / (Q0 * F0), V1 / (Q1 * F1)
        cur = {"qty": Q0, "price": P0, "fx": F0}
        new = {"qty": Q1, "price": P1, "fx": F1}
        val = Q0 * P0 * F0
        for k in order:
            cur[k] = new[k]
            v2 = cur["qty"] * cur["price"] * cur["fx"]
            res[k] += (v2 - val) / CHO
            val = v2
    return {k: r(v) for k, v in res.items()}


def balance(y0, y1):
    X0, X1 = tot.loc[y0, "exports_kyen"], tot.loc[y1, "exports_kyen"]
    M0, M1 = tot.loc[y0, "imports_kyen"], tot.loc[y1, "imports_kyen"]
    Mf0, Mf1 = imp("3", y0), imp("3", y1)
    f3_0 = sum(imp(c, y0) for c in FUELS); f3_1 = sum(imp(c, y1) for c in FUELS)
    out = {"y0": y0, "y1": y1, "balance0_tyen": r((X0 - M0) / CHO), "balance1_tyen": r((X1 - M1) / CHO),
           "d_balance_tyen": r(((X1 - M1) - (X0 - M0)) / CHO), "d_exports_tyen": r((X1 - X0) / CHO),
           "d_imports_tyen": r((M1 - M0) / CHO), "d_fuel_imports_tyen": r((Mf1 - Mf0) / CHO),
           "d_fuel3_imports_tyen": r((f3_1 - f3_0) / CHO), "d_other_fuel_imports_tyen": r(((Mf1 - f3_1) - (Mf0 - f3_0)) / CHO),
           "d_nonfuel_imports_tyen": r(((M1 - Mf1) - (M0 - Mf0)) / CHO),
           "fuel_share_of_import_increase_pct": r(100 * (Mf1 - Mf0) / (M1 - M0), 1) if M1 != M0 else None,
           "fuel_imports0_tyen": r(Mf0 / CHO), "fuel_imports1_tyen": r(Mf1 / CHO), "fuel_ratio": r(Mf1 / Mf0, 3)}
    # 燃料以外の輸入の為替の分（輸入物価指数の円ベース÷契約通貨ベースで近似、LMDI）
    N0, N1 = M0 - Mf0, M1 - Mf1
    F0 = fx.loc[y0, "PRCG20_2600000000"] / fx.loc[y0, "PRCG20_2500000000"]
    F1 = fx.loc[y1, "PRCG20_2600000000"] / fx.loc[y1, "PRCG20_2500000000"]
    out["nonfuel_fx_part_tyen"] = r(L(N0, N1) * np.log(F1 / F0) / CHO)
    return out


main = {}
cases = {"2020_2022": (2020, 2022), "2020_2025": (2020, 2025), "2019_2022": (2019, 2022), "2022_2025": (2022, 2025), "2021_2022": (2021, 2022)}
lm_all = []
for k, (a, b) in cases.items():
    df = lmdi_fuels(a, b)
    df.insert(0, "case", k)
    lm_all.append(df)
    s = df[["dV_tyen", "qty_tyen", "price_tyen", "fx_tyen"]].sum()
    main[f"fuel3_{k}"] = {"dV_tyen": r(s.dV_tyen), "qty_tyen": r(s.qty_tyen), "usd_price_tyen": r(s.price_tyen), "fx_tyen": r(s.fx_tyen),
                          "check_sum": r(s.qty_tyen + s.price_tyen + s.fx_tyen - s.dV_tyen, 6),
                          "share_price_pct": r(100 * s.price_tyen / s.dV_tyen, 1), "share_fx_pct": r(100 * s.fx_tyen / s.dV_tyen, 1),
                          "share_qty_pct": r(100 * s.qty_tyen / s.dV_tyen, 1)}
    main[f"balance_{k}"] = balance(a, b)
lm = pd.concat(lm_all, ignore_index=True)
lm.round(4).to_csv(R / "lmdi_fuels.csv", index=False)
main["by_item_2020_2022"] = {r_.item: {"qty_change_pct": r(r_.qty_change_pct, 1), "usd_price_change_pct": r(r_.usd_price_change_pct, 1),
                                       "dV_tyen": r(r_.dV_tyen), "price_tyen": r(r_.price_tyen), "fx_tyen": r(r_.fx_tyen), "qty_tyen": r(r_.qty_tyen)}
                             for r_ in lm[lm.case == "2020_2022"].itertuples()}
main["by_item_2020_2025"] = {r_.item: {"qty_change_pct": r(r_.qty_change_pct, 1), "usd_price_change_pct": r(r_.usd_price_change_pct, 1), "dV_tyen": r(r_.dV_tyen)}
                             for r_ in lm[lm.case == "2020_2025"].itertuples()}
main["usdjpy"] = {str(y): r(fx.loc[y, "FXERM07"], 1) for y in [2019, 2020, 2021, 2022, 2023, 2024, 2025]}
qsum = lambda y: sum(imp(c, y, "qty") for c in ["30301"])
main["fuel3_qty_change_2020_2022_pct"] = {name: r(100 * (imp(c, 2022, "qty") / imp(c, 2020, "qty") - 1), 1) for c, name in FUELS.items()}
# 頑健性
main["robust"] = {
    "sequential_qty_price_fx": sequential(2020, 2022, ["qty", "price", "fx"]),
    "sequential_fx_price_qty": sequential(2020, 2022, ["fx", "price", "qty"]),
    "sequential_price_fx_qty": sequential(2020, 2022, ["price", "fx", "qty"]),
    "fx_from_import_price_index": {k: r(v) for k, v in lmdi_fuels(2020, 2022, fxsrc="ipi")[["dV_tyen", "qty_tyen", "price_tyen", "fx_tyen"]].sum().items()},
}
# 年ごとの系列（図用）
ser = []
for y in range(2000, 2026):
    ser.append({"year": y, "exports_tyen": tot.loc[y, "exports_kyen"] / CHO, "imports_tyen": tot.loc[y, "imports_kyen"] / CHO,
                "balance_tyen": (tot.loc[y, "exports_kyen"] - tot.loc[y, "imports_kyen"]) / CHO, "fuel_imports_tyen": imp("3", y) / CHO,
                "usdjpy": fx.loc[y, "FXERM07"]})
ser = pd.DataFrame(ser)
ser["balance_ex_fuel_tyen"] = ser["balance_tyen"] + ser["fuel_imports_tyen"]
ser.round(4).to_csv(R / "annual_series.csv", index=False)
main["worst_balance"] = {"year": int(ser.loc[ser.balance_tyen.idxmin(), "year"]), "tyen": r(ser.balance_tyen.min())}

f = main["fuel3_2020_2022"]; b = main["balance_2020_2022"]
main["hypotheses"] = {
    "H1": {"usd_price_tyen": f["usd_price_tyen"], "fx_tyen": f["fx_tyen"], "verdict": "支持" if f["usd_price_tyen"] > f["fx_tyen"] else "外れ"},
    "H2": {"qty_change_pct": main["fuel3_qty_change_2020_2022_pct"], "verdict": "支持" if all(abs(v) <= 5 for v in main["fuel3_qty_change_2020_2022_pct"].values()) else "外れ"},
    "H3": {"fuel_share_of_import_increase_pct": b["fuel_share_of_import_increase_pct"], "verdict": "支持" if b["fuel_share_of_import_increase_pct"] >= 50 else "外れ"},
    "H4": {"fuel_ratio_2025_vs_2020": main["balance_2020_2025"]["fuel_ratio"], "verdict": "支持" if main["balance_2020_2025"]["fuel_ratio"] >= 1.5 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as fo:
    json.dump(main, fo, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0)[:7000])
