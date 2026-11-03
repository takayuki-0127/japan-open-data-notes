"""F159 02_整形：確定数・速報・概数（12か月合計）を1つの月次表にまとめる。

出力：data/monthly_panel.csv（year, month, kakutei, sokuhou, gaisu_r12, gaisu_pub, sokuhou_pub）
- 速報は「月の2か月後の月末ごろ」に公表（2007〜2026年の236回すべてで、公表は2か月後の月。
  月末からの日数は48〜61日、中央値53日）。ここでは公表日を「2か月後の月の25日」とみなす。
- 概数（月報）は data/raw/gaisu_rolling12_2011_2026.csv の公表日をそのまま使う。
- 確定数は「翌年9月30日」に公表とみなす（2025年確定数は2026年9月30日公表）。
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

k = pd.read_csv(RAW / "kakutei_monthly_2000_2025.csv")
k = k.melt(id_vars=["year", "total"], var_name="m", value_name="kakutei")
k["month"] = k["m"].str[1:].astype(int)
k = k[["year", "month", "kakutei"]]

s = pd.read_csv(RAW / "sokuhou_monthly_2005_2026.csv").rename(columns={"births_sokuhou": "sokuhou"})
g = pd.read_csv(RAW / "gaisu_rolling12_2011_2026.csv").rename(
    columns={"births_gaisu_12month_sum": "gaisu_r12", "published": "gaisu_pub"})

idx = pd.MultiIndex.from_product([range(2000, 2027), range(1, 13)], names=["year", "month"]).to_frame(index=False)
p = idx.merge(k, how="left").merge(s, how="left").merge(g, how="left")


def sok_pub(r):
    y, m = int(r.year), int(r.month) + 2
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y}-{m:02d}-25"


p["sokuhou_pub"] = [sok_pub(r) if pd.notna(r.sokuhou) else None for r in p.itertuples()]
p["kakutei_pub"] = [f"{int(r.year)+1}-09-30" if pd.notna(r.kakutei) else None for r in p.itertuples()]
p = p[(p.year >= 2000)]
p.to_csv(ROOT / "data" / "monthly_panel.csv", index=False)

# 確認
ann = p.groupby("year")[["kakutei", "sokuhou"]].sum(min_count=12)
ann["ratio"] = ann.kakutei / ann.sokuhou
nen = g[g.month == 12].set_index("year").gaisu_r12
ann["nengai"] = nen
ann["nengai_vs_kakutei_%"] = (ann.kakutei / ann.nengai - 1) * 100
print(ann.loc[2005:].round(4).to_string())
