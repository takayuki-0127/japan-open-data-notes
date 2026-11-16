"""F123 01 取得：新しいデータは取らず、これまでの記事のデータを再利用する。
リポジトリ japan-open-data-notes の兄弟フォルダからコピーし、MD5 で同じものか確かめる。
3つの記事フォルダは削除済みなので、手元にないときは削除前の版（コミット c56ebc6）から取る。
- 地価：F03_land_price_ml/data/features.csv（地価公示 2026年、25,565地点・特徴量つき）
- 出生率：F107_gcn_municipal/data/nodes.csv（市区町村の合計特殊出生率 2018〜22年と指標、1,841区域）
- 気温：F74_temperature_kriging/data/normals_mean_temp.csv（アメダスの年平均気温の平年値、915地点）
"""
import hashlib, shutil, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT.parent
SRC = {"land_price_features.csv": ART / "F03_land_price_ml/data/features.csv",
       "municipal_tfr.csv": ART / "F107_gcn_municipal/data/nodes.csv",
       "amedas_normals.csv": ART / "F74_temperature_kriging/data/normals_mean_temp.csv"}
# F03・F107・F74 の記事フォルダは削除したので、手元にないときは削除前の版（コミット c56ebc6）から取る
PIN = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c56ebc67126a738058bdae7c172e7b29473f9286/articles/"
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()
(ROOT / "data").mkdir(exist_ok=True)
for name, src in SRC.items():
    dst = ROOT / "data" / name
    if src.exists():
        if not dst.exists() or md5(src) != md5(dst):
            shutil.copy(src, dst)
        print(name, "←", src.relative_to(ART), md5(dst))
    else:
        urllib.request.urlretrieve(PIN + str(src.relative_to(ART)).replace("\\", "/"), dst)
        print(name, "← 削除前の版", src.relative_to(ART), md5(dst))
