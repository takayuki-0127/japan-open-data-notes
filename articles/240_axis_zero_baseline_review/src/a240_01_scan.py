"""記事のコード（src/*.py など）から、図の縦軸の決め方を数える。
使い方: python a240_01_scan.py <japan-open-data-notes を clone したフォルダ>
（2026-11-12 時点のコミット 996936a、501本の記事フォルダの .py で作成）
"""
import sys, os, re, glob, csv
from common import group_of

repo = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__)); data = os.path.join(here, "..", "data")
NUM = r"-?\d*\.?\d+"
rows, flags = [], []
for d in sorted(glob.glob(os.path.join(repo, "articles", "*"))):
    folder = os.path.basename(d)
    if group_of(folder) is None:
        continue
    files = glob.glob(os.path.join(d, "**", "*.py"), recursive=True)
    c = dict(files=0, plot_files=0, bar=0, barh=0, line=0, ylim=0, ylim_zero=0, ylim_neg=0, ylim_pos=0, ylim_var=0)
    for f in files:
        s = open(f, encoding="utf-8", errors="ignore").read()
        c["files"] += 1
        nb, nbh = len(re.findall(r"\.bar\(", s)), len(re.findall(r"\.barh\(", s))
        nl = len(re.findall(r"\.(plot|step)\(", s))
        if nb + nbh + nl == 0:
            continue
        c["plot_files"] += 1; c["bar"] += nb; c["barh"] += nbh; c["line"] += nl
        for m in re.finditer(r"(?:set_ylim|plt\.ylim)\(\s*(?:bottom\s*=\s*)?([^,)]*)", s):
            a = m.group(1).strip(); c["ylim"] += 1
            if re.fullmatch(r"0(\.0*)?", a):
                c["ylim_zero"] += 1
            elif re.fullmatch(NUM, a):
                v = float(a)
                if v < 0:
                    c["ylim_neg"] += 1
                else:
                    c["ylim_pos"] += 1
                    if nb:  # 縦の棒グラフがあるファイルで、下端が0より上の指定 → 目で確かめる候補
                        line = s[:m.start()].count("\n") + 1
                        flags.append([folder, os.path.relpath(f, d), line, a])
            else:
                c["ylim_var"] += 1
    rows.append([folder, group_of(folder)] + list(c.values()))
with open(os.path.join(data, "code_scan.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "group", "files", "plot_files", "bar", "barh", "line", "ylim", "ylim_zero", "ylim_neg", "ylim_pos", "ylim_var"]); w.writerows(rows)
with open(os.path.join(data, "bar_with_positive_ylim.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "file", "line", "lower"]); w.writerows(flags)
print(len(rows), "folders,", len(flags), "flags")
