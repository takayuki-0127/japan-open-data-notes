"""データの取得

1. 日本版死亡データベース（JMD、国立社会保障・人口問題研究所）全国の
   死亡率 Mx_1x1・死亡数 Deaths_1x1・人口 Exposures_1x1・平均寿命 E0per（1947〜2024年、各歳）
   https://www.ipss.go.jp/p-toukei/JMD/index.asp
2. 社人研『人口統計資料集（2025年版）』表5-12（特定年齢の平均余命：1921〜2070年。
   2045・2070年は『日本の将来推計人口（令和5年推計）』中位の仮定値）、表5-13、表5-6

実際の記事では、コンテナから ipss.go.jp に届かなかったため、ブラウザのページの中で同じURLを取得し、
data/raw/f86_jmd_bundle.json（jmd: 各ファイルの本文、ipss: 表のCSV）にまとめた。
このスクリプトは、ネットワークが届く環境で同じものを作り直す。
"""
import json
import io
import requests
import pandas as pd
from common import RAW

JMD = "https://www.ipss.go.jp/p-toukei/JMD/00/STATS/{}.txt"
IPSS = "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2025/{}.xlsx"


def main():
    out = {"jmd": {}, "ipss": {}}
    for f in ["Mx_1x1", "Deaths_1x1", "Exposures_1x1", "E0per"]:
        r = requests.get(JMD.format(f), timeout=60)
        r.raise_for_status()
        out["jmd"][f] = r.text
    for t, key in [("T05-12", "T0512"), ("T05-13", "T0513"), ("T05-06", "T0506")]:
        df = pd.read_excel(IPSS.format(t), header=None, dtype=str)
        out["ipss"][key] = df.to_csv(index=False, header=False)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "f86_jmd_bundle.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("saved", RAW / "f86_jmd_bundle.json")


if __name__ == "__main__":
    main()
