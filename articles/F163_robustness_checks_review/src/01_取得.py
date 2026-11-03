"""看板記事 F01〜F125 の README と、F125・F122 の判定表を、コミットを固定して取る。"""
import os, re, urllib.request, pathlib
COMMIT = "8090888"  # 2026-11-03 時点の root README（F160 まで）
BASE = f"https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/{COMMIT}"
here = pathlib.Path(__file__).resolve().parent.parent
raw = here / "data" / "raw"; (raw / "readmes").mkdir(parents=True, exist_ok=True)
root = urllib.request.urlopen(f"{BASE}/README.md").read().decode()
folders = sorted(set(re.findall(r"articles/(F\d{2,3}_[A-Za-z0-9_\-]+)", root)), key=lambda x: int(re.match(r"F(\d+)", x).group(1)))
folders = [f for f in folders if int(re.match(r"F(\d+)", f).group(1)) <= 125]
for f in folders:
    p = raw / "readmes" / f"{f}.md"
    if not p.exists():
        p.write_bytes(urllib.request.urlopen(f"{BASE}/articles/{f}/README.md").read())
for src, dst in [("articles/F125_null_results_review/data/articles.csv", "f125_articles.csv"),
                 ("articles/F125_null_results_review/data/raw/article_family_F122.csv", "article_family_F122.csv")]:
    if not (raw / dst).exists():
        (raw / dst).write_bytes(urllib.request.urlopen(f"{BASE}/{src}").read())
print(len(folders), "READMEs")
