"""383 先に決めた確かめ方のうち、実際にはできなかったものは何だったか（④ 振り返り R113）— PLAN.md と README を拾う

使い方: python a383_extract.py <japan-open-data-notes のルート>
  PLAN.md（分析の前に書いてコミットした計画）がある記事について、
    PLAN.md の「頑健性」の節の項目数、仮説（H1, H2, …）の数
    README の「計画からのずれ」「計画とのずれ」の節の項目（1項目1行）
  を data/plans.csv と data/deviation_items.csv に出す。項目の文は、あとで手で分類するために先頭120字だけ残す。
"""
import csv, glob, os, re, sys
from common import section, items, group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
def main(repo):
    plans, devs = [], []
    for p in sorted(glob.glob(os.path.join(repo, "articles", "*", "PLAN.md"))):
        d = os.path.dirname(p); folder = os.path.basename(d); aid = folder.split("_")[0]
        t = open(p, encoding="utf-8").read(); r = open(os.path.join(d, "README.md"), encoding="utf-8").read()
        rob = [i for b in section(t, r"頑健性") for i in items(b)]
        hyp = sorted(set(re.findall(r"\bH(\d)\b", t)))
        dv = [i for b in section(r, r"計画からのずれ|計画とのずれ") for i in items(b)]
        rrob = [i for b in section(r, r"^頑健性") for i in items(b)]
        plans.append(dict(id=aid, folder=folder, group=group_of(folder), plan_chars=len(t), n_hypotheses=len(hyp), n_planned_checks=len(rob), has_deviation_section=int(bool(section(r, r"計画からのずれ|計画とのずれ"))), n_deviation_items=len(dv), n_readme_robust_items=len(rrob)))
        for k, i in enumerate(dv): devs.append(dict(id=aid, k=k, chars=len(i), head=re.sub(r"\s+", " ", i)[:120]))
    os.makedirs(OUT, exist_ok=True)
    for name, rows in [("plans.csv", plans), ("deviation_items.csv", devs)]:
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(plans), "本の PLAN.md", len(devs), "項目のずれ")
if __name__ == "__main__":
    main(sys.argv[1])
