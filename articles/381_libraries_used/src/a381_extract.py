"""381 どのライブラリを、何本の記事で使ったか（④ 振り返り R111）— import 文と requirements.txt を拾う

使い方: python a381_extract.py <japan-open-data-notes のルート>
  articles/*/ の .py を ast で読み、import している一番上のモジュール名を記事ごとに集める。
  種類は 標準（Python に付属）／自作（同じ記事フォルダか、ほかの記事フォルダに同じ名前の .py がある）／外部（それ以外）。
  requirements.txt は1行ずつ、名前と版の書き方（==・>=・なし など）に分ける。コードの中身は出さない。
"""
import ast, csv, glob, os, re, sys
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
STD = set(sys.stdlib_module_names)
def main(repo):
    os.makedirs(OUT, exist_ok=True)
    imp, req, art = [], [], []
    ALL = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(repo, "articles", "*", "**", "*.py"), recursive=True)}  # ほかの記事の .py を読み込む場合も自作に数える
    for d in sorted(glob.glob(os.path.join(repo, "articles", "*"))):
        folder = os.path.basename(d); g = group_of(folder)
        if g is None or not os.path.isdir(d): continue
        pys = sorted(glob.glob(os.path.join(d, "**", "*.py"), recursive=True))
        stems = {os.path.splitext(os.path.basename(p))[0] for p in pys}
        mods, bad = {}, 0
        for p in pys:
            try: tree = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError: bad += 1; continue
            seen = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Import): seen |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0: seen.add(n.module.split(".")[0])
            for m in seen: mods[m] = mods.get(m, 0) + 1
        for m, k in sorted(mods.items()):
            kind = "自作" if m in stems else ("標準" if m in STD else ("自作" if m in ALL else "外部"))
            imp.append(dict(folder=folder, group=g, module=m, kind=kind, n_files=k))
        rp = os.path.join(d, "requirements.txt"); lines = []
        if os.path.exists(rp):
            for l in open(rp, encoding="utf-8", errors="replace"):
                l = l.split("#")[0].strip()
                if not l: continue
                m = re.match(r"([A-Za-z0-9_.\-]+)\s*(\[[^\]]*\])?\s*(==|>=|~=|<=|!=|<|>)?\s*([0-9][^,;\s]*)?", l)
                lines.append(dict(folder=folder, group=g, name=m.group(1).lower().replace("_", "-"), op=m.group(3) or "なし", version=m.group(4) or ""))
        req += lines
        art.append(dict(folder=folder, group=g, n_py=len(pys), n_unparsed=bad, has_requirements=int(os.path.exists(rp)), n_req=len(lines)))
    for name, rows in [("imports.csv", imp), ("requirements.csv", req), ("articles.csv", art)]:
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(art), "記事", len(imp), "import", len(req), "requirements の行")
if __name__ == "__main__":
    main(sys.argv[1])
