"""実行して確かめる記事を、層別の無作為抽出で選ぶ（乱数の種 165）。
層：通常記事の前半（000〜109）・後半（110〜）、看板記事の前半（F01〜F80）・後半（F81〜F163）。各層10本。
使い方: python 02_抽出.py <棚卸しCSV> <出力CSV>
"""
import sys, pandas as pd, numpy as np
d = pd.read_csv(sys.argv[1])
def stratum(r):
    if r.kind == "通常": return "通常・前半" if r.num < 110 else "通常・後半"
    return "看板・前半" if r.num <= 80 else "看板・後半"
d["stratum"] = d.apply(stratum, axis=1)
rng = np.random.default_rng(165)
parts = []
for s, g in d.groupby("stratum"):
    idx = rng.choice(len(g), size=min(10, len(g)), replace=False)
    parts.append(g.iloc[sorted(idx)].assign(N_stratum=len(g)))
out = pd.concat(parts)[["folder", "kind", "num", "stratum", "N_stratum"]]
out.to_csv(sys.argv[2], index=False)
print(out.groupby("stratum").agg(n=("folder", "size"), N=("N_stratum", "first")))
