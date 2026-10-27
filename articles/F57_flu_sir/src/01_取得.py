"""データの取得。

F57 は新しくデータを取っていない。F52（インフルエンザはどの県からどの県へ広がるのか）で取った
感染症発生動向調査（IDWR 速報データ）の「定点把握疾患 都道府県別 報告数・定点当たり報告数」
（*-teiten.csv）から抜き出したインフルエンザの列（data/raw/f52_teiten_flu.json）をそのまま使う。

取り直すときは、F52 の src/01_取得.py を実行して f52_teiten_flu.json を作り、data/raw/ に置く。
  https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F52_influenza_spread

人口（pref_pop_F10.csv）と都道府県の一覧（pref_points_F33.csv）も、F10・F33 のデータのコピー。
"""
from common import RAW

if __name__ == "__main__":
    for f in ["f52_teiten_flu.json", "pref_pop_F10.csv", "pref_points_F33.csv"]:
        p = RAW / f
        print(f, "ok" if p.exists() else "なし（F52 の 01_取得.py で作る）")
