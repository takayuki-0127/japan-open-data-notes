"""00 PDF→語の座標：saidai_02.pdf の「死者数（地震動：…）」表のページ 96 枚について、語と座標を CSV にする。
テキスト化（pdftotext -layout）だけでは列の順が崩れる行があるため、数値の右端 x 座標で列を決める。
PDF 本体は data/raw に置かないので、この段だけは PDF が要る（引数2：PDFの場所）。出力 data/raw/f292_s2_words.csv はリポジトリに含める。
"""
import sys, pathlib, csv
import pdfplumber
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
pdf_path = sys.argv[2]
pages = (out / "data/raw/f292_saidai_02.txt").read_text().split("\f")
idx = [i for i, p in enumerate(pages) if "死者数（地震動" in p]
assert len(idx) == 96 and all(pages[i].count("死者数（地震動") == 1 for i in idx)
with pdfplumber.open(pdf_path) as pdf, open(out / "data/raw/f292_s2_words.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["page", "x0", "x1", "top", "text"])
    for i in idx:
        for t in pdf.pages[i].extract_words():
            w.writerow([i, round(t["x0"], 1), round(t["x1"], 1), round(t["top"], 1), t["text"]])
print("pages", len(idx))
