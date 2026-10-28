"""01 取得：F12（e-Stat から取り込み済み）の消費者物価指数・毎月勤労統計と、F18 の実質GDP（季節調整済み）を写す。
元の取得手順は F12_stats_pipeline/src と F18_nowcast_dfm/src を参照。
- cpi.csv  : 消費者物価指数 2020年基準 長期時系列 中分類指数（全国・月次） statInfId 000032103842
- wage.csv : 毎月勤労統計調査 全国調査 長期時系列（指数）            statInfId 000032189777（調査産業計・5人以上・就業形態計）
- gdp_real_sa.csv : 内閣府 四半期別GDP速報 実質・季節調整系列（1994Q1〜）
"""
import shutil, pathlib
H = pathlib.Path(__file__).resolve().parents[1]
A = H.parent
for src in [A/'F12_stats_pipeline/data/raw/cpi.csv', A/'F12_stats_pipeline/data/raw/wage.csv', A/'F18_nowcast_dfm/data/raw/gdp_real_sa.csv']:
    if src.exists():
        shutil.copy(src, H/'data/raw'/src.name); print('copied', src.name)
    else:
        print('use the copy already in data/raw:', src.name)
