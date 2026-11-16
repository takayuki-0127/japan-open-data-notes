"""主な分析：パン÷米の比、パンが米を上回った年、米と食パンの支出の変化を量と価格に分ける、仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
g = pd.read_csv(ROOT / "data" / "grain.csv")
hh = pd.read_csv(ROOT / "data" / "household.csv").set_index("year").persons
a = g[g.group == "平均"]
amt = a.pivot(index="year", columns="item", values="amount")
qty = a.pivot(index="year", columns="item", values="qty")
prc = a.pivot(index="year", columns="item", values="price")


def r(x, k=1):
    return round(float(x), k)


t = pd.DataFrame({"rice": amt.rice, "bread": amt.bread, "plain_bread": amt.plain_bread, "other_bread": amt.other_bread,
                  "noodles": amt.noodles, "ratio_bread_rice": (amt.bread / amt.rice).round(4),
                  "rice_qty_kg": qty.rice, "rice_price_per_kg": prc.rice,
                  "plain_qty_g": qty.plain_bread, "plain_price_per_100g": prc.plain_bread,
                  "rice_share_of_food_pct": (100 * amt.rice / amt.food).round(3), "bread_share_of_food_pct": (100 * amt.bread / amt.food).round(3)})
t.to_csv(R / "by_year.csv")
over = [int(y) for y in t.index if t.bread[y] > t.rice[y]]


def decompose(item, y0, y1, kind="log"):
    A0, A1 = amt[item][y0], amt[item][y1]
    q0, q1, p0, p1 = qty[item][y0], qty[item][y1], prc[item][y0], prc[item][y1]
    if kind == "log":
        dA = np.log(A1 / A0); dq = np.log(q1 / q0); dp = np.log(p1 / p0)
        tot = A1 - A0
        # 対数の差の比で金額の差を分ける（量＋価格＝金額の差、残りは端数）
        return {"item": item, "y0": y0, "y1": y1, "amount0": r(A0, 0), "amount1": r(A1, 0), "change": r(tot, 0),
                "qty_part": r(tot * dq / dA, 0), "price_part": r(tot * dp / dA, 0), "price_share_pct": r(100 * dp / dA),
                "qty_change_pct": r(100 * (q1 / q0 - 1)), "price_change_pct": r(100 * (p1 / p0 - 1))}
    # ラスパイレス型：量の効果＝(q1−q0)p0、価格の効果＝(p1−p0)q1
    unit = A0 / (q0 * p0)
    qe = (q1 - q0) * p0 * unit; pe = (p1 - p0) * q1 * unit
    return {"item": item, "y0": y0, "y1": y1, "change": r(A1 - A0, 0), "qty_part": r(qe, 0), "price_part": r(pe, 0),
            "price_share_pct": r(100 * pe / (qe + pe))}


dec = [decompose("rice", 2023, 2025), decompose("rice", 2002, 2023), decompose("plain_bread", 2002, 2023),
       decompose("plain_bread", 2023, 2025), decompose("rice", 2023, 2024), decompose("rice", 2024, 2025)]
pd.DataFrame(dec).to_csv(R / "decomposition.csv", index=False)
d_rice = dec[0]

inc_plain = amt.plain_bread[2023] - amt.plain_bread[2002]
inc_other = amt.other_bread[2023] - amt.other_bread[2002]
hyp = {
    "H1": {"years_bread_over_rice": over, "first_year": min(over) if over else None, "verdict": "支持" if over else "外れ"},
    "H2": {"rice_over_bread_between": [int(y) for y in t.loc[min(over):2023].index if t.rice[y] >= t.bread[y]],
           "rice_over_bread_2025": bool(t.rice[2025] > t.bread[2025]),
           "verdict": "支持" if (all(t.bread[y] > t.rice[y] for y in range(min(over), 2024)) and t.rice[2025] > t.bread[2025]) else "外れ"},
    "H3": {"price_share_pct": d_rice["price_share_pct"], "verdict": "支持" if d_rice["price_share_pct"] >= 80 else "外れ"},
    "H4": {"plain_increase": r(inc_plain, 0), "other_increase": r(inc_other, 0), "verdict": "支持" if inc_other > inc_plain else "外れ"},
}

# 頑健性
rob = []
rob.append({"check": "本線：パン全体と米（年ごと）", "years_over": "・".join(map(str, over)), "first": min(over), "ratio_2023": r(t.ratio_bread_rice[2023], 2), "ratio_2025": r(t.ratio_bread_rice[2025], 2)})
over_p = [int(y) for y in t.index if t.plain_bread[y] > t.rice[y]]
rob.append({"check": "食パンだけと米", "years_over": "・".join(map(str, over_p)) or "なし", "first": min(over_p) if over_p else None,
            "ratio_2023": r(t.plain_bread[2023] / t.rice[2023], 2), "ratio_2025": r(t.plain_bread[2025] / t.rice[2025], 2)})
m3 = t[["bread", "rice"]].rolling(3).mean()
over3 = [int(y) for y in m3.dropna().index if m3.bread[y] > m3.rice[y]]
rob.append({"check": "3年平均（その年までの3年）", "years_over": "・".join(map(str, over3)), "first": min(over3),
            "ratio_2023": r(m3.bread[2023] / m3.rice[2023], 2), "ratio_2025": r(m3.bread[2025] / m3.rice[2025], 2)})
wheat = t.bread + t.noodles
over_w = [int(y) for y in t.index if wheat[y] > t.rice[y]]
rob.append({"check": "パン＋麺類（小麦の主食）と米", "years_over": "・".join(map(str, over_w)), "first": min(over_w),
            "ratio_2023": r(wheat[2023] / t.rice[2023], 2), "ratio_2025": r(wheat[2025] / t.rice[2025], 2)})
over_n = [int(y) for y in t.index if t.noodles[y] > t.rice[y]]
rob.append({"check": "麺類だけと米", "years_over": "・".join(map(str, over_n)) or "なし", "first": min(over_n) if over_n else None,
            "ratio_2023": r(t.noodles[2023] / t.rice[2023], 2), "ratio_2025": r(t.noodles[2025] / t.rice[2025], 2)})
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
las = decompose("rice", 2023, 2025, kind="las")
(R / "decomposition_laspeyres.json").write_text(json.dumps(las, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

main = {
    "amount": {str(y): {"rice": r(t.rice[y], 0), "bread": r(t.bread[y], 0), "plain_bread": r(t.plain_bread[y], 0), "other_bread": r(t.other_bread[y], 0)}
               for y in [2002, 2010, 2011, 2012, 2013, 2014, 2019, 2023, 2024, 2025]},
    "ratio_bread_rice": {str(y): r(t.ratio_bread_rice[y], 3) for y in [2002, 2011, 2023, 2024, 2025]},
    "ratio_max": {"year": int(t.ratio_bread_rice.idxmax()), "value": r(t.ratio_bread_rice.max(), 3)},
    "rice_min": {"year": int(t.rice.idxmin()), "value": r(t.rice.min(), 0)},
    "rice_qty": {str(y): r(t.rice_qty_kg[y], 2) for y in [2002, 2023, 2024, 2025]},
    "rice_price": {str(y): r(t.rice_price_per_kg[y], 2) for y in [2002, 2023, 2024, 2025]},
    "plain_qty": {str(y): r(t.plain_qty_g[y], 0) for y in [2002, 2023, 2025]},
    "plain_price": {str(y): r(t.plain_price_per_100g[y], 2) for y in [2002, 2023, 2025]},
    "food_share": {str(y): {"rice": r(t.rice_share_of_food_pct[y], 2), "bread": r(t.bread_share_of_food_pct[y], 2)} for y in [2002, 2023, 2025]},
    "decomposition": dec,
    "decomposition_laspeyres_2023_2025": las,
    "hypotheses": hyp,
    "note": "二人以上の世帯の1世帯当たり年間の支出金額（円）。米の数量はkg、価格は円/kg。食パンの数量はg、価格は円/100g。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
