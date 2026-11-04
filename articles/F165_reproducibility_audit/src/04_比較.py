"""作り直した results/ を、リポジトリにあるもとの results/ と比べる。
使い方: python 04_比較.py <作業ディレクトリ> <実行結果CSV> <出力CSV(記事ごと)> <出力CSV(ファイルごと)>
数値は相対誤差で判定：完全一致／1e-6以内／1e-3以内／1e-2以内／ずれ。文字のファイルは、数字を抜き出して同じ基準で比べる。
"""
import sys, re, csv, io
from pathlib import Path
import numpy as np, pandas as pd

work = Path(sys.argv[1]); runs = pd.read_csv(sys.argv[2])
NUM = re.compile(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+(?:[eE][-+]?\d+)?")
ORDER = ["完全一致", "1e-6以内", "1e-3以内", "1e-2以内", "ずれ", "形が違う", "作られない"]
LOG = re.compile(r"(^|/)(run_)?log[^/]*\.txt$|_log\.txt$", re.I)
LEVELS = [("完全一致", 0.0), ("1e-6以内", 1e-6), ("1e-3以内", 1e-3), ("1e-2以内", 1e-2)]

def level(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return "形が違う"
    m = ~(np.isnan(a) & np.isnan(b))
    if (np.isnan(a[m]) != np.isnan(b[m])).any(): return "ずれ"
    a, b = a[m & ~np.isnan(a)], b[m & ~np.isnan(b)]
    if len(a) == 0: return "完全一致"
    if np.array_equal(a, b): return "完全一致"
    # 0 に近い値で相対誤差が大きく出すぎないよう、分母はその列（文字のファイルは全体）の最大の絶対値の1%を下限にする
    scale = np.nanmax(np.abs(b)) if np.isfinite(b).any() else 1.0
    den = np.maximum(np.abs(b), 0.01 * scale + 1e-300)
    rel = np.abs(a - b) / den
    mx = float(np.nanmax(rel))
    for name, tol in LEVELS:
        if mx <= tol: return name
    return "ずれ"

def nums(text):
    return [float(x) for x in NUM.findall(text)]

def compare(e, n):
    suf = e.suffix.lower()
    if suf in (".csv", ".tsv"):
        try:
            de = pd.read_csv(e, sep=None, engine="python"); dn = pd.read_csv(n, sep=None, engine="python")
        except Exception:
            return compare_text(e, n)
        if de.shape != dn.shape or list(de.columns) != list(dn.columns): return "形が違う"
        ne = de.select_dtypes("number"); nn = dn[ne.columns].apply(pd.to_numeric, errors="coerce")
        oe = de.drop(columns=ne.columns).astype(str); on = dn.drop(columns=ne.columns).astype(str)
        if not oe.equals(on): return "ずれ"
        if not ne.shape[1]: return "完全一致"
        lv = [level(nn[c].values, ne[c].values) for c in ne.columns]
        return max(lv, key=lambda x: ORDER.index(x) if x in ORDER else 0)
    if suf in (".txt", ".md", ".json", ".tex", ".html"):
        return compare_text(e, n)
    if e.read_bytes() == n.read_bytes(): return "完全一致"
    return "比較しない"

def compare_text(e, n):
    te, tn = e.read_text(errors="ignore"), n.read_text(errors="ignore")
    if te == tn: return "完全一致"
    a, b = nums(tn), nums(te)
    if len(a) != len(b): return "形が違う"
    return level(a, b)

per_file, per_art = [], []
for _, r in runs.iterrows():
    name = r.folder
    exp = work / "_expected" / name / "results"; new = work / name / "results"
    files = [p for p in exp.rglob("*") if p.is_file() and p.suffix.lower() in (".csv", ".tsv", ".txt", ".md", ".json")
             and not LOG.search(str(p.relative_to(exp)))] if exp.exists() else []
    n_logs = sum(1 for p in exp.rglob("*") if p.is_file() and LOG.search(str(p.relative_to(exp)))) if exp.exists() else 0
    levels = []
    for e in files:
        rel = e.relative_to(exp); n = new / rel
        lv = compare(e, n) if n.exists() else "作られない"
        levels.append(lv); per_file.append(dict(folder=name, file=str(rel), level=lv))
    cnt = {k: levels.count(k) for k in ORDER}
    if not files: worst = "比べる結果なし"
    else:
        worst = max((l for l in levels if l in ORDER), key=ORDER.index, default="比べる結果なし")
    per_art.append(dict(folder=name, n_result_files=len(files), n_logs_excluded=n_logs, worst=worst,
                        share_match_1e3=round(sum(cnt[k] for k in ORDER[:3]) / len(files), 3) if files else np.nan,
                        **{f"n_{k}": v for k, v in cnt.items()}))
pd.DataFrame(per_art).to_csv(sys.argv[3], index=False)
pd.DataFrame(per_file).to_csv(sys.argv[4], index=False)
print(pd.DataFrame(per_art)[["folder", "n_result_files", "worst", "share_match_1e3"]].to_string())
