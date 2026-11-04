from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2018, 2026))
# e-Stat の統計表ID（人口動態統計 確定数）
STAT_IDS = {
    "hokan_shussei_t07_2025": "000040503807",
    "hokan_shussei_t07_2024": "000040320531",
    "hokan_shussei_t07_2023": "000040207269",
    "hokan_shussei_t07_2022": "000040101676",
    "hokan_shussei_t07_2021": "000032241418",
    "hokan_shussei_t07_2020": "000032118682",
    "hokan_shussei_t07_2019": "000031981666",
    "hokan_shussei_t07_2018": "000031881466",
    "joukan_shussei_t4_2_2025": "000040503641",  # 上巻 出生 第4.2表 出生月別にみた年次別出生数
    "joukan_shibou_t5_4_2025": "000040502537",   # 上巻 死亡 第5.4表 死亡月別にみた年次別死亡数
}
PLACES = ["総数", "病院", "診療所", "助産所", "自宅", "その他"]
WD = ["月", "火", "水", "木", "金", "土", "日"]
