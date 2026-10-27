"""02 整形：都道府県×年度×学校種×教科の表を作る。

正答数ごとの人数から、平均正答率を小数まで計算し直す（公表値は2017年度以降、整数に丸められている）。
標本誤差の目安として、正答率の標準誤差 = 標準偏差 ÷ √人数 ÷ 問題数 × 100 も計算する。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREF = ("北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 "
        "岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 "
        "佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄").split()


def main():
    raw = json.loads((ROOT / "data/raw/nier_pref_2019_2026.json").read_text())
    rec = []
    for r in raw:
        n, items, pub = r["raw"][1], r["raw"][4], r["raw"][5]
        k = np.array([int(x) for x in r["dist"]])
        c = np.array(list(r["dist"].values()), float)
        assert c.sum() == n, (r["year"], r["pref"], r["subject"])
        m = (k * c).sum() / n
        sd = np.sqrt(((k - m) ** 2 * c).sum() / (n - 1))
        subj = "算数・数学" if r["subject"] in ("算数", "数学") else "国語"
        rec.append(dict(year=r["year"], level=r["level"], subject=subj, pref_code=int(r["pref"]),
                        pref=PREF[int(r["pref"]) - 1], n=n, items=items, rate_pub=pub,
                        rate=m / items * 100, sd_items=sd, se_rate=sd / np.sqrt(n) / items * 100,
                        nat_rate_pub=r["natraw"][5]))
    df = pd.DataFrame(rec).sort_values(["level", "subject", "year", "pref_code"])
    # 全国（公立）の正答率は、47都道府県の人数で重みをつけた平均で計算し直す
    g = df.groupby(["year", "level", "subject"])
    df["wr"] = df["rate"] * df["n"]
    df["nat_rate"] = g["wr"].transform("sum") / g["n"].transform("sum")
    df = df.drop(columns="wr")
    df["diff"] = df["rate"] - df["nat_rate"]
    df["rank"] = g["rate"].rank(ascending=False, method="average")
    df["rank_pub"] = g["rate_pub"].rank(ascending=False, method="min")
    df.to_csv(ROOT / "data/pref_scores.csv", index=False)
    chk = (df["rate"].round(0) - df["rate_pub"]).abs().max()
    print(len(df), "最大の差（再計算の四捨五入 − 公表値）", chk)


if __name__ == "__main__":
    main()
