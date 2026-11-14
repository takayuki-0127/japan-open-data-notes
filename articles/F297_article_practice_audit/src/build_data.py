"""リポジトリの全記事の README と CORRECTIONS.md・UNVERIFIED.md から、記事ごとの決まりの守り方を表にする。
リポジトリの中（articles/F297_.../src）で動かす。出力は data/ の3つの CSV（このフォルダだけで分析を再現できるように置いておく）。
使い方: python build_data.py
"""
import os, re, csv
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
ART = REPO / "articles"
rows = []
for d in sorted(os.listdir(ART)):
    m = re.match(r"(F?)(\d+)_", d)
    p = ART / d / "README.md"
    if not m or not p.exists() or d.startswith(("F296_", "F297_")):
        continue
    s = p.read_text(encoding="utf-8")
    heads = re.findall(r"^#+\s*(.+)$", s, re.M)
    src = sum(1 for _, _, fs in os.walk(ART / d / "src") for f in fs if f.endswith((".py", ".sql", ".R")))
    figs = len(os.listdir(ART / d / "figures")) if (ART / d / "figures").is_dir() else 0
    rows.append({
        "folder": d, "kind": "看板" if m.group(1) else "一覧", "no": int(m.group(2)),
        "readme_chars": len(s),
        "has_cannot": int(any("言えない" in h for h in heads)),
        "has_robust": int(any("頑健" in h for h in heads)),
        "has_checked": int(any("確かめたこと" in h or "再現" in h for h in heads)),
        "has_plan": int(bool(re.search(r"事前の計画|結果を見る前|先に決め", s))),
        "fictional": int("架空" in s), "simulation": int("シミュレーション" in s),
        "guess_count": s.count("推測"), "n_figures": figs, "n_code_files": src,
        "has_sql": int(bool(re.search(r"\bSQL\b|DuckDB", s))),
    })
with open(HERE / "data" / "articles.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def table_rows(md, header):
    sec = md.split(header, 1)[1].split("\n## ", 1)[0]
    out = []
    for line in sec.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 3 and re.fullmatch(r"F?\d+", c[0]):
            out.append(c)
    return out


cor = (REPO / "CORRECTIONS.md").read_text(encoding="utf-8")
with open(HERE / "data" / "design_changes.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["no", "what_changed"])
    for c in table_rows(cor, "## 3."):
        w.writerow([c[0], c[2]])
unv = (REPO / "UNVERIFIED.md").read_text(encoding="utf-8")
with open(HERE / "data" / "unverified.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["no", "kind"])
    for hdr, kind in (("## 1.", "T-SQL"), ("## 2.", "Excel")):
        for c in table_rows(unv, hdr):
            w.writerow([c[0], kind])
print(len(rows), "articles")
