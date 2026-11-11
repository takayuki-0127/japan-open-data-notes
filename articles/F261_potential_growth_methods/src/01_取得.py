"""F261 データの取得の記録と確認。

公表元のサイトはこの環境の Python から直接は取れないため、ブラウザ（Claude in Chrome）でページ内の
fetch と SheetJS（xlsx 0.18.5）で読み、必要な列だけを CSV にして data/raw/ に置いた。
このスクリプトは、置いたファイルがそろっていて、形が想定どおりかを確かめるだけ。

取得元（2026-11-11 取得）
- 内閣府「GDPギャップ、潜在成長率」 https://www5.cao.go.jp/keizai3/getsurei/2622gap.xlsx
  （月例経済報告 関係資料、2026年4-6月期2次速報ベース。シート「四半期」）
  -> data/raw/cao_gap_2026Q2_2nd.csv（値は公表どおり小数1桁）
- 日本銀行「需給ギャップと潜在成長率」 https://www.boj.or.jp/research/research_data/gap/gap.xlsx
  （2026年10月5日公表。シート data1・data2）
  -> data/raw/boj_gap_2026Oct.csv（小数3桁に丸め）
  -> data/raw/boj_potential_growth_2026Oct.csv（年度半期。H1=4-9月、H2=10-3月。小数3桁に丸め）
- 内閣府「四半期別GDP速報」2026年4-6月期2次速報 実質季節調整系列
  https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jk2622.csv
  -> data/raw/real_gdp_sa_2026Q2_2nd.csv（国内総生産（支出側）の列、10億円、2020暦年連鎖価格）
- F50（articles/F50_gdp_revisions）で集めた、GDP速報の公表回ごとの実質季節調整系列の前期比
  -> data/raw/f50_vintages_real_sa_qoq.csv、data/raw/f50_releases.csv（F50 のファイルをそのまま写した）
"""
import hashlib
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

EXPECT = {
    "cao_gap_2026Q2_2nd.csv": (130, ["quarter", "gap", "pot_growth", "c_tfp", "c_capital", "c_hours", "c_employed"]),
    "boj_gap_2026Oct.csv": (174, ["quarter", "output_gap", "capital_gap", "labor_gap"]),
    "boj_potential_growth_2026Oct.csv": (87, ["fy_half", "pot_growth", "c_tfp", "c_capital", "c_hours", "c_employed"]),
    "real_gdp_sa_2026Q2_2nd.csv": (130, ["quarter", "real_gdp_bn_yen_2020chain"]),
    "f50_releases.csv": (195, ["rid", "ref", "stage", "reissue", "order"]),
}

for name, (n, cols) in EXPECT.items():
    df = pd.read_csv(RAW / name)
    assert len(df) == n, (name, len(df))
    assert list(df.columns) == cols, (name, list(df.columns))
    md5 = hashlib.md5((RAW / name).read_bytes()).hexdigest()
    print(f"ok {name:40s} rows={len(df):4d} md5={md5}")

v = pd.read_csv(RAW / "f50_vintages_real_sa_qoq.csv", index_col=0)
assert v.shape == (195, 286), v.shape
print("ok f50_vintages_real_sa_qoq.csv", v.shape)
