"""02_build.py : 家計消費状況調査 年報（2015〜2025年）の Excel から、使う行だけを縦長の CSV にする（オフライン）。
出力：data/age_items.csv（年・世帯区分・年齢・項目・値）、data/national_items.csv（年・世帯区分・項目・支出世帯の額・割合）
"""
import pathlib
import re
import unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
YEARS = range(2015, 2026)
AGES = (["平均"] + [f"5:{a}" for a in ["-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-"]]
        + [f"A:{a}" for a in ["-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85-"]] + ["A:65-"]
        + [f"B:{a}" for a in ["-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-"]] + ["B:60-", "B:70-"])
SHEETS = {"総世帯": "total", "二人以上世帯": "two_plus"}
ITEMS = {  # 正規化した項目名 → key
    "世帯数分布(抽出率調整)": "weight", "世帯人員": "hh_size", "世帯主の年齢": "head_age",
    "インターネットを利用した支出総額(22品目計)": "net_total",
    "電子書籍": "ebook", "ダウンロード版の音楽・映像、アプリなど": "download",
    "音楽・映像ソフト、パソコン用ソフト、ゲームソフト": "soft", "書籍": "book",
    "計(デジタルコンテンツ)": "digital",
    "インターネットを通じて注文をした世帯(1万分比)": "order_rate",
    "インターネットを通じて注文をした世帯当たりの支出総額": "net_total_per_orderer",
    "インターネットを通じて注文をした": "order_pct",
}


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    s = re.sub(r"[\s　]+", "", s)
    s = s.replace("〔自宅用〕", "").replace("(人)", "").replace("(歳)", "").replace("(円)", "")
    s = re.sub(r"^\d+~\d+計\(", "計(", s)     # 「66~67計(デジタルコンテンツ)」（2019年まで）
    s = re.sub(r"^\d+(_\d+)?", "", s)          # 先頭の品目番号（64 や 66_67）
    s = re.sub(r"^\(インターネットを利用した支出総額\)", "", s)
    return s


def layout(df):
    """(項目の列, 値の最初の列)。新しい様式（2020年〜）は「一連番号」の見出しがある。"""
    if str(df.iloc[7, 7]) == "一連番号":
        hdr = [str(c) for c in df.iloc[7].tolist()]
        lc = hdr.index("項目")
        return lc, hdr.index("平均") if "平均" in hdr else lc + 2
    return 7, 8


def read_age_table(path, kind):
    out = []
    xl = pd.read_excel(path, sheet_name=None, header=None)
    for sh, hh in SHEETS.items():
        df = xl[sh]
        lc, vc = layout(df)
        for i in range(len(df)):
            key = ITEMS.get(norm(df.iloc[i, lc]))
            if key is None:
                continue
            vals = df.iloc[i, vc:vc + len(AGES)].tolist()
            for a, v in zip(AGES, vals):
                v = pd.to_numeric(v, errors="coerce")
                out.append({"table": kind, "hh": hh, "age": a, "item": key, "value": v})
    df = xl["単身世帯"]                                 # 単身世帯は年齢の区分が違う（総数の4列だけ使う）
    lc, vc = layout(df)
    for i in range(len(df)):
        key = ITEMS.get(norm(df.iloc[i, lc]))
        if key is None:
            continue
        for a, v in zip(["S:平均", "S:-34", "S:35-59", "S:60-"], df.iloc[i, vc:vc + 4].tolist()):
            out.append({"table": kind, "hh": "single", "age": a, "item": key, "value": pd.to_numeric(v, errors="coerce")})
    return out


def read_national(path, kind):
    out = []
    xl = pd.read_excel(path, sheet_name=None, header=None)
    for sh, hh in SHEETS.items():
        df = xl[sh]
        lc, vc = layout(df)
        for i in range(len(df)):
            lab = norm(df.iloc[i, lc])
            key = ITEMS.get(lab)
            if key in ("ebook", "download", "soft", "book", "digital", "net_total"):
                out.append({"table": kind, "hh": hh, "item": key, "value": pd.to_numeric(df.iloc[i, vc], errors="coerce")})
    return out


def main():
    rows, nat = [], []
    for y in YEARS:
        for kind in ("t1_2", "t4_2"):
            p = next(RAW.glob(f"kcs_{kind}_{y}.xls*"))
            for r in read_age_table(p, kind):
                rows.append({"year": y, **r})
        for kind in ("t6_1", "t6_2"):
            p = next(RAW.glob(f"kcs_{kind}_{y}.xls*"))
            for r in read_national(p, kind):
                nat.append({"year": y, **r})
    a = pd.DataFrame(rows).drop_duplicates(["year", "table", "hh", "age", "item"], keep="first")
    a = a.sort_values(["year", "table", "hh", "item", "age"]).reset_index(drop=True)
    a.to_csv(ROOT / "data" / "age_items.csv", index=False)
    n = pd.DataFrame(nat).drop_duplicates(["year", "table", "hh", "item"], keep="first")
    n = n.sort_values(["year", "table", "hh", "item"]).reset_index(drop=True)
    n.to_csv(ROOT / "data" / "national_items.csv", index=False)
    print(a.groupby(["table", "item"]).year.agg(["min", "max", "count"]))
    print(n.groupby(["table", "item"]).year.agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
