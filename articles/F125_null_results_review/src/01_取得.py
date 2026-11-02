"""F01〜F120 の README を集める。
japan-open-data-notes を sparse clone して articles/F*/README.md だけ取り出し、
data/raw/readmes/ に保存する（git が使えない場合は raw.githubusercontent.com から1本ずつ取る）。"""
import pathlib, re, shutil, subprocess, sys, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "readmes"; OUT.mkdir(parents=True, exist_ok=True)
REPO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_repo"
if not REPO.exists():
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                    "https://github.com/takayuki-0127/japan-open-data-notes", str(REPO)], check=True)
    subprocess.run(["git", "-C", str(REPO), "sparse-checkout", "set", "--no-cone", "/articles/*/README.md"], check=True)
n = 0
for d in sorted((REPO / "articles").glob("F*")):
    m = re.match(r"F(\d+)_", d.name)
    if not m or not (1 <= int(m.group(1)) <= 120):
        continue
    shutil.copy(d / "README.md", OUT / f"F{int(m.group(1)):02d}.md"); n += 1
print("copied", n)
