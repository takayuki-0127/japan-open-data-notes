"""照合：作り直したファイルを、2つの相手と比べる。

1. 基準（expected/manifest.json）：引き継ぎのときに run_all.py で1回作り直して固定した出力の md5。
   合否はこちらで決める。数字のファイルが1つでも違う・足りないと「NG」（終了コード 1）
2. 元のファイル（決めたコミットに入っているもの）：記事に載った数字。参考として、どれだけ近いかを書く
   - バイトが同じ → 同じ／.gz は中身を開いて同じ → 同じ（中身）
   - .csv：表として読み、数の列は「相対 1e-9」か「書いた桁の1単位」（%.1f の列なら 0.1）以内 → 同じ（丸めの差 n セル）
   - .json：同じ形で、数の最大の相対差を書く → 近い（相対 x）
   - 見た目のファイル（.png .pdf .html）：フォントやライブラリの版で変わるので数えるだけ
比べるのは「この実行で作られた（書き換えられた）ファイル」だけ（時刻が実行の開始より後のもの）。
md5 は .gz なら中身の md5（gzip は書いた時刻を頭に入れるので、同じ中身でもバイトが変わる）。
"""
import csv, gzip, hashlib, io, json, pathlib, subprocess
import numpy as np
import pandas as pd

NUM = {".csv", ".json", ".md", ".sql", ".txt", ".m", ".dax", ".tsv"}
LOOK = {".png", ".pdf", ".html", ".svg"}
MANIFEST = pathlib.Path(__file__).resolve().parents[1] / "expected" / "manifest.json"
# 毎回変わってよい欄（処理の速さを測った秒など）。md5 はこの欄を除いた中身で取る（docs/troubleshooting.md の T8）
VOLATILE_JSON = {"main.json": ["/速さ/"]}   # F249 の results/main.json


def content_md5(b, name, key=""):
    if name in VOLATILE_JSON and key.startswith("F249_"):
        try:
            d = dict(_flat(json.loads(b)))
            d = {k: v for k, v in d.items() if not any(k.startswith(p) for p in VOLATILE_JSON[name])}
            b = json.dumps(d, ensure_ascii=False, sort_keys=True).encode()
        except Exception:
            pass
    if name.endswith(".gz"):
        try:
            b = gzip.decompress(b)
        except OSError:
            pass
    return hashlib.md5(b).hexdigest()


def _head_blob(repo, rel):
    p = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=repo, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def _decimals(col):
    t = col.dropna().astype(str)
    t = t[t.str.contains(r"\.", regex=True) & ~t.str.contains("e", case=False)]
    return int(t.str.split(".").str[1].str.len().max()) if len(t) else 0


def _close_csv(a, b, rtol=1e-9):
    """数の列は「相対 1e-9」か「書いた桁の1単位（四捨五入の境目）」の大きい方まで許す。(同じか, 1単位ずれたセル数)"""
    try:
        x = pd.read_csv(io.BytesIO(a), encoding="utf-8-sig", low_memory=False, dtype=str)
        y = pd.read_csv(io.BytesIO(b), encoding="utf-8-sig", low_memory=False, dtype=str)
    except Exception:
        return False, 0
    if x.shape != y.shape or list(x.columns) != list(y.columns):
        return False, 0
    nflip = 0
    for c in x.columns:
        u, v = x[c], y[c]
        if u.fillna("").equals(v.fillna("")):
            continue
        un, vn = pd.to_numeric(u, errors="coerce"), pd.to_numeric(v, errors="coerce")
        if un.isna().ne(u.isna()).any() or vn.isna().ne(v.isna()).any():
            return False, 0
        unit = 10.0 ** -max(_decimals(u), _decimals(v))
        d = (un - vn).abs().to_numpy(float); ref = np.abs(vn.to_numpy(float))
        tol = np.maximum(rtol * ref, unit * 1.000001)
        if np.nanmax(np.where(np.isnan(d), 0, d) - tol) > 0:
            return False, 0
        nflip += int(np.nansum(d > rtol * ref + 1e-300))
    return True, nflip


