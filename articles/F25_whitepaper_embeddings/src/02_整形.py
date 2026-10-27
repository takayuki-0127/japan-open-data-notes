"""02 整形：取得したページ（data/raw/pages.json）から本文だけを取り出し、約500字の塊（チャンク）に分ける。

- 目次・付注・参考文献・図表のページは除く
- 同じ年のページの2割以上に出てくる行（サイトのメニューなど）は除く
- 図表の題（「第1-1-9図」など）と短い行（15字未満）は除く
- 文（「。」まで）をつなげて、目安の長さを超えたところで区切る

出力：data/chunks_<長さ>.parquet（本文つき。GitHub には上げない）と data/chunks_meta.csv（本文なし）
"""
import json, re, sys
from collections import Counter
import pandas as pd
from common import RAW, DATA

SKIP_TITLE = re.compile(r"目次|付注|参考文献|用語|索引|図表|長期経済統計|付録|付図|付表|公表に当たって|ウェブアクセシビリティ|電子書籍|PDF|サイトマップ|正誤")
FIG_LINE = re.compile(r"^\s*(第\s*[\d０-９]+[\-－‐ー][\d０-９\-－‐ー]+\s*[図表]|[図表]\s*[\d０-９]+[\-－‐ー]|（備考）|（出所）|資料出所|\(備考\)|\[戻る\]|\[次へ\]|このページの先頭へ|CSV形式)")


def first_heading(h):
    for tag in ("H2:", "H3:", "H1:"):
        for x in h:
            if x.startswith(tag):
                return x[3:].strip()
    return ""


def page_title(h):
    for x in h:
        if x.startswith("H1:"):
            return x[3:].strip()
    return h[0][3:].strip() if h else ""


def chunk_text(lines, target):
    sents = []
    for ln in lines:
        for s in re.split(r"(?<=。)", ln):
            s = s.strip()
            if s:
                sents.append(s)
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > target:
            out.append(cur)
            cur = ""
        cur += s
    if cur:
        if out and len(cur) < target * 0.3:
            out[-1] += cur
        else:
            out.append(cur)
    return out


def main(target=500):
    pages = json.load(open(RAW / "pages.json", encoding="utf-8"))
    df = pd.DataFrame(pages)
    df = df.drop_duplicates("url")
    df = df[(df.year >= 1985) & (df.year <= 2025)]  # 2桁の年の読み違い（1947〜49年度）を除く
    df["ptitle"] = df.h.apply(page_title)
    df["heading"] = df.h.apply(first_heading)
    df = df[~df.ptitle.str.contains(SKIP_TITLE) & ~df.heading.str.contains(SKIP_TITLE)]
    df = df[~df.url.str.contains(r"(?:000i\d|index|/\d\d|wp-je\d\d)\.html?$")]  # 各年度の目次ページ
    rows = []
    for y, g in df.groupby("year"):
        cnt = Counter()
        for t in g.text:
            cnt.update(set(l.strip() for l in t.split("\n")))
        common = {l for l, c in cnt.items() if c >= max(3, 0.2 * len(g))}
        for _, p in g.iterrows():
            lines = [l.strip() for l in p.text.split("\n")]
            lines = [l for l in lines if l and l not in common and len(l) >= 15 and not FIG_LINE.match(l)]
            for i, c in enumerate(chunk_text(lines, target)):
                rows.append(dict(year=int(y), url=p.url, page_title=p.ptitle, heading=p.heading, i=i, n_chars=len(c), text=c))
    ch = pd.DataFrame(rows)
    ch = ch[ch.n_chars >= 80].reset_index(drop=True)
    ch.to_parquet(DATA / f"chunks_{target}.parquet")
    if target == 500:
        ch.drop(columns="text").to_csv(DATA / "chunks_meta.csv", index=False)
        by = ch.groupby("year").agg(pages=("url", "nunique"), chunks=("text", "size"), chars=("n_chars", "sum"))
        by.to_csv(DATA / "year_counts.csv")
        print(by.to_string())
    print(target, len(ch), "chunks")


if __name__ == "__main__":
    for t in ([int(a) for a in sys.argv[1:]] or [500]):
        main(t)
