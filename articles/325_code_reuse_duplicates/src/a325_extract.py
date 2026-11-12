"""325 同じ処理を、何回書き直していたか（④ 振り返り R105）— その1：関数を取り出す

使い方: python a325_extract.py <リポジトリのルート>
  articles/*/src/ の .py を1本ずつ読み、関数（def）ごとに次を data/functions.csv.gz に書き出す（コードそのものは書き出さない）
  - 記事フォルダ、ファイル名、関数名、行数、トークンの数
  - exact：書式・コメント・docstring を除いた中身（ast.dump）のハッシュ。同じなら「まったく同じ関数」
  - shingles：トークン4つの並びの集合を64個の MinHash にしたもの（ほぼ同じかどうかを比べるのに使う）
  あわせて data/files.csv（ファイルごとの行数・関数の数・ファイル全体のハッシュ）と、
  data/idioms.csv（フォントの設定・図の保存など、決まった処理の行。空白を除いた行そのもの）
"""
import os, sys, ast, glob, hashlib, io, tokenize, csv, re
REPO = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
K = 64; MOD = (1 << 61) - 1
import random
rnd = random.Random(325); AB = [(rnd.randrange(1, MOD), rnd.randrange(0, MOD)) for _ in range(K)]
def toks(src):
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER): continue
            out.append("S" if t.type == tokenize.STRING else t.string)       # 文字列の中身（ファイル名・題名）は同じとみなす
    except Exception: pass
    return out
def minhash(tk):
    sh = {int(hashlib.md5("\x1f".join(tk[i:i + 4]).encode()).hexdigest()[:15], 16) % MOD for i in range(max(1, len(tk) - 3))}
    return [min((a * x + b) % MOD for x in sh) for a, b in AB], len(sh)
IDIOMS = {"日本語フォントの設定": r"font\.family|font_manager|rcParams\[.font\.sans", "図の保存（savefig）": r"\.savefig\(",
          "文字コードを指定して CSV を読む": r"read_csv\(.*encoding\s*=\s*.(cp932|shift_jis|sjis|shift-jis)", "乱数の種を決める": r"default_rng\(|random\.seed\(|RandomState\(",
          "結果を JSON に書く": r"json\.dump\(", "出力フォルダを作る": r"makedirs\("}
frows, files, irows = [], [], []
for p in sorted(glob.glob(os.path.join(REPO, "articles", "*", "src", "**", "*.py"), recursive=True)):
    folder = p.split(os.sep + "articles" + os.sep)[1].split(os.sep)[0]; name = os.path.basename(p)
    src = open(p, encoding="utf-8", errors="replace").read()
    for ln in src.split("\n"):
        for nm, pat in IDIOMS.items():
            if re.search(pat, ln, re.I) and not ln.strip().startswith("#"):
                irows.append([folder, name, nm, re.sub(r"\s+", "", ln)[:160]])
    try: tree = ast.parse(src)
    except SyntaxError:
        files.append([folder, name, src.count("\n") + 1, -1, hashlib.md5(src.encode()).hexdigest()[:12]]); continue
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str): body = body[1:]
            if not body: continue
            dump = "|".join(ast.dump(b) for b in body) + "#" + ast.dump(node.args)
            seg = ast.get_source_segment(src, node) or ""
            tk = toks(seg); mh, ns = minhash(tk)
            frows.append([folder, name, node.name, node.end_lineno - node.lineno + 1, len(tk), hashlib.md5(dump.encode()).hexdigest()[:12], ns, " ".join(format(x, "x") for x in mh)]); n += 1
    files.append([folder, name, src.count("\n") + 1, n, hashlib.md5(re.sub(r"\s+", "", src).encode()).hexdigest()[:12]])
import gzip
with gzip.open(os.path.join(OUT, "functions.csv.gz"), "wt", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "file", "func", "lines", "tokens", "exact", "n_shingles", "minhash"]); w.writerows(frows)
with open(os.path.join(OUT, "files.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "file", "lines", "functions", "file_hash"]); w.writerows(files)
with open(os.path.join(OUT, "idioms.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["folder", "file", "idiom", "line"]); w.writerows(irows)
print(len(files), "files;", len(frows), "functions")
