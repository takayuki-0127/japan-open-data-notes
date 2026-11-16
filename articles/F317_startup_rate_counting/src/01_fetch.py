"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。
厚生労働省「雇用保険事業年報」の PDF（平成29年度〜令和7年度）から、第1表「雇用保険産業別適用状況〔適用事業所〕」のページだけを切り出して保存する。
ページの場所は pdftotext（poppler-utils）で探し、切り出しは pypdf で行う。"""
import datetime, pathlib, subprocess, tempfile, urllib.request
from pypdf import PdfReader, PdfWriter

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (research script)"}
KEYS = ["h29", "h30", "r01", "r02", "r03", "r04", "r05", "r06", "r07"]
URL = "https://www.mhlw.go.jp/bunya/koyou/koyouhoken02/pdf/all_{}.pdf"
def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    L = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for k in KEYS:
        u = URL.format(k)
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=300) as r:
            b = r.read()
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "a.pdf"; p.write_bytes(b)
            txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True).stdout.decode("utf-8", "ignore")
            pages = txt.split("\f")
            idx = [i for i, pg in enumerate(pages) if "第1表" in pg and "雇用保険産業別適用状況" in pg and "適用事業所" in pg][0]
            w = PdfWriter(); w.add_page(PdfReader(str(p)).pages[idx])
            with open(RAW / f"koyouhoken_{k}_t1.pdf", "wb") as f:
                w.write(f)
        L.append(f"| koyouhoken_{k}_t1.pdf | 厚生労働省「雇用保険事業年報」（{k}）第1表 雇用保険産業別適用状況〔適用事業所〕（元の PDF の {idx + 1} ページ目だけを切り出した） | {u} | {today} |")
    L += ["", "- 雇用保険事業年報：https://www.mhlw.go.jp/bunya/koyou/koyouhoken02/",
          "- 元の PDF は9年度分で約50MBあり同梱の上限を超えるため、第1表のページだけを切り出して保存した（中身は変えていない）。", ""]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
