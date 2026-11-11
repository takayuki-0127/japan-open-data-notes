"""F269 01 取得：元データの記録とテキスト化。

元データ（どれも公表されているもの）
- 中小企業庁「価格交渉促進月間フォローアップ調査の結果」（結果1の PDF）
  https://www.chusho.meti.go.jp/keiei/torihiki/follow-up/dl/{回}/result_01.pdf
  回 = 202109, 202309, 202409, 202503, 202509, 202603（2026-11-11 取得。ブラウザで開いて保存）
  ※サイトの仕組みでスクリプトからの直接取得は通らないことがあるので、PDF はブラウザで保存して data/raw/pdf/ に置く。
- 日本銀行「短観」販売価格判断DI・仕入価格判断DI（実績、規模別・全産業/製造業/非製造業、2010年〜）
  日本銀行 時系列統計データ検索サイト API（db=CO）で取得 → data/raw/boj_tankan_prices.json

このスクリプトは、PDF があれば pdftotext（poppler）でテキストにして data/raw/txt/ に保存し、
PDF・テキスト・JSON の md5 を data/raw/MANIFEST.json に書く。
リポジトリには PDF は置かず、テキストだけを置く（PDF がなくても 02 以降は動く）。
"""
import hashlib, json, os, subprocess, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
ROUNDS = ["202109", "202309", "202409", "202503", "202509", "202603"]
URL = "https://www.chusho.meti.go.jp/keiei/torihiki/follow-up/dl/{}/result_01.pdf"

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

man = {"followup": {}, "tankan": {}}
for r in ROUNDS:
    pdf = os.path.join(RAW, "pdf", f"fu_{r}.pdf")
    txt = os.path.join(RAW, "txt", f"fu_{r}.txt")
    ent = {"url": URL.format(r)}
    if os.path.exists(pdf):
        subprocess.run(["pdftotext", "-layout", pdf, txt], check=True)
        ent["pdf_md5"] = md5(pdf)
        ent["pdf_bytes"] = os.path.getsize(pdf)
    if not os.path.exists(txt):
        sys.exit(f"missing {txt}: put the PDF in data/raw/pdf/")
    ent["txt_md5"] = md5(txt)
    man["followup"][r] = ent
j = os.path.join(RAW, "boj_tankan_prices.json")
man["tankan"] = {"file": "boj_tankan_prices.json", "md5": md5(j),
                 "api": "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=CO&startDate=201001&endDate=202604&code=TK99F{0,1,2}00061{4,5}GCQ0{0,1,2,3}000"}
json.dump(man, open(os.path.join(RAW, "MANIFEST.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(man, ensure_ascii=False, indent=1)[:800])
