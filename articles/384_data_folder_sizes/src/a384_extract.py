"""384 置いたデータは、どれくらいの大きさだったか（④ 振り返り R114）— ファイルの一覧を表にする

使い方: python a384_extract.py <GitHub のツリーの一覧 tree.csv> [<記事フォルダの手元の写しのルート>]
  tree.csv は GitHub の API（git/trees/<コミット>?recursive=1）から path・size（バイト）・sha（中身のハッシュの先頭12桁）だけを取り出したもの。
  articles/<記事>/<場所>/... に分け、拡張子を付けて data/files.csv.gz に出す。
  2つめの引数があれば、data フォルダの CSV のうち、手元に同じ大きさの写しがあるものの行数と列数を数えて data/csv_rows.csv に出す（中身は出さない）。
"""
import csv, gzip, os, re, sys
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
def main(tree, local=None):
    os.makedirs(OUT, exist_ok=True); rows = []
    for r in csv.DictReader(open(tree, encoding="utf-8")):
        parts = r["path"].split("/")
        if len(parts) < 3 or parts[0] != "articles" or group_of(parts[1]) is None: continue
        name = parts[-1]; ext = name.rsplit(".", 1)[-1].lower() if "." in name else "(なし)"
        if name.lower().endswith(".csv.gz"): ext = "csv.gz"
        rows.append(dict(folder=parts[1], group=group_of(parts[1]), place=parts[2] if len(parts) > 3 else "(直下)", depth=len(parts) - 2, ext=ext, size=int(r["size"]), sha=r.get("sha", ""), path="/".join(parts[2:])))
    with gzip.open(os.path.join(OUT, "files.csv.gz"), "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "ファイル", len({r["folder"] for r in rows}), "記事")
    if local:
        out = []
        for r in rows:
            if r["place"] != "data" or r["ext"] != "csv": continue
            p = os.path.join(local, r["folder"], r["path"])
            if not os.path.exists(p) or os.path.getsize(p) != r["size"]: continue
            n = 0; cols = 0
            with open(p, "rb") as f:
                for i, line in enumerate(f):
                    if i == 0: cols = line.count(b",") + 1
                    n += 1
            out.append(dict(folder=r["folder"], group=r["group"], path=r["path"], size=r["size"], lines=n, cols_first_line=cols))
        with open(os.path.join(OUT, "csv_rows.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
        print(len(out), "CSV の行数を数えた")
if __name__ == "__main__":
    main(*sys.argv[1:3])
