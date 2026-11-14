"""記事フォルダを空の場所で流し直し、results/ と data/ がリポジトリの中身と一致するかを確かめる。

対象：記事の一覧のうち、src/ に a<番号>_*.py が1本ある記事（551〜）。データは乱数で作り直されるもの。
図（PNG）は、フォントや環境で画素が変わるので比べない。
使い方：
  python tools/repro_check.py --articles 601 742            # 番号を指定
  python tools/repro_check.py --chunk auto --n-chunks 5      # 週の番号で5分の1ずつ回す
"""
import argparse, datetime, glob, gzip, io, json, math, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "articles"
RTOL, ATOL = 1e-6, 1e-9


def targets():
    out = []
    for d in sorted(ART.iterdir()):
        m = re.match(r"^(\d{3})_", d.name)
        if not m or int(m.group(1)) < 551:
            continue
        mains = sorted((d / "src").glob(f"a{m.group(1)}_*.py"))
        if len(mains) == 1:
            out.append((int(m.group(1)), d, mains[0].name))
    return out


def close(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        return math.isclose(a, b, rel_tol=RTOL, abs_tol=ATOL)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b


def read(p):
    raw = p.read_bytes()
    if p.suffix == ".gz":
        raw = gzip.decompress(raw)
        name = p.stem
    else:
        name = p.name
    return name, raw


def same_file(p, q):
    n, a = read(p); _, b = read(q)
    if a == b:
        return True, "同じ"
    if n.endswith(".json"):
        ok = close(json.loads(a), json.loads(b))
        return ok, "数値の誤差の範囲" if ok else "JSON の値が違う"
    if n.endswith(".csv"):
        try:
            x = pd.read_csv(io.BytesIO(a)); y = pd.read_csv(io.BytesIO(b))
            pd.testing.assert_frame_equal(x, y, check_exact=False, rtol=RTOL, atol=ATOL, check_dtype=False)
            return True, "数値の誤差の範囲"
        except Exception as e:
            return False, "CSV の値が違う: " + str(e).splitlines()[0][:120]
    return False, "中身が違う"


def check(no, d, main, timeout=900):
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / d.name
        shutil.copytree(d / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        for sub in ("data", "results", "figures"):
            (work / sub).mkdir(exist_ok=True)
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLBACKEND="Agg")
        r = subprocess.run([sys.executable, main], cwd=work / "src", env=env, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return dict(no=no, ok=False, sec=round(time.time() - t0, 1), detail="実行エラー: " + (r.stderr.strip().splitlines() or [""])[-1][:200])
        bad = []; n = 0
        for sub in ("results", "data"):
            for p in sorted((d / sub).glob("*")) if (d / sub).exists() else []:
                if not p.is_file():
                    continue
                q = work / sub / p.name
                n += 1
                if not q.exists():
                    bad.append(f"{sub}/{p.name}: 作られなかった"); continue
                ok, why = same_file(p, q)
                if not ok:
                    bad.append(f"{sub}/{p.name}: {why}")
        return dict(no=no, ok=not bad, sec=round(time.time() - t0, 1), files=n, detail="; ".join(bad) or "一致")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles", nargs="*", type=int)
    ap.add_argument("--chunk", default=None, help="auto か 0 から始まる番号")
    ap.add_argument("--n-chunks", type=int, default=5)
    ap.add_argument("--out", default="repro_result.json")
    a = ap.parse_args()
    T = targets()
    if a.articles:
        T = [t for t in T if t[0] in a.articles]
    elif a.chunk is not None:
        k = datetime.date.today().isocalendar()[1] % a.n_chunks if a.chunk == "auto" else int(a.chunk)
        T = [t for i, t in enumerate(T) if i % a.n_chunks == k]
    res = []
    for no, d, m in T:
        r = check(no, d, m); res.append(r)
        print(("OK  " if r["ok"] else "NG  ") + f"{no} {r['sec']}s {r['detail']}", flush=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ng = [r for r in res if not r["ok"]]
    summ = f"## 再現チェック\n\n対象 {len(res)}本・一致 {len(res)-len(ng)}本・不一致 {len(ng)}本\n\n"
    if ng:
        summ += "| 記事 | 内容 |\n|---|---|\n" + "\n".join(f"| {r['no']} | {r['detail']} |" for r in ng) + "\n"
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summ)
    print(summ)
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()