def _flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _flat(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _flat(v, f"{p}/{i}")
    else:
        yield p, o


def _json_rel(a, b):
    try:
        x, y = dict(_flat(json.loads(a))), dict(_flat(json.loads(b)))
    except Exception:
        return None
    if x.keys() != y.keys():
        return None
    m = 0.0
    for k in x:
        u, v = x[k], y[k]
        if isinstance(u, (int, float)) and isinstance(v, (int, float)) and not isinstance(u, bool):
            if u != v:
                m = max(m, abs(u - v) / max(abs(v), 1e-12))
        elif u != v:
            return None
    return m


def vs_published(a, b, name):
    if b is None:
        return "元に無い"
    if a == b:
        return "同じ"
    if name.endswith(".gz"):
        try:
            a, b = gzip.decompress(a), gzip.decompress(b)
        except OSError:
            return "違う"
        if a == b:
            return "同じ（中身）"
    if name.endswith(".csv") or name.endswith(".csv.gz"):
        ok, n = _close_csv(a, b)
        if ok:
            return f"同じ（丸めの差 {n} セル）"
    if name.endswith(".json"):
        r = _json_rel(a, b)
        if r is not None:
            return f"近い（相対 {r:.1e}）"
    return "違う"


def kind_of(f):
    return "数字" if (f.suffix in NUM or f.name.endswith(".csv.gz")) else ("見た目" if f.suffix in LOOK else "その他")


def produced(repo, arts, since):
    for a in arts:
        for f in sorted((repo / "articles" / a).rglob("*")):
            if f.is_file() and "/src/" not in f.as_posix() and "__pycache__" not in f.parts and f.stat().st_mtime >= since:
                yield a, f


def make_manifest(repo, arts, since, target):
    m = {}
    for a, f in produced(repo, arts, since):
        if kind_of(f) == "数字":
            k = f.relative_to(repo / "articles").as_posix()
            m[k] = content_md5(f.read_bytes(), f.name, k)
    MANIFEST.parent.mkdir(exist_ok=True)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    old[target] = dict(sorted(m.items()))
    MANIFEST.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[基準] {len(m)} ファイルの md5 を {MANIFEST} に書いた（target={target}）")


def check(repo, arts, since, out_csv, target="report"):
    man = json.loads(MANIFEST.read_text(encoding="utf-8")).get(target, {}) if MANIFEST.exists() else {}
    rows, seen = [], set()
    for a, f in produced(repo, arts, since):
        rel = f.relative_to(repo).as_posix(); key = f.relative_to(repo / "articles").as_posix()
        b = f.read_bytes(); kind = kind_of(f)
        if kind == "数字" and key in man:
            vb = "同じ" if content_md5(b, f.name, key) == man[key] else "違う"; seen.add(key)
        else:
            vb = "—"
        vp = vs_published(b, _head_blob(repo, rel), f.name)
        rows.append({"回": a[:4], "ファイル": key.split("/", 1)[1], "種類": kind, "基準と": vb, "元のファイルと": vp})
    missing = [k for k in man if k not in seen]
    for k in missing:
        rows.append({"回": k[:4], "ファイル": k.split("/", 1)[1], "種類": "数字", "基準と": "作られなかった", "元のファイルと": "—"})
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["回", "ファイル", "種類", "基準と", "元のファイルと"]); w.writeheader(); w.writerows(rows)
    num = [r for r in rows if r["種類"] == "数字"]
    bad = [r for r in num if r["基準と"] in ("違う", "作られなかった")]
    def c(col, pre, rs=num): return sum(1 for r in rs if r[col].startswith(pre))
    if man:
        print(f"[照合] 基準と：数字のファイル {len(man)} のうち 同じ {c('基準と', '同じ')}、違う {c('基準と', '違う')}、作られなかった {len(missing)}")
    else:
        print("[照合] 基準（expected/manifest.json）が無いので、元のファイルとだけ比べた")
    print(f"[照合] 元のファイルと：数字 同じ {c('元のファイルと', '同じ')}（うち丸めの差 {c('元のファイルと', '同じ（丸め')}・"
          f"gz の中身 {c('元のファイルと', '同じ（中身')}）、近い {c('元のファイルと', '近い')}、違う {c('元のファイルと', '違う')}、"
          f"元に無い {c('元のファイルと', '元に無い')}")
    for r in bad[:20]:
        print("   NG：", r["回"], r["ファイル"], r["基準と"])
    print(f"[照合] 一覧：{out_csv}")
    return (not bad) if man else (c("元のファイルと", "違う") == 0)
