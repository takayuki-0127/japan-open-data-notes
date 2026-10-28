"""元データを取ってくる（どれも前の記事で取ったものを GitHub から再利用）。

- 都道府県間の移動者数（日本人、1989〜2025年）：F33 の data/panel.csv
  （住民基本台帳人口移動報告 長期時系列表 第11表 と 2025年 表2）
- 都道府県の日本人人口・出生数・死亡数（2012〜2023年）：SSDSE-B-2026（F10 の data/raw）
- 社人研「日本の地域別将来推計人口（令和5年推計）」の都道府県×男女×5歳：F45 の data/pop_2023.csv
- 令和7年国勢調査の都道府県×男女×5歳：F45 の data/pop_census2025.csv
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "f33_panel.csv": "F33_migration_gravity/data/panel.csv",
    "SSDSE-B-2026.csv": "F10_mobility_network/data/raw/SSDSE-B-2026.csv",
    "ipss2023_pop.csv": "F45_population_projection/data/pop_2023.csv",
    "census2025_pop.csv": "F45_population_projection/data/pop_census2025.csv",
}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり", name)
        continue
    urllib.request.urlretrieve(BASE + path, out)
    print("取得", name)
