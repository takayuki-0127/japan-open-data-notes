"""data/raw/kouhai_<年>.pdf の「都道府県別の荒廃農地面積」の表（資料2）を CSV に抜き出す。
pdftotext（poppler 24.02.0）を使う。run_all.sh からは呼ばない（抜き出した data/kouhai_pref_raw.csv から先がオフラインで再現できる）。
2018年の PDF は字形の対応表が壊れていて、数字が U+3EDC〜U+3EE5（0〜9）、U+3ED8（,）として出るので、数字に戻す。
県名が読めない年があるので、行の順（PDF の表の順：北海道〜沖縄、全国）で県を決め、全国の行との合計の一致で確かめる（02_build.py）。"""
import pathlib, re, subprocess
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
JIS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
       "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
       "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
       "宮崎", "鹿児島", "沖縄"]
CODE = {p: i for i, p in enumerate(JIS, start=1)}
# PDF の表の行の順（農水省の地域ブロック順）。JIS の順とは山梨・長野・静岡（関東の後）と北陸4県・岐阜の位置が違う。
# （独立レビューで直した：以前は JIS の順で当てていたため、15〜22行目の8県の名前がずれていた）
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "山梨", "長野", "静岡", "新潟", "富山", "石川", "福井", "岐阜", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄", "全国"]
# 年ごとの列の並び（PDF の表の左から）
COLS4 = ["total", "A", "B", "reclaimed"]
COLS8 = ["total", "total_n", "A", "A_n", "B", "B_n", "reclaimed", "reclaimed_n"]
COLS10 = ["new", "new_n", "reclaimed", "reclaimed_n", "A", "A_n", "B", "B_n", "total", "total_n"]
LAYOUT = {2011: COLS4, 2012: COLS4, **{y: COLS8 for y in range(2013, 2021)}, **{y: COLS10 for y in range(2021, 2025)}}
FIX = {chr(0x3EDC + d): str(d) for d in range(10)}
FIX[chr(0x3ED8)] = ","
NUM = re.compile(r"^[\d,]+$")


def rows_of(year):
    txt = subprocess.run(["pdftotext", "-layout", str(RAW / f"kouhai_{year}.pdf"), "-"], capture_output=True, check=True).stdout.decode("utf-8")
    txt = "".join(FIX.get(c, c) for c in txt)
    ncol = len(LAYOUT[year])
    cand = []
    for line in txt.splitlines():
        tok = line.split()
        if len(tok) < ncol + 1:
            continue
        nums = tok[-ncol:]
        head = tok[:-ncol]
        if all(NUM.match(t) for t in nums) and not re.search(r"[0-9]", "".join(head)):
            cand.append([int(t.replace(",", "")) for t in nums])
    # 都道府県別の表は、条件に合う行が48行続く最後のかたまり
    assert len(cand) >= 48, (year, len(cand))
    return cand[-48:]


def main():
    out = []
    for y, cols in LAYOUT.items():
        rows = rows_of(y)
        for p, v in zip(PREFS, rows):
            rec = {"year": y, "pref_code": CODE.get(p, 0), "pref": p}
            rec.update(dict(zip(cols, v)))
            out.append(rec)
    df = pd.DataFrame(out)
    cols = ["year", "pref_code", "pref", "total", "A", "B", "reclaimed", "new", "total_n", "A_n", "B_n", "reclaimed_n", "new_n"]
    df = df.reindex(columns=cols).sort_values(["year", "pref_code"], key=lambda c: c.where(c != 0, 99) if c.name == "pref_code" else c, kind="stable").reset_index(drop=True)
    df.to_csv(ROOT / "data" / "kouhai_pref_raw.csv", index=False, encoding="utf-8")
    print(df.groupby("year").size().to_dict())


if __name__ == "__main__":
    main()
