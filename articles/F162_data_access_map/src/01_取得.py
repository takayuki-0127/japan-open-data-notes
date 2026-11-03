"""01 記事のリポジトリ（japan-open-data-notes）を決まったコミットで取り寄せ、
各記事の README のデータ・出典・再現手順の節と、取得用のコード・メモの行を data/source_lines.csv.gz にまとめる。

使い方：python src/01_取得.py [既存のクローンのパス]
  引数がなければ GitHub から blob を絞ったクローンを作る（git が必要）。
"""
import subprocess, sys, gzip, csv
from pathlib import Path
from common import ROOT, DATA, article_text

COMMIT = "8090888"   # F157 を README に足したコミット（2026-11-03）。F162 自身より前の全記事
REPO = "https://github.com/takayuki-0127/japan-open-data-notes.git"

def clone(dst: Path):
    if not dst.exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO, str(dst)], check=True)
    subprocess.run(["git", "-C", str(dst), "checkout", COMMIT, "--", "README.md"], check=True)
    names = subprocess.run(["git", "-C", str(dst), "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", COMMIT],
                           capture_output=True, text=True, check=True).stdout.split("\n")
    want = [n for n in names if n.startswith("articles/") and (n.endswith("README.md") or "/src/" in n or n.endswith(".md"))]
    for i in range(0, len(want), 200):
        subprocess.run(["git", "-C", str(dst), "checkout", COMMIT, "--", *want[i:i+200]], check=True)
    return names

def main():
    dst = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "_repo"
    names = clone(dst) if not (dst / "articles").exists() else subprocess.run(
        ["git", "-C", str(dst), "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", COMMIT],
        capture_output=True, text=True, check=True).stdout.split("\n")
    DATA.mkdir(exist_ok=True)
    # 記事フォルダの一覧と、data フォルダに置かれたファイルの拡張子（同梱の形）
    with open(DATA / "tree_data_files.csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo); w.writerow(["article", "path"])
        for n in names:
            p = n.split("/")
            if len(p) > 3 and p[0] == "articles" and p[2] == "data":
                w.writerow([p[1], "/".join(p[2:])])
    folders = sorted({n.split("/")[1] for n in names if n.startswith("articles/") and n.count("/") >= 2})
    n = 0
    with gzip.open(DATA / "source_lines.csv.gz", "wt", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo); w.writerow(["article", "file", "line_no", "text"])
        for a in folders:
            for i, (f, l) in enumerate(article_text(dst / "articles" / a)):
                w.writerow([a, f, i, l[:600]]); n += 1
    print(len(folders), "記事フォルダ", n, "行")

if __name__ == "__main__":
    main()
