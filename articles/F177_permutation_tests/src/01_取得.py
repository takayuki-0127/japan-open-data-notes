"""F177 の取得：新しい外部データは取らない。
このリポジトリのほかの記事フォルダから、使う表をそのまま data/raw/ にコピーする。
リポジトリをクローンした状態で、articles/F177_permutation_tests で実行する（data/raw/ に同じファイルが入っていれば不要）。

- F168：30地点の年最高気温の上がり方（100年あたりの位置母数 μ1）と、都市（U）・都市化の影響が少ない地点（R）の区分
- F80 ：都道府県の100指標（社会・人口統計体系 2026年版）、指標名、県の隣接
- F98 ：都道府県×月の日本人延べ宿泊者数（宿泊旅行統計調査）と県の隣接
"""
import shutil
from common import ROOT, RAW

ART = ROOT.parent
COPY = {
    "F168_extreme_heat_trend/results/gev_linear_1901_2025.csv": "f168_gev_linear_1901_2025.csv",
    "F80_multiple_comparisons/data/indicators_2026.csv": "f80_indicators_2026.csv",
    "F80_multiple_comparisons/data/indicator_meta.csv": "f80_indicator_meta.csv",
    "F80_multiple_comparisons/data/adjacency.csv": "f80_adjacency.csv",
    "F80_multiple_comparisons/results/chosen_100.csv": "f80_chosen_100.csv",
    "F98_disaster_lodging_recovery/data/panel.csv": "f98_panel.csv",
    "F98_disaster_lodging_recovery/data/raw/pairs.csv": "f98_pairs.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for src, dst in COPY.items():
        p = ART / src
        if p.exists():
            shutil.copy(p, RAW / dst)
            print("copy", src)
        else:
            print("skip (not found, using data/raw as is):", src)
