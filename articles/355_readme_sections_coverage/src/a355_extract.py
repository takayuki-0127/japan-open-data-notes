"""355 README の8つの節は、どれだけそろっているか（④ 振り返り R110）— 見出しを拾う

使い方: python a355_extract.py <japan-open-data-notes のルート>
  articles/*/README.md の見出し（# の行）だけを読み、8つの節があるかどうかを記事ごとに 0/1 で data/sections.csv に出す。
  strict_ は決めた名前そのもの、ほかは同じ役目の別の名前も数える。tbl_ は、見出しではなく表の列（| 問い | 手法 |）で書いたもの。本文は出さない。
  初期の記事で同じ README の本文を共有しているものは、最初の1本だけを数える（common.dedup）
"""
import re, sys, os, csv
from common import readmes, group_of, dedup
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
SEC = {  # 節: (決めた名前, 同じ役目の名前も含めた形)
    "question": (r"^問い", r"問い|確かめたいこと|何を調べ|この記事で(分か|確かめ)|目的"),
    "data": (r"^データ", r"データ|使った数字"),
    "method": (r"^手法", r"手法|方法|数え方|やり方|設計|モデル"),
    "result": (r"^(主な)?結果", r"結果|結論|分かったこと|判定"),
    "robust": (r"^頑健性", r"頑健性|確かめたこと|設定を変え|条件を変え|感度"),
    "repro": (r"^再現手順", r"再現|動かし方|実行|使い方"),
    "limits": (r"^言えないこと", r"言えない|注意|限界"),
    "source": (r"^出典", r"出典|ライセンス"),
}
def main(repo):
    rows = []
    for folder, t in dedup(readmes(repo)):
        heads = [re.sub(r"^[0-9０-９.．)\s]+", "", m.group(2)).strip() for m in re.finditer(r"^(#{2,})\s+(.*)$", t, re.M)]
        r = dict(folder=folder, group=group_of(folder), n_heads=len(heads), chars=len(t), wrapped=int(any("もとのリポジトリの説明" in h for h in heads)))
        for k, (st, lo) in SEC.items():
            r["strict_" + k] = int(any(re.search(st, h) for h in heads))
            r[k] = int(any(re.search(lo, h) for h in heads))
        tbl = [l for l in t.split("\n") if l.startswith("|")]
        r["tbl_question"] = int(any(re.search(r"\|\s*問い\s*\|", l) for l in tbl))
        r["tbl_method"] = int(any(re.search(r"\|\s*手法\s*\|", l) for l in tbl))
        r["extra_plan"] = int(any(re.search(r"計画|PLAN|設計書から", h) for h in heads))
        r["extra_review"] = int(any(re.search(r"レビュー", h) for h in heads))
        r["extra_files"] = int(any(re.search(r"ファイル|フォルダ|^図", h) for h in heads))
        rows.append(r)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "sections.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "README")
if __name__ == "__main__":
    main(sys.argv[1])
