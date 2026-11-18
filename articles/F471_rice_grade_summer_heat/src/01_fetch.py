"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
農林水産省「米の農産物検査結果」（確定値、2006〜2024年産）と、
気象庁「過去の気象データ検索」の県庁所在地などの気象台の月平均気温（全年）を取る。
"""
import pathlib, time, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (open-data-notes)"}
B = "https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/"
# 年産 → 確定値のファイル（公表は翌年10月31日現在）
MAFF = {
    2006: "attach/pdf/index-44.pdf", 2007: "attach/pdf/index-41.pdf", 2008: "attach/pdf/index-40.pdf",
    2009: "attach/pdf/index-43.pdf", 2010: "attach/pdf/index-42.pdf", 2011: "pdf/23km2410.pdf",
    2012: "pdf/24km2510b.pdf", 2013: "pdf/25km2510.pdf", 2014: "pdf/26km2710_kakutei.pdf",
    2015: "attach/pdf/index-11.pdf", 2016: "attach/xls/index-2.xlsx", 2017: "attach/xls/index-13.xlsx",
    2018: "attach/xls/index-30.xlsx", 2019: "attach/xls/index-17.xlsx", 2020: "attach/xls/index-18.xlsx",
    2021: "attach/xls/index-15.xlsx", 2022: "attach/xls/index-46.xlsx", 2023: "attach/xls/index-57.xlsx",
    2024: "attach/xls/index-73.xlsx",
}
NATIONAL = "attach/xls/index-81.xlsx"  # 水稲うるち玄米 1等比率の推移（全国）
# 都道府県 → (prec_no, block_no, 地点名)。県庁所在地の気象台（埼玉は熊谷、滋賀は彦根）
JMA = {
    "北海道": (14, 47412, "札幌"), "青森": (31, 47575, "青森"), "岩手": (33, 47584, "盛岡"),
    "宮城": (34, 47590, "仙台"), "秋田": (32, 47582, "秋田"), "山形": (35, 47588, "山形"),
    "福島": (36, 47595, "福島"), "茨城": (40, 47629, "水戸"), "栃木": (41, 47615, "宇都宮"),
    "群馬": (42, 47624, "前橋"), "埼玉": (43, 47626, "熊谷"), "千葉": (45, 47682, "千葉"),
    "東京": (44, 47662, "東京"), "神奈川": (46, 47670, "横浜"), "山梨": (49, 47638, "甲府"),
    "長野": (48, 47610, "長野"), "静岡": (50, 47656, "静岡"), "新潟": (54, 47604, "新潟"),
    "富山": (55, 47607, "富山"), "石川": (56, 47605, "金沢"), "福井": (57, 47616, "福井"),
    "岐阜": (52, 47632, "岐阜"), "愛知": (51, 47636, "名古屋"), "三重": (53, 47651, "津"),
    "滋賀": (60, 47761, "彦根"), "京都": (61, 47759, "京都"), "大阪": (62, 47772, "大阪"),
    "兵庫": (63, 47770, "神戸"), "奈良": (64, 47780, "奈良"), "和歌山": (65, 47777, "和歌山"),
    "鳥取": (69, 47746, "鳥取"), "島根": (68, 47741, "松江"), "岡山": (66, 47768, "岡山"),
    "広島": (67, 47765, "広島"), "山口": (81, 47784, "山口"), "徳島": (71, 47895, "徳島"),
    "香川": (72, 47891, "高松"), "愛媛": (73, 47887, "松山"), "高知": (74, 47893, "高知"),
    "福岡": (82, 47807, "福岡"), "佐賀": (85, 47813, "佐賀"), "長崎": (84, 47817, "長崎"),
    "熊本": (86, 47819, "熊本"), "大分": (83, 47815, "大分"), "宮崎": (87, 47830, "宮崎"),
    "鹿児島": (88, 47827, "鹿児島"), "沖縄": (91, 47936, "那覇"),
}
JMA_URL = "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no={p}&block_no={b}&year=2024&month=&day=&view="


def get(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        path.write_bytes(r.read())
    time.sleep(1.0)


def main():
    (RAW / "maff").mkdir(parents=True, exist_ok=True)
    (RAW / "jma").mkdir(parents=True, exist_ok=True)
    for y, f in MAFF.items():
        ext = f.rsplit(".", 1)[1]
        get(B + f, RAW / "maff" / f"kensa_{y}.{ext}")
    get(B + NATIONAL, RAW / "maff" / "ittou_suii_national.xlsx")
    for pref, (p, b, name) in JMA.items():
        get(JMA_URL.format(p=p, b=b), RAW / "jma" / f"{b}.html")
    # PDF は本文の文字を pdftotext（poppler）で取り出し、data/raw/pdf_text/ に置く（02 以降はこの txt を読む）
    (RAW / "pdf_text").mkdir(exist_ok=True)
    for y in range(2006, 2016):
        subprocess.run(["pdftotext", "-layout", str(RAW / "maff" / f"kensa_{y}.pdf"),
                        str(RAW / "pdf_text" / f"kensa_{y}.txt")], check=True, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
