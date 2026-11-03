"""02 整形：data/raw/f138_ess2022_telework.json → data/telework_industry.csv, data/telework_occupation.csv
raw は e-Stat データベース表 03700（産業）・03800（職業）を地域ごとに表示して読み取ったもの。
キーは 産業表が「地域|地位」（0=総数, 4=会社などの役員を除く雇用者）、職業表が「地域」。値は表の行（1行目が見出し）。"""
import os, json
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
raw = json.load(open(os.path.join(ROOT, "data", "raw", "f138_ess2022_telework.json"), encoding="utf-8"))
COLS = {"総数": "total", "実施した": "tw", "20％未満": "f0_20", "20～40％未満": "f20_40", "40～60％未満": "f40_60",
        "60～80％未満": "f60_80", "80％以上": "f80", "自宅": "home", "サテライトオフィス": "satellite", "その他": "other", "実施していない": "no_tw"}
def num(s):
    s = (s or "").replace(",", "").strip()
    return float(s) if s not in ("", "-", "…", "X", "x", "***") else 0.0
def tidy(rows, extra):
    head = rows[0][1:]
    out = []
    for r in rows[1:]:
        d = dict(extra); d["cat"] = r[0]
        for h, v in zip(head, r[1:]):
            if h in COLS: d[COLS[h]] = num(v)
        out.append(d)
    return out
ind, occ = [], []
for k, rows in raw["industry"].items():
    reg, st = k.split("|")
    ind += tidy(rows, {"region": reg, "status": {"0": "有業者総数", "4": "雇用者（役員を除く）"}[st]})
for reg, rows in raw["occupation"].items():
    occ += tidy(rows, {"region": reg, "status": "有業者総数"})
I = pd.DataFrame(ind); O = pd.DataFrame(occ)
# 前の地域の表が残っていないかの確認：地域ごとの総数が全て異なること
for D, nm in [(I, "industry"), (O, "occupation")]:
    t = D[D.cat == "総数"].groupby("status")["total"]
    assert all(t.apply(lambda s: s.is_unique)), f"{nm}: 同じ総数の地域がある（取り違えの疑い）"
    # 産業・職業の合計（分類不能を含む）と総数の差
I.to_csv(os.path.join(ROOT, "data", "telework_industry.csv"), index=False, encoding="utf-8")
O.to_csv(os.path.join(ROOT, "data", "telework_occupation.csv"), index=False, encoding="utf-8")
print(I.shape, O.shape, I.region.nunique(), O.region.nunique())
