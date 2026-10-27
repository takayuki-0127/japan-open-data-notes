"""表12-33 を「都道府県×年」の縦長の表にする"""
import numpy as np
import pandas as pd
from common import RAW, DATA

PREFS = ["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川",
         "新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良",
         "和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分",
         "宮崎","鹿児島","沖縄"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


if __name__ == "__main__":
    r = pd.read_csv(RAW / "ipss_T12-33_tfr_pref.csv", header=None, dtype=str, encoding="utf-8-sig")
    hdr = r.iloc[1].tolist()
    years = [int(str(h).replace("年", "")) for h in hdr[1:] if str(h).strip() and str(h) != "nan"]
    out = []
    for _, row in r.iloc[3:].iterrows():
        name = str(row[0]).strip()
        if name in ["全国"] + PREFS:
            for k, y in enumerate(years):
                v = num(row[k + 1])
                if not np.isnan(v):
                    out.append(dict(pref=name, year=y, tfr=v))
    d = pd.DataFrame(out)
    d.to_csv(DATA / "tfr_long.csv", index=False)
    nat = d[d.pref == "全国"].sort_values("year")
    print(len(d), d.pref.nunique(), "national years", nat.year.min(), nat.year.max(), len(nat))
    print(d[d.pref != "全国"].groupby("year").size().loc[1969:1973])
