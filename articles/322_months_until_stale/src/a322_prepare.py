"""322 書いた記事は、何か月で「古い数字」になるのか（④ 振り返り R102）— その1：材料をそろえる

使い方: python a322_prepare.py <定点観測の候補一覧.md> <git log の出力> <並べ替え前の予定表.md> <並べ替え後の予定表.md> <公開ログ.md>
  手元の計画メモ・予定表・リポジトリの履歴から、記事ごとに次の4つを data/ に書き出す（題名や本文は持ち出さない）
  - candidates.csv      記事の番号、主な統計、公表の頻度、次の公表の目安（候補一覧の表。目安の多くは例年の時期からの見込み）
  - first_commit.csv    記事フォルダが GitHub に最初に入った日
  - schedule.csv        予定表での公開予定日（2026-11-12 の並べ替えの前と後）、公開済みならその日
git log は `git log --name-status --format='C|%H|%ad|%s' --date=iso-strict` の出力
"""
import re, sys, os, csv, datetime
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
cand, gitlog, before, after, publog = sys.argv[1:6]
norm = lambda s: s if s[0] in "FT" else str(int(s))

c = open(cand, encoding="utf-8").read(); rows = []
for l in c[c.index("## 全候補の一覧"):].split("\n"):
    if l.startswith("| ") and not l.startswith("| #") and not l.startswith("|---"):
        x = [s.strip() for s in l.strip().strip("|").split("|")]
        if len(x) >= 7: rows.append([norm(x[0]), x[2], x[3], x[4], x[5]])
pd.DataFrame(rows, columns=["id", "stat", "freq", "next", "latest_year"]).to_csv(os.path.join(OUT, "candidates.csv"), index=False)

first = {}
for l in open(gitlog, encoding="utf-8"):
    l = l.rstrip("\n")
    if l.startswith("C|"): cur = l.split("|")[2][:10]
    elif "\t" in l:
        m = re.match(r"articles/((?:F|T)?\d+)_[^/]*/", l.split("\t")[-1])
        if m: first[norm(m.group(1))] = cur          # 履歴は新しい順なので、最後に残るのが最初の日
pd.DataFrame(sorted(first.items()), columns=["id", "first_commit"]).to_csv(os.path.join(OUT, "first_commit.csv"), index=False)

def sched(path):
    out = {}
    for l in open(path, encoding="utf-8"):
        m = re.match(r"\| (\d+)/(\d+)([朝夜]) \| (.*?) \| ((?:F|T)?\d+)_[^|]*\.md \|", l)
        if m:
            mo, da = int(m.group(1)), int(m.group(2)); y = 2026 if mo >= 10 else 2027
            out[norm(m.group(5))] = (datetime.date(y, mo, da).isoformat(), m.group(4).strip())
    return out
B, A = sched(before), sched(after)
log = open(publog, encoding="utf-8").read()
pub = {}
for l in log.split("\n"):
    m = re.match(r"- (\d{4}-\d{2}-\d{2}) [^｜]*｜(.*?)｜", l)
    if m: pub[m.group(2).strip()] = m.group(1)
rows = []
for k in sorted(set(B) | set(A)):
    t = (B.get(k) or A.get(k))[1]
    rows.append([k, pub.get(t, ""), B.get(k, ("",))[0], A.get(k, ("",))[0]])
pd.DataFrame(rows, columns=["id", "published", "plan_before", "plan_after"]).to_csv(os.path.join(OUT, "schedule.csv"), index=False)
print(len(first), len(rows), sum(1 for r in rows if r[1]))
