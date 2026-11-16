"""01 取得：新しいダウンロードはしない。

前の記事で取ったデータを data/raw/ にコピーして使う。
- f19_screening_long.csv … F19（articles/F19_small_area_fh/data/screening_long.csv）
    厚生労働省「地域保健・健康増進事業報告」市区町村表 第20-1表、
    国保の被保険者 40〜69歳の大腸がん・肺がん検診の対象者数と受診者数（2021〜2024年度）
- f27_smr_2018_22.csv … F27（articles/F27_disease_map_bym2/data/smr_2018_22.csv）
    厚生労働省「人口動態保健所・市区町村別統計」H30〜R4 の死亡数・期待死亡数・標準化死亡比

F19・F27 のフォルダから取り直す場合は、それぞれの src/01_取得 を実行してから
このファイルと同じ名前で data/raw/ に置く。
"""
import shutil
import urllib.request
from common import RAW, ROOT

SRC = {
    "f19_screening_long.csv": ROOT.parent / "F19_small_area_fh" / "data" / "screening_long.csv",
    "f27_smr_2018_22.csv": ROOT.parent / "F27_disease_map_bym2" / "data" / "smr_2018_22.csv",
}
# F27 の記事フォルダは削除したので、手元にないときは削除前の版（コミット c56ebc6）から取る
PIN_URL = {"f27_smr_2018_22.csv": "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c56ebc67126a738058bdae7c172e7b29473f9286/articles/F27_disease_map_bym2/data/smr_2018_22.csv"}

if __name__ == "__main__":
    for name, src in SRC.items():
        dst = RAW / name
        if dst.exists():
            print("あり:", dst.name)
        elif src.exists():
            shutil.copy(src, dst)
            print("コピー:", src, "->", dst)
        elif name in PIN_URL:
            urllib.request.urlretrieve(PIN_URL[name], dst)
            print("取得（削除前の版）:", dst.name)
        else:
            print("見つからない:", src, "（F19・F27 の 01 を先に実行）")
