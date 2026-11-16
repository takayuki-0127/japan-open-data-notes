"""灯油の長期推移、2008→2025年の分解、都市別、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
L = pd.read_csv(ROOT / "data" / "kerosene_long_1963_2007.csv").set_index("year")
N = pd.read_csv(ROOT / "data" / "kerosene_national.csv").set_index("year")
C = pd.read_csv(ROOT / "data" / "kerosene_cities.csv")
link = float(N.loc[2007, "qty"] / L.loc[2007, "qty"])
ser = pd.concat([L.qty.loc[:2006] * link, N.qty.loc[2007:]]).rename("qty_linked").dropna()
ser_raw = pd.concat([L.qty.loc[:2006], N.qty.loc[2007:]]).rename("qty_unlinked")
sp = pd.concat([L.spend.loc[:2006] * float(N.loc[2007, "spend"] / L.loc[2007, "spend"]), N.spend.loc[2007:]]).rename("spend_linked")
out = pd.concat([ser, ser_raw, sp], axis=1); out.index.name = "year"
out.to_csv(R / "kerosene_long_linked.csv", float_format="%.3f")
N["share_buyers"] = N.buyers / 10000 * 100
N["qty_per_buyer"] = N.qty / (N.buyers / 10000)
N.to_csv(R / "kerosene_national_2007_2025.csv", float_format="%.4f")
peak = int(ser.idxmax())
m = lambda s, ys: float(s.loc[ys].mean())
main = {"link_ratio_2007": round(link, 4), "peak_year": peak, "peak_qty": round(float(ser.max()), 1),
        "first_qty_year": int(ser.dropna().index.min()), "qty_first": round(float(ser.dropna().iloc[0]), 1), "qty_2000": round(float(ser.loc[2000]), 1), "qty_2008": round(float(N.loc[2008, "qty"]), 1),
        "qty_2025": round(float(N.loc[2025, "qty"]), 1), "qty_pct_peak_2025": round(float(N.loc[2025, "qty"] / ser.max() * 100 - 100), 1),
        "qty_pct_2008_2025": round(float((N.loc[2025, "qty"] / N.loc[2008, "qty"] - 1) * 100), 1),
        "spend_pct_2008_2025": round(float((N.loc[2025, "spend"] / N.loc[2008, "spend"] - 1) * 100), 1),
        "spend_2008": float(N.loc[2008, "spend"]), "spend_2025": float(N.loc[2025, "spend"]),
        "price_2008": float(N.loc[2008, "price"]), "price_2025": float(N.loc[2025, "price"]), "price_2016": float(N.loc[2016, "price"]),
        "buyers_share_2008": round(float(N.loc[2008, "share_buyers"]), 1), "buyers_share_2025": round(float(N.loc[2025, "share_buyers"]), 1),
        "per_buyer_2008": round(float(N.loc[2008, "qty_per_buyer"]), 1), "per_buyer_2025": round(float(N.loc[2025, "qty_per_buyer"]), 1)}
dl = np.log(N.loc[2025, "qty"]) - np.log(N.loc[2008, "qty"])
db = np.log(N.loc[2025, "buyers"]) - np.log(N.loc[2008, "buyers"]); dq = np.log(N.loc[2025, "qty_per_buyer"]) - np.log(N.loc[2008, "qty_per_buyer"])
main["decomp_share_buyers_pct"] = round(float(db / dl * 100), 1); main["decomp_per_buyer_pct"] = round(float(dq / dl * 100), 1)
P = C.pivot(index="region", columns="year", values="qty")
order = list(C[C.year == 2025].region)  # 表の並び（北から南）
P = P.loc[order]
main["n_cities"] = len(P); main["n_down_2018_2025"] = int((P[2025] < P[2018]).sum())
main["n_down_2019_2024"] = int((P[2024] < P[2019]).sum())
NORTH = order[:7]  # 札幌・青森・盛岡・仙台・秋田・山形・福島
main["north_cities"] = NORTH
main["north_pct"] = round(float((P.loc[NORTH, 2025].sum() / P.loc[NORTH, 2018].sum() - 1) * 100), 1)
rest = [c for c in order if c not in NORTH]
main["rest_pct"] = round(float((P.loc[rest, 2025].sum() / P.loc[rest, 2018].sum() - 1) * 100), 1)
main["north_down"] = int((P.loc[NORTH, 2025] < P.loc[NORTH, 2018]).sum()); main["rest_down"] = int((P.loc[rest, 2025] < P.loc[rest, 2018]).sum())
cityt = pd.DataFrame({"qty_2018": P[2018], "qty_2025": P[2025], "pct": (P[2025] / P[2018] - 1) * 100})
cityt.to_csv(R / "cities_2018_2025.csv", float_format="%.3f")
main["hypotheses"] = {"H1": "支持" if peak < 2000 else "外れ", "H2": "支持" if main["spend_pct_2008_2025"] > main["qty_pct_2008_2025"] else "外れ",
                      "H3": "支持" if main["n_down_2018_2025"] >= 40 else "外れ", "H4": "支持" if main["decomp_share_buyers_pct"] >= 50 else "外れ"}
rb = []
a, b = [2008, 2009, 2010], [2023, 2024, 2025]
rb.append(dict(check="2008〜10年平均→2023〜25年平均：購入数量", value=round((m(N.qty, b) / m(N.qty, a) - 1) * 100, 1), unit="%"))
rb.append(dict(check="同：支出金額", value=round((m(N.spend, b) / m(N.spend, a) - 1) * 100, 1), unit="%"))
dl2 = np.log(m(N.qty, b)) - np.log(m(N.qty, a)); db2 = np.log(m(N.buyers, b)) - np.log(m(N.buyers, a))
rb.append(dict(check="同：買う世帯の割合の減りの分の割合", value=round(float(db2 / dl2 * 100), 1), unit="%"))
rb.append(dict(check="2019→2024年に購入数量が減った市", value=main["n_down_2019_2024"], unit=f"/{len(P)}"))
rb.append(dict(check="北海道・東北7市の合計 2018→2025年", value=main["north_pct"], unit="%"))
rb.append(dict(check="それ以外45市の合計 2018→2025年", value=main["rest_pct"], unit="%"))
rb.append(dict(check="つなぎ目を補正しないときのいちばん多い年", value=int(ser_raw.idxmax()), unit="年"))
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: r.value for r in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rbd.to_string())
