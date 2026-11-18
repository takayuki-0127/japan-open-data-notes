"""元データを国税庁のサイトから取る（run_all.sh では呼ばない）。
会社標本調査の各年度分の「第2表 資本金、営業収入、申告所得」（Excel）と、
令和6年度分・平成25年度分の「調査結果の概要」（PDF、累年の欠損法人割合の照合用）。
PDF の表は pdftotext（poppler-utils）で文字にして data/official_ratio_pdf.txt に置く（ここまでがネットと外部ツールを使う部分）。"""
import hashlib, pathlib, urllib.request, datetime, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
B = "https://www.nta.go.jp/publication/statistics/kokuzeicho/"
T2 = {2007: "kaishahyohon2007/06.xls", 2008: "kaishahyohon2008/xls/04.xls", 2009: "kaishahyohon2009/xls/04.xls"}
for y in range(2010, 2016):
    T2[y] = f"kaishahyohon{y}/xls/02.xls"
for y in range(2016, 2022):
    T2[y] = f"kaishahyohon{y}/xls/02.xlsx"
T2[2022] = "kaishahyohon2022/xls/R04_02.xlsx"
T2[2023] = "kaishahyohon2023/xls/R05_02.xlsx"
T2[2024] = "kaishahyohon2024/xls/R06_02.xlsx"
PDF = {"kekka_fy2024.pdf": "kaishahyohon2024/pdf/kekka.pdf",
       "kekka_fy2013.pdf": "kaishahyohon2013/pdf/kekka.pdf",
       "gaiyou_fy2024.pdf": "kaishahyohon2024/pdf/gaiyou.pdf"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=120).read()

rows = []
for y, path in sorted(T2.items()):
    ext = path.rsplit(".", 1)[1]
    name = f"t2_fy{y}.{ext}"
    b = get(B + path)
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | 会社標本調査 {y}年度分 第2表 資本金、営業収入、申告所得（業種別・資本金階級別、利益計上法人・欠損法人） | {B + path} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
for name, path in PDF.items():
    b = get(B + path)
    (RAW / name).write_bytes(b)
    lab = {"kekka_fy2024.pdf": "令和6年度分 調査結果の概要（第6表 利益計上法人数・欠損法人数の推移 2014〜2024年度分）",
           "kekka_fy2013.pdf": "平成25年度分 調査結果の概要（第6表 同 2003年分〜2013年度分）",
           "gaiyou_fy2024.pdf": "令和6年度分 会社標本調査について（用語の説明：欠損法人の定義など）"}[name]
    rows.append(f"| {name} | 会社標本調査 {lab}（PDF） | {B + path} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
# PDF の累年表を文字にする（照合用。02 以降はこのテキストを読むだけ）
for nm in ["kekka_fy2024", "kekka_fy2013"]:
    txt = subprocess.run(["pdftotext", "-layout", str(RAW / f"{nm}.pdf"), "-"], capture_output=True, text=True).stdout
    (ROOT / "data" / f"{nm}.txt").write_text(txt, encoding="utf-8")
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(
    "# 元データ（取得日 " + today + "）\n\n"
    "国税庁「会社標本調査（税務統計から見た法人企業の実態）」。各年度分の統計表（Excel）と、令和6年度分の調査結果の概要（PDF）。\n\n"
    "| ファイル | 中身 | URL | sha256（先頭12桁） |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- 調査の一覧：https://www.nta.go.jp/publication/statistics/kokuzeicho/kaishahyohon/toukei.htm\n"
    "- `data/kekka_fy2024.txt`・`data/kekka_fy2013.txt` は同名の PDF を `pdftotext -layout` で文字にしたもの（01_fetch.py が作る。照合用）。\n", encoding="utf-8")
