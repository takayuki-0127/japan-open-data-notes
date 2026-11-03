"""賃金構造基本統計調査（短時間労働者 都道府県別第1表）から、47都道府県×年の
1時間当たり所定内給与額と労働者数（企業規模計10人以上・産業計・男女計）を取り出す。

元の Excel は e-Stat からブラウザで取得し（statInfId は data/raw/SOURCES.md）、SheetJS で
シートごとの表を JSON にしたもの（約11MB、リポジトリには置かない）を読み込む。
使い方: python 01_取得.py <json1> [<json2> ...]
"""
import json, re, sys, unicodedata
import pandas as pd
from common import DATA, PREFS

ERA = {"平成": 1988, "令和": 2018}
# 表題に年が書かれていない2ファイル群（e-Stat の掲載位置で年を確認）
ID_YEAR = {"0000072": 2009, "0000073": 2009, "0000082": 2010, "0000083": 2010}

def nk(s):
    return unicodedata.normalize("NFKC", str(s)).replace("\n", "").replace("\r", "").replace(" ", "").replace("　", "")

def year_of(fid, rows):
    for r in rows[:15]:
        for c in r:
            m = re.search(r"(平成|令和)(\d+|元)年", nk(c))
            if m:
                return ERA[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2)))
    return ID_YEAR.get(fid[:7])

out = []
for fn in sys.argv[1:]:
    for fid, v in json.load(open(fn)).items():
        for sn, rows in v.items():
            if sn.startswith("_") or sn == "err" or sn not in PREFS:
                continue
            y = year_of(fid, rows)
            hi = next((i for i, r in enumerate(rows[:20]) if any(nk(c) == "1時間当たり所定内給与額" for c in r)), None)
            if hi is None:
                continue
            H = [nk(c) for c in rows[hi]]
            wcol = H.index("1時間当たり所定内給与額")
            ncol = H.index("労働者数") if "労働者数" in H else None
            for r in rows[hi + 1:]:
                t = "".join(nk(c) for c in r[:10])
                if "企業規模計" in t and "産業計" in t:
                    out.append(dict(pref=sn, year=y, wage=r[wcol], workers10=r[ncol] if ncol is not None else None))
                    break
df = pd.DataFrame(out).drop_duplicates(["pref", "year"]).sort_values(["year", "pref"])
df["code"] = df["pref"].map({p: i + 1 for i, p in enumerate(PREFS)})
df = df[["code", "pref", "year", "wage", "workers10"]].sort_values(["code", "year"])
assert df.groupby("year").size().eq(47).all(), df.groupby("year").size()
df.to_csv(DATA / "raw" / "wage_short_pref_2009_2025.csv", index=False)
print(df.groupby("year")["wage"].agg(["count", "mean", "min", "max"]))
