"""README から「言えないこと」の項目と「レビューで直したこと」の項目を取り出す。
使い方: python a242_01_extract.py <japan-open-data-notes を clone したフォルダ>
（2026-11-12 時点のコミット 996936a の README 501本で作成）
"""
import sys, csv, os
from common import readmes, group_of, section, items

repo = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__)); data = os.path.join(here, "..", "data")
idx, lim, rev = [], [], []
for folder, text in readmes(repo):
    ls = section(text, r"言えないこと")
    rs = section(text, r"^レビューで直したこと")
    li = [x for b in ls for x in items(b)]
    ri = [x for b in rs for x in items(b)]
    idx.append([folder, group_of(folder), len(text), int(bool(ls)), len(li), int(bool(rs)), len(ri)])
    lim += [[folder, group_of(folder), x[:400]] for x in li]
    rev += [[folder, group_of(folder), x[:400]] for x in ri]
for name, head, rows in [("readme_index.csv", ["folder", "group", "n_chars", "has_limits", "n_limits", "has_review", "n_review"], idx),
                         ("limits_items.csv", ["folder", "group", "item"], lim),
                         ("review_items.csv", ["folder", "group", "item"], rev)]:
    with open(os.path.join(data, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
print(len(idx), "READMEs,", len(lim), "limit items,", len(rev), "review items")
