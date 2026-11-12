"""323 公開したあとの手直しは、どれくらいあったか（④ 振り返り R103）— その1：履歴を表にする

使い方: python a323_prepare.py <git log の出力>
  git log --name-status --format='C|%H|%ad|%s' --date=iso-strict の出力を、
  「コミット × 記事フォルダ」が1行の表（data/commit_folder.csv）にする。
  列：コミット（先頭7桁）、日時、メッセージが既定の「Add files via upload」か、フォルダ、
      そのコミットがフォルダの中で触ったファイルの数（README・PLAN・src・results・data・figures・その他）、追加・変更・削除・名前の変更の数、
      変更（書き換え）したファイルの数を種類ごとに（mod_README など）
"""
import re, sys, os, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
KINDS = ["README", "PLAN", "src", "results", "data", "figures", "other"]
def kind(rel):
    if rel == "README.md": return "README"
    if rel == "PLAN.md": return "PLAN"
    top = rel.split("/")[0]
    return top if top in ("src", "results", "data", "figures") else "other"
rows = []; cur = None; root = []
def flush():
    if cur is None: return
    for folder, c in cur["f"].items():
        rows.append([cur["h"], cur["d"], cur["default"], folder] + [c[k] for k in KINDS] + [c["A"], c["M"], c["D"], c["R"]] + [c["M_" + k] for k in KINDS])
    root.append([cur["h"], cur["d"], cur["default"], cur["root_readme"], len(cur["f"]), cur["other_root"]])
for l in open(sys.argv[1], encoding="utf-8"):
    l = l.rstrip("\n")
    if l.startswith("C|"):
        flush(); _, h, d, s = l.split("|", 3)
        cur = dict(h=h[:7], d=d, default=int(s.strip() == "Add files via upload"), f=collections.defaultdict(collections.Counter), root_readme=0, other_root=0)
    elif "\t" in l:
        p = l.split("\t"); st = p[0][0]; path = p[-1]
        m = re.match(r"articles/([^/]+)/(.+)", path)
        if m:
            c = cur["f"][m.group(1)]; c[kind(m.group(2))] += 1; c[st] += 1
            if st == "M": c["M_" + kind(m.group(2))] += 1
        elif path == "README.md": cur["root_readme"] += 1
        else: cur["other_root"] += 1
flush()
with open(os.path.join(OUT, "commit_folder.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["commit", "datetime", "default_message", "folder"] + KINDS + ["added", "modified", "deleted", "renamed"] + ["mod_" + k for k in KINDS]); w.writerows(rows)
with open(os.path.join(OUT, "commits.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["commit", "datetime", "default_message", "root_readme", "folders_touched", "other_root_files"]); w.writerows(root)
print(len(root), "commits;", len(rows), "commit×folder rows")
