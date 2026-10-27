"""01_取得：日本銀行「金融市場調節方針に関する公表文」を集める

日本銀行のサイトは、この記事を作った環境（クラウドのコンテナ）からは直接届かなかったため、
ブラウザで 01_取得_browser.js を実行して f53_boj_statements.json を作った（392文書、1998年1月〜2026年9月）。
手元からサイトに届く環境なら、下の requests 版でも同じものが作れる（PDF は pypdf で読む）。

この JSON には会合の出席者の氏名が含まれるため GitHub には置いていない。
02_整形 では、出席者・賛否の欄と、氏名や「総裁」「大臣」を含む文を除いてから分析している。
"""
import json
import re
import time
from io import BytesIO
from common import STATEMENTS_JSON

BASE = "https://www.boj.or.jp"


def main():
    import requests
    from bs4 import BeautifulSoup
    from pypdf import PdfReader
    top = BeautifulSoup(requests.get(BASE + "/mopo/mpmdeci/state_all/index.htm", timeout=30).content, "html.parser")
    years = sorted({a["href"] for a in top.select("a[href]") if re.search(r"state_\d{4}/index", a["href"])})
    docs = []
    for y in years:
        soup = BeautifulSoup(requests.get(BASE + y, timeout=30).content, "html.parser")
        for tr in soup.select("tr"):
            a = tr.select_one("a[href]")
            if not a:
                continue
            t = re.sub(r"\s+", " ", tr.get_text(" ")).strip()
            m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", t)
            if not m or re.search(r"（参考）|^参考", re.sub(r"^.*?日\s*", "", t)):
                continue
            date = f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}"
            h = a["href"]
            r = requests.get(BASE + h, timeout=60)
            if h.endswith(".pdf"):
                text = "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(r.content)).pages)
            else:
                s = BeautifulSoup(r.content, "html.parser")
                main_ = s.select_one("#contents, main, .main, #main") or s.body
                text = main_.get_text("\n")
            docs.append({"date": date, "title": re.sub(r"\[.*$", "", re.sub(r"^.*?日\s*", "", t)).strip(), "href": h, "text": text})
            time.sleep(0.5)
    json.dump(docs, open(STATEMENTS_JSON, "w", encoding="utf-8"), ensure_ascii=False)
    print(len(docs))


if __name__ == "__main__":
    main()
