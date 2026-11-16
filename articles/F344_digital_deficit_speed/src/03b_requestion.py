"""問い直し（結果を見てから足した）。
Q：円で見た赤字は2025年に初めて前年を下回り（6.68→6.60兆円）、2026年1〜9月も前年同期を1.1%下回った。
   伸びは止まったのか。ドルで見るとどうか。どの項目が動いたのか。
   12か月の移動合計（円・ドル）と、2024→2025年の項目ごとの変化を見る。
結果は results/requestion.json と results/requestion_rolling12.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
m = pd.read_csv(D / "bop_monthly.csv")
fx = pd.read_csv(D / "usdjpy_monthly.csv")[["period", "value"]].rename(columns={"value": "usdjpy"})
ITEMS = {"9072": "コンピュータ", "9062": "著作権等使用料", "9082": "専門・経営コンサル"}
w = m[m.code.isin([f"BPBP6JYNSN{i}" for i in ITEMS])].pivot(index="period", columns="code", values="value")
w = w.dropna().sort_index()
w.columns = [ITEMS[c.replace("BPBP6JYNSN", "")] for c in w.columns]
w["deficit_oku"] = -w.sum(axis=1)
w = w.join(fx.set_index("period"))
w["deficit_musd"] = w["deficit_oku"] * 1e8 / w["usdjpy"] / 1e6   # 百万ドル
roll = pd.DataFrame({"deficit_tyen_12m": w["deficit_oku"].rolling(12).sum() / 1e4,
                     "deficit_busd_12m": w["deficit_musd"].rolling(12).sum() / 1e3}).dropna()
roll["yoy_yen_pct"] = 100 * (roll["deficit_tyen_12m"] / roll["deficit_tyen_12m"].shift(12) - 1)
roll["yoy_usd_pct"] = 100 * (roll["deficit_busd_12m"] / roll["deficit_busd_12m"].shift(12) - 1)
roll.round(4).to_csv(R / "requestion_rolling12.csv")
last = int(roll.index.max())
peak_yen = int(roll["deficit_tyen_12m"].idxmax()); peak_usd = int(roll["deficit_busd_12m"].idxmax())
# 2024→2025 の項目ごと
ann = w.assign(year=w.index // 100).groupby("year")[list(ITEMS.values())].sum() / 1e4
ch = (-(ann.loc[2025] - ann.loc[2024])).round(3).to_dict()
usd_ann = w.assign(year=w.index // 100).groupby("year")["deficit_musd"].sum() / 1e3
out = {"last_period": last, "deficit_tyen_12m_last": round(float(roll.loc[last, "deficit_tyen_12m"]), 2),
       "deficit_busd_12m_last": round(float(roll.loc[last, "deficit_busd_12m"]), 1),
       "yoy_yen_last_pct": round(float(roll.loc[last, "yoy_yen_pct"]), 1), "yoy_usd_last_pct": round(float(roll.loc[last, "yoy_usd_pct"]), 1),
       "peak_yen_period": peak_yen, "peak_yen_tyen": round(float(roll.loc[peak_yen, "deficit_tyen_12m"]), 2),
       "peak_usd_period": peak_usd, "peak_usd_busd": round(float(roll.loc[peak_usd, "deficit_busd_12m"]), 1),
       "deficit_increase_2024_2025_by_item_tyen": ch,
       "deficit_busd_annual": {str(int(y)): round(float(v), 1) for y, v in usd_ann.loc[2014:2025].items()}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
