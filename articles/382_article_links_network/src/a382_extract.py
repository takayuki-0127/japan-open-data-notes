"""382 記事どうしは、どうつながっているか（④ 振り返り R112）— README の中の、ほかの記事への言及を拾う

使い方: python a382_extract.py <japan-open-data-notes のルート>
  articles/*/README.md を読み、ほかの記事の番号が出てくる所を拾う。拾う形は4つ：
    link  articles/<フォルダ名> の形のリンクやパス
    F     F01〜F295 の形の番号（F の後ろに数字2〜3桁）
    T     T001 の形の番号
    num   「記事 141」「記事141」の形と、「141_wage_increase」のようなフォルダ名
  番号だけの数字（「232」など）は、ほかの数字と区別できないので拾わない。「F01〜F99」のような範囲の両端も拾わない。自分自身への言及は除く。
  初期の記事で同じ README の本文を共有しているものは、最初の1本だけを読む（common.dedup）。
  data/nodes.csv（記事）と data/edges.csv（言及元 → 言及先、回数）を出す。本文は出さない。
"""
import csv, os, re, sys
from common import readmes, group_of, dedup, title_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
aid = lambda folder: re.match(r"((?:F|T)?\d+)_", folder).group(1)
PAT = {"link": r"articles/((?:F|T)?\d+)_[A-Za-z0-9_]+", "F": r"(?<![A-Za-z0-9_/])(F\d{2,3})(?![\d_A-Za-z])", "T": r"(?<![A-Za-z0-9_/])(T\d{3})(?![\d_A-Za-z])",
       "num": r"記事\s?(\d{3})(?!\d)|(?<![\w/.])(\d{3})_[a-z][a-z0-9_]+"}
def main(repo):
    allr = readmes(repo); ids = {aid(f): f for f, _ in allr}; docs = dedup(allr)
    kept = {f for f, _ in docs}; nodes, edges = [], {}
    for f, t in allr:
        nodes.append(dict(id=aid(f), folder=f, group=group_of(f), read=int(f in kept), chars=len(t), title=title_of(t)[:80]))
    for f, t in docs:
        me = aid(f)
        for kind, p in PAT.items():
            for m in re.finditer(p, t):
                d = next(g for g in m.groups() if g)
                if d == me or d not in ids: continue
                if kind in ("F", "T") and (re.match(r"\s*[〜～–—\-~]\s*(F|T)?\d", t[m.end():m.end() + 6]) or re.search(r"(F|T)\d{2,3}\s*[〜～–—\-~]\s*$", t[max(0, m.start() - 8):m.start()])):
                    continue  # 「F01〜F99」のような番号の範囲は、まとまりの名前なので数えない
                e = edges.setdefault((me, d), dict(src=me, dst=d, n=0, link=0, F=0, T=0, num=0)); e["n"] += 1; e[kind] += 1
    os.makedirs(OUT, exist_ok=True)
    for name, rows in [("nodes.csv", nodes), ("edges.csv", sorted(edges.values(), key=lambda e: (e["src"], e["dst"])))]:
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(nodes), "記事（読んだ README", len(docs), "本）", len(edges), "組の言及")
if __name__ == "__main__":
    main(sys.argv[1])
