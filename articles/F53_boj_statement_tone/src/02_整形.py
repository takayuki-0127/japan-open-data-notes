"""02_整形：公表文を会合ごとにまとめ、文に分け、「景気の判断の文」を取り出す

- 「（参考）開催時間・出席委員…」より後ろは使わない（氏名を含むため）
- 委員の氏名や賛否の内訳を含む文（「審議委員」「反対：」など）も使わない
- 長い別冊（総括的な検証・多角的レビューなど 1万字超）は除く
出力：data/statements_index.csv（会合の一覧）、data/sentences.csv（文ごと、分類つき）
"""
import json
import re
import pandas as pd
from common import DATA, STATEMENTS_JSON, ECON, PRICE, OPS

NAMEY = re.compile(r"賛成：|反対：|総裁|大臣|(?<!政策)委員(?!会)")
CUT = re.compile(r"(（参考）|\(参考\)|・開催時間|参考開催時間|開催時間[0-9０-９])")


def clean(text):
    t = re.sub(r"\s+", "", text)                 # 日本語なので空白・改行をすべて消す
    t = t.replace("PDF版ダウンロード", "")
    t = re.sub(r"\[PDF[0-9,]+KB\]", "", t)
    m = CUT.search(t)
    if m:
        t = t[:m.start()]
    return t


def split_sent(t):
    s = re.split(r"(?<=。)", t)
    return [x for x in s if len(x) >= 8]


def kind(s):
    if any(w in s for w in OPS):
        return "ops"
    has_econ = any(w in s for w in ECON)
    has_price = any(w in s for w in PRICE)
    if has_price and not has_econ:
        return "price"
    if has_econ:
        return "econ" if not has_price else "both"
    return "other"


LEAD = re.compile(r"^(?:[（(]?[0-9０-９]+[．.）)]|[①-⑳])?(?:また、|すなわち、|この間、|一方、|こうした(?:中|もと|なか)で?、|もっとも、|ただし、|この結果、)?")
SUBJ = re.compile(r"^(?:わが国の景気|わが国経済|景気|海外経済|輸出|生産|輸出や生産|輸出・生産|鉱工業生産|設備投資|個人消費|住宅投資|公共投資|雇用・所得環境|雇用・所得情勢|雇用者所得|企業収益|企業の業況感|業況感|企業マインド|国内民間需要|内需|外需)(?:は|も)")
PSUBJ = re.compile(r"^(?:物価面では、)?(?:消費者物価|国内企業物価|物価|予想物価上昇率|中長期的な予想物価上昇率)")


def kind2(s):
    """現状判断の文（主語が景気や需要項目）・先行きの文・物価の文・それ以外"""
    b = LEAD.sub("", s)
    if b.startswith("先行き"):
        return "outlook"
    if SUBJ.match(b):
        return "current"
    if PSUBJ.match(b):
        return "price"
    return "other"


def main():
    docs = json.load(open(STATEMENTS_JSON, encoding="utf-8"))
    rows, idx = [], []
    for d in docs:
        t = clean(d["text"])
        long_doc = len(t) > 10000
        idx.append({"date": d["date"], "title": d["title"], "url": "https://www.boj.or.jp" + d["href"],
                    "chars": len(t), "used": not long_doc})
        if long_doc:
            continue
        for i, s in enumerate(split_sent(t)):
            if NAMEY.search(s):
                continue
            rows.append({"date": d["date"], "doc": d["href"].split("/")[-1], "i": i, "kind": kind(s), "kind2": kind2(s), "sentence": s})
    idx = pd.DataFrame(idx)
    idx.to_csv(DATA / "statements_index.csv", index=False)
    sen = pd.DataFrame(rows)
    # 景気の文に出てくる「わが国の景気は」で始まる総括の文に印をつける
    sen["headline"] = sen.sentence.str.contains(r"^(?:[0-9０-９]+．)?(?:わが国の)?景気(?:は|の現状)") & sen.kind.isin(["econ", "both"])
    sen.to_csv(DATA / "sentences.csv", index=False)
    m = sen.groupby("date").agg(n=("sentence", "size"), econ=("kind", lambda k: (k.isin(["econ", "both"])).sum()))
    print("documents", len(idx), "used", idx.used.sum(), "meetings", idx.date.nunique())
    print("sentences", len(sen), sen.kind.value_counts().to_dict())
    y = m.reset_index()
    y["year"] = y.date.str[:4]
    print(y.groupby("year").agg(meet=("date", "size"), econ_mean=("econ", "mean"), with_econ=("econ", lambda e: (e > 0).sum())).to_string())


if __name__ == "__main__":
    main()
