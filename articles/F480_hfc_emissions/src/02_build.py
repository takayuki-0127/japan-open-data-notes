"""data/raw の Excel（2026年版・2025年版）から、ガス別・用途別の長い表 data/fgas_long.csv を作る。ネットにはつながない。
単位はすべて百万トンCO2換算（Mt）。'NO'（発生しない）は0とする。"""
import pathlib
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FILES = {"2026": "L5-7gas_2026_gioweb_ver1.0.xlsx", "2025": "L5-7gas_2025_gioweb_1.0.xlsx"}

# 8.F-gas の5〜39行（排出量の表）。行番号 → (ガス, 用途のキー, 日本語名)
FROWS = {
    5: ("HFC", "total", "HFC 計"), 6: ("HFC", "refrig_total", "冷蔵庫及び空調機器"),
    7: ("HFC", "refrig_commercial", "業務用冷凍空調機器"), 8: ("HFC", "refrig_household_ac", "家庭用エアコン"),
    9: ("HFC", "refrig_car_ac", "カーエアコン"), 10: ("HFC", "refrig_other", "冷凍空調のその他"),
    11: ("HFC", "foam", "発泡剤"), 12: ("HFC", "aerosol", "エアゾール・MDI"), 13: ("HFC", "solvent", "洗浄剤・溶剤"),
    14: ("HFC", "fugitive_mfg", "HFC 製造時の漏出"), 15: ("HFC", "semiconductor", "半導体"), 16: ("HFC", "lcd", "液晶"),
    17: ("HFC", "byproduct_hfc23", "HCFC22 製造時の副生 HFC23"), 18: ("HFC", "fire", "消火剤"),
    19: ("HFC", "magnesium", "マグネシウム製造"), 20: ("HFC", "other", "その他"),
    21: ("PFC", "total", "PFC 計"), 28: ("SF6", "total", "SF6 計"), 35: ("NF3", "total", "NF3 計"),
    39: ("FGAS", "total", "代替フロン等4ガス 計"),
}
# 1.Summary（百万トン）
SROWS = {5: ("CO2", "total", "CO2 計"), 8: ("CH4", "total", "CH4 計"), 9: ("N2O", "total", "N2O 計"), 15: ("GHG", "total", "温室効果ガス 計")}


def num(x):
    if x is None or isinstance(x, str):
        return 0.0
    return float(x)


rows = []
for ver, fn in FILES.items():
    wb = openpyxl.load_workbook(RAW / fn, read_only=True, data_only=True)
    for sheet, spec, scale in [("8.F-gas", FROWS, 1 / 1000), ("1.Summary", SROWS, 1.0)]:
        grid = [list(r) for r in wb[sheet].iter_rows(min_row=1, max_row=45, values_only=True)]
        years = {j: int(v) for j, v in enumerate(grid[3]) if isinstance(v, (int, float)) and 1989 < v < 2100}
        for rn, (gas, key, name) in spec.items():
            r = grid[rn - 1]
            for j, y in years.items():
                rows.append({"version": ver, "gas": gas, "use": key, "name": name, "fy": y, "mt": round(num(r[j]) * scale, 6)})
df = pd.DataFrame(rows).sort_values(["version", "gas", "use", "fy"]).reset_index(drop=True)
# 点検：HFC の用途の合計が HFC 計に一致すること
for ver in FILES:
    d = df[(df.version == ver) & (df.gas == "HFC")]
    parts = d[~d.use.isin(["total", "refrig_total"])].groupby("fy").mt.sum()
    assert (parts - d[d.use == "total"].set_index("fy").mt).abs().max() < 0.01, ver
df.to_csv(ROOT / "data" / "fgas_long.csv", index=False)
print(df.groupby("version").fy.agg(["min", "max"]), len(df))
