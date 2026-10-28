"""データの取得

この記事では新しくデータを取得していません。これまでの記事で取得・整形した表をそのまま使います。
- data/raw/daily_tokyo_f67.csv.gz, daily_kansai_f67.csv.gz
    F67（articles/F67_temp_power_gam）の data/daily_*.csv を gzip したもの。
    もとは東京電力パワーグリッド・関西電力送配電「エリア需給実績」（1時間ごと）と気象庁「過去の気象データ」（F22 で取得）。
- data/raw/cpi_chubunrui_f12.csv.gz
    F12（articles/F12_stats_pipeline）の data/raw/cpi.csv を gzip したもの。
    総務省統計局「消費者物価指数 2020年基準 長期時系列 中分類指数（全国・月次）」（e-Stat 統計表 000032103842）、1970年1月〜2026年9月。

このスクリプトは、隣の記事フォルダから同じファイルを作り直すためのものです（リポジトリを丸ごと clone した場合）。
"""
import gzip
import shutil
from common import ROOT, RAW

ART = ROOT.parent
pairs = [
    (ART / "F67_temp_power_gam/data/daily_tokyo.csv", RAW / "daily_tokyo_f67.csv.gz"),
    (ART / "F67_temp_power_gam/data/daily_kansai.csv", RAW / "daily_kansai_f67.csv.gz"),
    (ART / "F12_stats_pipeline/data/raw/cpi.csv", RAW / "cpi_chubunrui_f12.csv.gz"),
]
RAW.mkdir(parents=True, exist_ok=True)
for src, dst in pairs:
    if dst.exists():
        print("あり:", dst.name)
        continue
    with open(src, "rb") as f, gzip.open(dst, "wb") as g:
        shutil.copyfileobj(f, g)
    print("作成:", dst.name)
