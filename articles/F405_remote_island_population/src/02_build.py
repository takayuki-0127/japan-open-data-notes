"""02 整形：国勢調査「都道府県・市区町村別の主な結果」2015・2020・2025年と、離島振興対策実施地域一覧（PDF のテキスト）から、
市町村の表 data/municipalities.csv を作る。オフライン。"""
import pathlib, re
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"

# 町全体が離島振興対策実施地域の島でできている市町村（一覧の島の2020年の人口の合計を、PDF から作成者が足したもの）
ISLAND = [
    ("北海道", "礼文町", [2509]), ("北海道", "利尻町", [2004]), ("北海道", "利尻富士町", [2458]), ("北海道", "奥尻町", [2410]),
    ("東京都", "大島町", [7102]), ("東京都", "利島村", [327]), ("東京都", "新島村", [1967, 474]), ("東京都", "神津島村", [1855]),
    ("東京都", "三宅村", [2273]), ("東京都", "御蔵島村", [323]), ("東京都", "八丈町", [7042]), ("東京都", "青ヶ島村", [169]),
    ("新潟県", "粟島浦村", [353]), ("新潟県", "佐渡市", [51492]),
    ("島根県", "隠岐の島町", [13433]), ("島根県", "海士町", [2267]), ("島根県", "西ノ島町", [2788]), ("島根県", "知夫村", [634]),
    ("広島県", "大崎上島町", [11, 7084, 30]),
    ("香川県", "土庄町", [12011, 58, 9, 768]), ("香川県", "小豆島町", [13870]), ("香川県", "直島町", [3071, 20, 12]),
    ("愛媛県", "上島町", [11, 138, 2599, 428, 1389, 1942, 2]),
    ("長崎県", "五島市", [1927, 23, 255, 9, 95, 31945, 10, 32, 1, 15, 79]), ("長崎県", "壱岐市", [24678, 15, 71, 91, 93]),
    ("長崎県", "対馬市", [28374, 51, 9, 25, 18, 25]), ("長崎県", "小値賀町", [1, 1, 21, 2015, 38, 61, 151]),
    ("長崎県", "新上五島町", [16112, 14, 6, 1218, 27, 100, 26]),
    ("大分県", "姫島村", [1725]),
    ("鹿児島県", "西之表市", [14706, 2]), ("鹿児島県", "中種子町", [7539]), ("鹿児島県", "南種子町", [5445]),
    ("鹿児島県", "屋久島町", [11765, 93]), ("鹿児島県", "三島村", [72, 139, 194]), ("鹿児島県", "十島村", [103, 146, 78, 107, 90, 69, 147]),
]
# 別の法律の離島（奄美群島振興開発特別措置法・小笠原諸島振興開発特別措置法）。本土の側から除く。沖縄県も全部除く
OTHER_ISLAND = [("鹿児島県", n) for n in ["奄美市", "大和村", "宇検村", "瀬戸内町", "龍郷町", "喜界町", "徳之島町", "天城町",
                                           "伊仙町", "和泊町", "知名町", "与論町"]] + [("東京都", "小笠原村")]
REGION = {1: "北海道", **{p: "東北" for p in range(2, 8)}, **{p: "関東" for p in range(8, 15)}, **{p: "中部" for p in range(15, 24)},
          **{p: "近畿" for p in range(24, 31)}, **{p: "中国" for p in range(31, 36)}, **{p: "四国" for p in range(36, 40)},
          **{p: "九州" for p in range(40, 48)}}

def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan

def read_new(path, year):
    d = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    d = d[d[1].astype(str).str.match(r"^\d{5}_")]
    out = pd.DataFrame({
        "code": d[1].str[:5], "pref": d[0].str[3:], "name": d[1].str[6:], "kind": d[3].astype(str),
        f"pop{year}": d[4].map(f), f"pop{year-5}r": d[7].map(f),
        f"a0_14_{year}": d[14].map(f), f"a15_64_{year}": d[15].map(f), f"a65_{year}": d[16].map(f)})
    return out.reset_index(drop=True)

