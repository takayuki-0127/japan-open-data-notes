"""10通りのやり方で4つの表を PDF から読み、data/extracted/<やり方>.json に「行＝セルの文字列のリスト」で保存する。
文字の層を読むもの（pdfplumber・camelot・tabula・PyMuPDF）と、画像にしてから文字認識するもの（Tesseract、スキャンした PDF の代わり）。"""
import sys, time, io, subprocess, tempfile, os
import pdfplumber, camelot, tabula, pymupdf
from PIL import Image
from common import *

def t_plumber_text(pdf, p):
    with pdfplumber.open(pdf) as d:
        return [[l] for l in (d.pages[p].extract_text() or "").split("\n")]
def t_plumber_lines(pdf, p):
    with pdfplumber.open(pdf) as d:
        return [r for t in d.pages[p].extract_tables() for r in t]
def t_plumber_textstrat(pdf, p):
    with pdfplumber.open(pdf) as d:
        return [r for t in d.pages[p].extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"}) for r in t]
def t_camelot(flavor):
    def f(pdf, p):
        try:
            ts = camelot.read_pdf(str(pdf), pages=str(p + 1), flavor=flavor)
        except Exception as e:
            print("  camelot", flavor, "error", type(e).__name__, str(e)[:80]); return []
        return [list(r) for t in ts for r in t.df.values.tolist()]
    return f
def t_tabula(lattice):
    def f(pdf, p):
        try:
            ts = tabula.read_pdf(str(pdf), pages=p + 1, lattice=lattice, stream=not lattice, multiple_tables=True, pandas_options={"header": None}, silent=True)
        except Exception as e:
            print("  tabula error", type(e).__name__, str(e)[:80]); return []
        return [["" if pd.isna(x) else str(x) for x in r] for t in ts for r in t.values.tolist()]
    return f
def t_mupdf_tables(pdf, p):
    d = pymupdf.open(pdf)
    return [["" if c is None else c for c in r] for t in d[p].find_tables().tables for r in t.extract()]
def t_mupdf_text(pdf, p):
    d = pymupdf.open(pdf)
    # 単語を y 座標で行にまとめる（pdf.js で行ごとに並べたやり方に近い）
    ws = d[p].get_text("words")
    ws.sort(key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))
    lines, cur, cy = [], [], None
    for w in sorted(ws, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        y = (w[1] + w[3]) / 2
        if cy is not None and abs(y - cy) > 2.5:
            lines.append(" ".join(x[4] for x in sorted(cur, key=lambda x: x[0]))); cur = []
        cur.append(w); cy = y if cy is None or not cur[:-1] else (cy + y) / 2
    if cur: lines.append(" ".join(x[4] for x in sorted(cur, key=lambda x: x[0])))
    return [[l] for l in lines]
# 日本語の OCR は tessdata_fast の jpn.traineddata（https://github.com/tesseract-ocr/tessdata_fast）を TESSDATA_PREFIX に置いて使う
def t_ocr(dpi, lang="eng"):
    def f(pdf, p):
        d = pymupdf.open(pdf)
        pix = d[p].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        with tempfile.TemporaryDirectory() as td:
            fn = os.path.join(td, "p.png"); pix.save(fn)
            out = subprocess.run(["tesseract", fn, "-", "-l", lang, "--psm", "6"], capture_output=True, text=True).stdout
        return [[l] for l in out.split("\n") if l.strip()]
    return f

TOOLS = {
    "pdfplumber_文字": t_plumber_text, "pdfplumber_表（罫線）": t_plumber_lines, "pdfplumber_表（文字の並び）": t_plumber_textstrat,
    "camelot_lattice": t_camelot("lattice"), "camelot_stream": t_camelot("stream"),
    "tabula_lattice": t_tabula(True), "tabula_stream": t_tabula(False),
    "PyMuPDF_表": t_mupdf_tables, "PyMuPDF_文字": t_mupdf_text,
    "OCR英語_300dpi": t_ocr(300), "OCR英語_150dpi": t_ocr(150),
    "OCR日本語_300dpi": t_ocr(300, "jpn+eng"), "OCR日本語_150dpi": t_ocr(150, "jpn+eng"),
}
if __name__ == "__main__":
    only = sys.argv[1:] or list(TOOLS)
    timing = {}
    for name in only:
        out, t0 = {}, time.time()
        for tid, T in TABLES.items():
            out[tid] = {str(p): TOOLS[name](RAW / T["pdf"], p) for p in T["pages"]}
        timing[name] = round(time.time() - t0, 1)
        json.dump(out, open(EXT / f"{name}.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(name, timing[name], "s", {t: sum(len(v) for v in out[t].values()) for t in out}, flush=True)
    tf = RES / "extract_seconds.json"
    old = json.load(open(tf)) if tf.exists() else {}
    old.update(timing); json.dump(old, open(tf, "w"), ensure_ascii=False, indent=1)
