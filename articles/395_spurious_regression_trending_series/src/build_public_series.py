"""手元の公的統計の年次系列（これまでの記事で作った表）から、10本を1つの表にまとめる。
リポジトリの articles/ の下で動かす想定（各記事のフォルダを読む）。できた表は data/public_annual_series.csv。"""
import pandas as pd
from pathlib import Path
A = Path(__file__).resolve().parents[2]; OUT = Path(__file__).resolve().parents[1] / "data" / "public_annual_series.csv"
s = {}
d = pd.read_csv(A / "340_high_school_enrollment/data/high_school_rate_1948_2025.csv").set_index("year"); s["高校進学率"] = d["ex_t"]
d = pd.read_csv(A / "370_employee_share_80_percent/data/status_1953_latest.csv"); d = d[d.sex == "男女計"].set_index("year"); s["雇用者の割合"] = d["s_employee"]
d = pd.read_csv(A / "369_coal_to_oil_energy_shift/data/primary_energy_shares_fy1953_2023.csv").set_index("fy"); s["天然ガスの割合"] = d["gas"]; s["エネルギー供給量"] = d["total_pj"]
d = pd.read_csv(A / "366_holidays_long_weekends/data/holidays_by_year.csv").set_index("year"); s["休日の数"] = d["total"]
d = pd.read_csv(A / "368_export_leaders_since_1962/data/export_shares_1962_2025.csv").set_index("year"); s["繊維の輸出割合"] = d["textile"]; s["化学製品の輸出割合"] = d["chemical"]
d = pd.read_csv(A / "254_rice_yield_volatility/data/rice_panel.csv"); d = d[(d.level == "region") & (d.name == "全国")].set_index("year"); s["米の10a当たり収量"] = d["yield_kg"]
d = pd.read_csv(A / "264_diurnal_temperature_range/results/a264_rural_anomaly.csv").set_index("year"); s["最高気温の平年差"] = d["tmax_a"]
d = pd.read_csv(A / "265_wet_days_rain_intensity/results/a265_rural_index.csv").set_index("year"); s["雨の日の雨量"] = d["sdii_r"]
df = pd.DataFrame(s).loc[1962:2023]; df.index.name = "year"
assert df.notna().all().all(), df.isna().sum()
df.round(4).to_csv(OUT); print(df.shape, df.iloc[[0, -1]].T)