def read_2015(path):
    d = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    d = d[d[1].astype(str).str.match(r"^\d{5}$")]
    out = pd.DataFrame({
        "code": d[1].astype(str), "pref": d[6].astype(str), "name": d[7].astype(str).str.replace(r"^.*　", "", regex=True),
        "kind": d[5].astype(str), "metro2015": (d[2].notna() | d[3].notna()).astype(int), "pop2015": d[8].map(f), "pop2010r": d[9].map(f),
        "a0_14_2015": d[17].map(f), "a15_64_2015": d[18].map(f), "a65_2015": d[19].map(f)})
    return out.reset_index(drop=True)

def main():
    c25 = read_new(RAW / "census_2025_main_000040507382.xlsx", 2025)
    c20 = read_new(RAW / "census_2020_main_000032143614.xlsx", 2020)
    c15 = read_2015(RAW / "census_2015_main_000031594311.xls")
    m = c25[c25.kind.isin(["1", "2", "3"])].copy()
    m = m.merge(c20[["code", "pop2020", "pop2015r", "a15_64_2020", "a65_2020"]], on="code", how="left")
    m = m.merge(c15[["code", "metro2015", "pop2015", "pop2010r", "a0_14_2015", "a15_64_2015", "a65_2015"]], on="code", how="left")
    m["pcode"] = m.code.str[:2].astype(int)
    m["region"] = m.pcode.map(REGION)

    txt = (RAW / "mlit_ritou_list_R8_001886615.txt").read_text(encoding="utf-8")
    flat = re.sub(r"\s+", "", txt)
    isl = pd.DataFrame([(p, n, sum(v)) for p, n, v in ISLAND], columns=["pref", "name", "pdf_pop2020"])
    for n in isl.name:
        assert n in flat, n
    m = m.merge(isl, on=["pref", "name"], how="left")
    m["island"] = m.pdf_pop2020.notna()
    assert m.island.sum() == len(ISLAND)
    # 確かめ：一覧の島の人口の合計が、その市町村の2020年の人口と一致する（＝町全体が島）
    chk = m[m.island]
    # 大崎上島町だけ 33人（0.5%）合わない（一覧に載らない小さな島の分と考えられる。町は全部が島）
    gap = (chk.pop2020 - chk.pdf_pop2020) / chk.pop2020
    assert gap.abs().max() < 0.01, chk[["name", "pdf_pop2020", "pop2020"]]
    print("mismatch:", chk.loc[gap != 0, ["name", "pdf_pop2020", "pop2020"]].values.tolist())
    # 一部が島の市町村（一覧に名前がある）・別の法律の離島・沖縄県は、本土の側から除く
    names_in = sorted({n for n in m.name if n in flat})
    def listed(n):
        # 「関市」が「下関市」の一部として出てくるだけ、のような場合は数えない
        if n not in flat:
            return False
        longer = [n2 for n2 in names_in if n2 != n and n2.endswith(n)]
        return flat.count(n) > sum(flat.count(n2) for n2 in longer)
    m["partial_island"] = (~m.island) & m.name.map(listed)
    other = set(OTHER_ISLAND)
    m["other_law_island"] = [(p, n) in other or pc == 47 for p, n, pc in zip(m.pref, m.name, m.pcode)]
    m["group"] = np.where(m.island, "island",
                          np.where(m.partial_island | m.other_law_island, "excluded", "mainland"))
    cols = ["code", "pref", "name", "kind", "pcode", "region", "metro2015", "group", "pdf_pop2020",
            "pop2010r", "pop2015", "pop2015r", "pop2020", "pop2020r", "pop2025",
            "a0_14_2015", "a15_64_2015", "a65_2015", "a15_64_2020", "a65_2020", "a0_14_2025", "a15_64_2025", "a65_2025"]
    print("partial:", m[m.partial_island].name.tolist())
    print("other:", m[m.other_law_island & (m.pcode != 47)].name.tolist())
    m = m[cols].sort_values("code", kind="mergesort").reset_index(drop=True)
    m.to_csv(BASE / "data" / "municipalities.csv", index=False, lineterminator="\n")
    print(m.group.value_counts().to_dict())
    print("missing 2020 link:", m[m.pop2020.isna()].name.tolist(), "missing 2015 link:", m[m.pop2015.isna()].name.tolist())

if __name__ == "__main__":
    main()
