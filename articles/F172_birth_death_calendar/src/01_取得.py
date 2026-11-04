"""データの取得（e-Stat、人口動態統計 確定数の CSV）。
- 保管統計表 出生 第7表「出生数，出生の場所・出生月・出生日・出生時別」2018〜2025年（1年1ファイル）
- 上巻 出生 第4.2表「出生月別にみた年次別出生数及び出生率」（2025年版、1947年〜）
- 上巻 死亡 第5.4表「死亡月別にみた年次別死亡数及び死亡率」（2025年版、1947年〜）
e-Stat の CSV は Shift_JIS。data/raw/ には UTF-8 に直して保存しています。
"""
import requests
from common import RAW, STAT_IDS

URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"

if __name__ == "__main__":
    for name, sid in STAT_IDS.items():
        b = requests.get(URL.format(sid), timeout=120).content
        (RAW / f"{name}.csv").write_text(b.decode("cp932"), encoding="utf-8")
        print(name, len(b))
