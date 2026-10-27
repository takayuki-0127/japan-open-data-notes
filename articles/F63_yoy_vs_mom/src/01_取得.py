"""01 取得：このリポジトリの F42・F35 で取得したデータを使う（新しい取得はない）。
- data/raw/f42_series.csv：F42 の data/series.csv（鉱工業指数・労働力調査・一般職業紹介状況の原数値と公表の季節調整値）
- data/raw/f35_ci_iip_monthly.csv：F35 の data/raw/ci_iip_monthly.csv（景気動向指数 CI一致・先行）
- data/raw/cycle_dates.csv：内閣府の景気基準日付（F35 と同じ）
取り直すときは、F42・F35 の src/01_取得.py を動かしてから、それぞれのファイルをここにコピーする。"""
import shutil
from common import ROOT, RAW

SRC = {
    "f42_series.csv": ROOT.parent / "F42_seasonal_adjustment" / "data" / "series.csv",
    "f35_ci_iip_monthly.csv": ROOT.parent / "F35_business_cycle_markov" / "data" / "raw" / "ci_iip_monthly.csv",
    "cycle_dates.csv": ROOT.parent / "F35_business_cycle_markov" / "data" / "raw" / "cycle_dates.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, src in SRC.items():
        if (RAW / name).exists():
            print("同梱済み:", name)
        elif src.exists():
            shutil.copy(src, RAW / name)
            print("コピー:", name)
        else:
            raise FileNotFoundError(f"{src} がありません。F42/F35 の取得スクリプトを先に動かしてください")
