"""02 整形: e-Stat の長期累年表（JSON化したもの）から、魚種別・漁業種類別の年次パネルを作る
入力 : data/raw/f143_fish_longterm.json （01_取得.md の手順で取得）
出力 : data/species_long.csv, data/species_wide.csv, data/gear_wide.csv
"""
import json, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = json.load(open(ROOT / "data/raw/f143_fish_longterm.json", encoding="utf-8"))


def year_of(s):
    m = re.search(r"\((\d{4})\)", str(s))
    return int(m.group(1)) if m else None


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    v = str(v).strip().replace(",", "")
    try:
        return float(v)
    except ValueError:
        return np.nan  # "…"（調査なし・分類なし）、"x"（秘匿）、"-"（なし）は欠測扱い


def table(sheet, nhead, hrow=4):
    H = sheet[hrow:hrow + nhead]
    cur = [""] * nhead
    names = []
    for j in range(len(sheet[hrow])):
        for i in range(nhead):
            if H[i][j] != "":
                cur[i] = str(H[i][j]).strip()
                for k in range(i + 1, nhead):
                    cur[k] = ""
        names.append("/".join(c for c in cur if c))
    rows = [r for r in sheet if year_of(r[0])]
    df = pd.DataFrame([[num(v) for v in r] for r in rows], columns=names)
    df.insert(0, "year", [year_of(r[0]) for r in rows])
    df = df.loc[:, ~df.columns.duplicated()]
    return df.drop(columns=["年次"]).set_index("year")


# ---------- 魚種別 ----------
sp = table(D["000040416370"]["Sheet1"], 3)
# 末端の魚種だけ（計・小計・その他は除く）
leaf = [c for c in sp.columns if not re.search(r"計|小計|その他", c) and c != "漁獲量計"]
# 親が「小計」だけの列（例：魚類/さば類）も末端として残る
long = sp[leaf].reset_index().melt(id_vars="year", var_name="path", value_name="t")
long["species"] = long.path.str.split("/").str[-1]
long["group"] = long.path.str.split("/").str[0]
long.to_csv(ROOT / "data/species_long.csv", index=False)
wide = sp[leaf].copy()
wide.columns = [c.split("/")[-1] for c in wide.columns]
wide["漁獲量計"] = sp["漁獲量計"]
wide.to_csv(ROOT / "data/species_wide.csv")

# ---------- 漁業種類別（分類の変更をまたいで続く主な漁業種類にまとめる） ----------
g = table(D["000040416369"]["Sheet1"], 5)


def pick(df, prefixes, total=None):
    """total 列があればそれを、なければ prefixes の列の合計（全部欠測なら欠測）"""
    cols = [c for c in df.columns if any(c.startswith(p) for p in prefixes)]
    s = df[cols].sum(axis=1, min_count=1)
    if total and total in df.columns:
        s = df[total].combine_first(s)
    return s


gear = pd.DataFrame({
    "大中型まき網": pick(g, ["網漁業/まき網/大中型まき網/1そうまき/", "網漁業/まき網/大中型まき網/2そうまき網/2そうまき網計"]),
    "中・小型まき網": pick(g, ["網漁業/まき網/中・小型まき網/"]),
    "沖合底びき網": pick(g, ["網漁業/底びき網/沖合底びき網/1そうびき", "網漁業/底びき網/沖合底びき網/2そうびき"],
                       total="網漁業/底びき網/沖合底びき網/沖合底びき網計"),
    "小型底びき網": pick(g, ["網漁業/底びき網/小型底びき網/"]),
    "船びき網": pick(g, ["網漁業/船びき網/ひき回し網", "網漁業/船びき網/ひき寄せ網"], total="網漁業/船びき網/船びき網計"),
    "定置網": pick(g, ["網漁業/定置網/"]),
    "さんま棒受網": g["網漁業/敷網/さんま棒受網"],
    "まぐろはえ縄": pick(g, ["釣漁業/はえ縄/まぐろはえ縄/遠洋まぐろはえ縄/計", "釣漁業/はえ縄/まぐろはえ縄/近海",
                          "釣漁業/はえ縄/まぐろはえ縄/沿岸", "釣漁業/はえ縄/まぐろはえ縄/母船式まぐろはえ縄/計"],
                       total="釣漁業/はえ縄/まぐろはえ縄/まぐろはえ縄計"),
    "かつお一本釣": pick(g, ["釣漁業/はえ縄以外の釣/かつお一本釣/遠洋", "釣漁業/はえ縄以外の釣/かつお一本釣/近海",
                          "釣漁業/はえ縄以外の釣/かつお一本釣/沿岸"], total="釣漁業/はえ縄以外の釣/かつお一本釣/計"),
    "いか釣": pick(g, ["釣漁業/はえ縄以外の釣/いか釣/遠洋", "釣漁業/はえ縄以外の釣/いか釣/近海",
                     "釣漁業/はえ縄以外の釣/いか釣/沖合", "釣漁業/はえ縄以外の釣/いか釣/沿岸"],
                 total="釣漁業/はえ縄以外の釣/いか釣/いか釣計"),
    "刺網": pick(g, ["網漁業/刺網/"]),
})
gear["漁獲量計"] = g["漁獲量計"]
gear.to_csv(ROOT / "data/gear_wide.csv")
print(wide.shape, gear.shape)
print(gear.loc[[1960, 1980, 2000, 2024]].round(-2))
