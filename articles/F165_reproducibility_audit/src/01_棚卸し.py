"""全記事フォルダの静的な棚卸し（実行はしない）。
使い方: python 01_棚卸し.py <リポジトリの articles ディレクトリ> <出力CSV>
"""
import sys, os, re, ast, csv, json
from pathlib import Path

root = Path(sys.argv[1]); out = Path(sys.argv[2])
EXCLUDE = {"F162_data_access_map", "F164", "F165"}  # 作業中の記事は母集団から外す
STD = set(sys.stdlib_module_names)
# import 名 → pip のパッケージ名
ALIAS = {"sklearn": "scikit-learn", "PIL": "pillow", "cv2": "opencv-python", "bs4": "beautifulsoup4",
         "yaml": "pyyaml", "mpl_toolkits": "matplotlib", "dateutil": "python-dateutil",
         "skimage": "scikit-image", "fitz": "pymupdf", "docx": "python-docx", "Levenshtein": "python-levenshtein",
         "google": "google-cloud-bigquery", "jpholiday": "jpholiday", "pdfplumber": "pdfplumber",
         "linearmodels": "linearmodels", "lifelines": "lifelines", "sksurv": "scikit-survival",
         "geopandas": "geopandas", "shapely": "shapely", "pyproj": "pyproj", "pymc": "pymc", "arviz": "arviz",
         "duckdb": "duckdb", "dbt": "dbt-core", "mecab": "mecab-python3", "MeCab": "mecab-python3",
         "fugashi": "fugashi", "janome": "janome", "sudachipy": "sudachipy", "sentence_transformers": "sentence-transformers",
         "torch": "torch", "lightgbm": "lightgbm", "xgboost": "xgboost", "catboost": "catboost", "shap": "shap",
         "econml": "econml", "doubleml": "doubleml", "pmdarima": "pmdarima", "prophet": "prophet",
         "networkx": "networkx", "scipy": "scipy", "numpy": "numpy", "pandas": "pandas", "statsmodels": "statsmodels",
         "matplotlib": "matplotlib", "seaborn": "seaborn", "openpyxl": "openpyxl", "xlrd": "xlrd", "requests": "requests",
         "japanize_matplotlib": "japanize-matplotlib", "libpysal": "libpysal", "esda": "esda", "spreg": "spreg",
         "mgwr": "mgwr", "pulp": "pulp", "cvxpy": "cvxpy", "ruptures": "ruptures", "hdbscan": "hdbscan", "umap": "umap-learn",
         "pyarrow": "pyarrow", "tabula": "tabula-py", "camelot": "camelot-py", "rapidfuzz": "rapidfuzz",
         "sentencepiece": "sentencepiece", "transformers": "transformers", "gensim": "gensim", "wordcloud": "wordcloud",
         "tqdm": "tqdm", "joblib": "joblib", "numba": "numba", "patsy": "patsy", "pymupdf": "pymupdf"}
RAND_USE = re.compile(r"np\.random|numpy\.random|default_rng|\brandom\.|RandomForest|GradientBoost|KMeans|lightgbm|lgb\.|xgboost|xgb\.|bootstrap|permutation|pymc|sample\(|shuffle|train_test_split|KFold|TSNE|UMAP|GaussianMixture|MCMC", re.I)
SEED = re.compile(r"(seed\s*[=(]\s*\d|random_state\s*=\s*\d|default_rng\(\s*\d|RandomState\(\s*\d|SEED\s*=\s*\d|random_seed\s*=\s*\d|np\.random\.seed\(|random\.seed\()")
NET = re.compile(r"requests\.(get|post|Session)|urllib\.request|urlopen|urlretrieve|httpx|wget|curl |pd\.read_(csv|excel|html|json)\(\s*['\"]https?://|aiohttp")
ABS = re.compile(r"['\"](/mnt/|/tmp/|/home/|/sessions/|/root/|[A-Za-z]:\\\\|~/)")
XREF = re.compile(r"\.\./\.\./|\.\./(F\d+|\d{3})_|articles/(F\d+|\d{3})_")

def imports(code):
    mods = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names: mods.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods.add(n.module.split(".")[0])
    return mods

def req_names(p):
    names, pinned, total = set(), 0, 0
    if not p.exists(): return None, 0, 0
    for l in p.read_text(errors="ignore").splitlines():
        l = l.split("#")[0].strip()
        if not l: continue
        total += 1
        if "==" in l: pinned += 1
        names.add(re.split(r"[<>=!~\[; ]", l)[0].lower().replace("_", "-"))
    return names, pinned, total

rows = []
for d in sorted(root.iterdir()):
    if not d.is_dir() or any(d.name.startswith(e) for e in EXCLUDE): continue
    py = sorted(d.rglob("*.py")); nb = list(d.rglob("*.ipynb")); sql = list(d.rglob("*.sql"))
    code = {p: p.read_text(errors="ignore") for p in py}
    allcode = "\n".join(code.values())
    local = {p.stem for p in py}
    mods, parse_err = set(), 0
    for c in code.values():
        m = imports(c)
        if m is None: parse_err += 1
        else: mods |= m
    third = {m for m in mods if m not in STD and m not in local and m != "__future__"}
    rq, pinned, rtotal = req_names(d / "requirements.txt")
    missing = sorted(m for m in third if rq is not None and ALIAS.get(m, m).lower().replace("_", "-") not in rq) if rq is not None else sorted(third)
    srcdir = d / "src"
    srcfiles = sorted(p.name for p in srcdir.glob("*.py")) if srcdir.exists() else []
    numbered = sum(1 for f in srcfiles if re.match(r"^\d{2}_", f))
    datadir = d / "data"
    dsize = sum(p.stat().st_size for p in datadir.rglob("*") if p.is_file()) if datadir.exists() else 0
    dfiles = sum(1 for p in datadir.rglob("*") if p.is_file()) if datadir.exists() else 0
    big = sum(1 for p in d.rglob("*") if p.is_file() and p.stat().st_size > 10e6)
    readme = (d / "README.md").read_text(errors="ignore") if (d / "README.md").exists() else ""
    rand = bool(RAND_USE.search(allcode)); seeded = bool(SEED.search(allcode))
    rows.append(dict(
        folder=d.name, kind="看板" if d.name.startswith("F") else "通常",
        num=int(re.match(r"F?(\d+)", d.name).group(1)),
        n_py=len(py), n_ipynb=len(nb), n_sql=len(sql), src_files=len(srcfiles), numbered=numbered,
        run_all=int((srcdir / "run_all.sh").exists() or (d / "run_all.sh").exists() or (srcdir / "00_run_all.py").exists()),
        readme=int(bool(readme)), readme_repro=int(bool(re.search(r"再現|実行手順|動かし方|How to run|python src", readme))),
        req=int(rq is not None), req_total=rtotal, req_pinned=pinned,
        third_party=";".join(sorted(third)), req_missing=";".join(missing), n_req_missing=len(missing),
        uses_random=int(rand), seed_fixed=int(seeded),
        net_in_code=int(bool(NET.search(allcode))), abs_path=int(bool(ABS.search(allcode))),
        cross_ref=int(bool(XREF.search(allcode))), parse_err=parse_err,
        data_files=dfiles, data_mb=round(dsize / 1e6, 2), big_files=big))
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "folders")
