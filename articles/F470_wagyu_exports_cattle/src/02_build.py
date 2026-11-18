"""data/raw の Excel・CSV を読み、分析に使う CSV を data/ に作る。ネットにはつながない。
列は行や列の位置ではなく、表の見出しの文字（上の段から順につないだもの）で選ぶ。選んだ列の見出しと、
内訳の合計が計と合うかを results/build_checks.csv に書く。"""
import gzip, io, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; D = ROOT / "data"; R = ROOT / "results"
R.mkdir(exist_ok=True)
checks = []


def header_paths(df, top, bottom):
    """見出しの段（top〜bottom 行）を、結合セルの分だけ右へ広げてから、上の段から順に「/」でつなぐ。
    上の段のどこかに文字がある列（新しい見出しが始まる列）で、下の段の広げを切る。"""
    ncol = df.shape[1]

    def cell(r, c):
        v = df.iat[r, c]
        if isinstance(v, float) and np.isnan(v):
            return None
        v = str(v).replace("\n", "").replace("　", "").replace(" ", "").strip()
        return v or None

    filled = []
    boundary = [False] * ncol
    for r in range(top, bottom + 1):
        row, cur = [], None
        for c in range(ncol):
            v = cell(r, c)
            if boundary[c]:
                cur = None
            if v:
                cur = v
            row.append(cur)
        filled.append(row)
        boundary = [boundary[c] or cell(r, c) is not None for c in range(ncol)]
    return ["/".join([filled[i][c] for i in range(len(filled)) if filled[i][c]]) for c in range(ncol)]


def pick(paths, must, exact_end=None, exclude=()):
    hits = [i for i, p in enumerate(paths) if all(m in p for m in must) and not any(e in p for e in exclude)
            and (exact_end is None or p.endswith(exact_end))]
    if len(hits) != 1:
        raise ValueError(f"見出し {must} {exact_end} の列が1つに決まらない：{[paths[i] for i in hits]}")
    return hits[0]


def num(v):
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if v in ("…", "-", "x", "－", "…", ""):
            return np.nan
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def year_of(lbl):
    m = re.search(r"\((\d{4})\)", str(lbl))
    return int(m.group(1)) if m else None


# 1) 畜産統計 肉用牛（全国、各年2月1日）
df = pd.read_excel(RAW / "chikusan_nikuyougyu_zenkoku.xls", header=None)
paths = header_paths(df, 4, 9)
COLS = {
    "farms": (["飼養戸数"], "飼養戸数", ["乳用種"]),
    "total": (["飼養頭数", "総頭数"], None, []),
    "beef_breed": (["飼養頭数", "肉用種", "計"], "肉用種/計", []),
    "kuroge": (["肉用種", "黒毛和種"], None, []),
    "breeding_cows": (["肉用種", "めす", "子取り用めす牛"], "子取り用めす牛/小計", ["出産経験"]),
    "dairy_breed": (["飼養頭数", "乳用種", "計"], "乳用種/計", []),
    "holstein": (["乳用種", "ホルスタイン種他"], "ホルスタイン種他", []),
    "cross": (["乳用種", "交雑種"], "交雑種", []),
    "per_farm": (["1戸当たり飼養頭数"], None, []),
}
idx = {}
for k, (must, end, exc) in COLS.items():
    idx[k] = pick(paths, must, end, exc)
    checks.append({"check": f"畜産統計の列 {k}", "value": paths[idx[k]], "ok": True})
rows = []
for r in range(10, df.shape[0]):
    lbl = df.iat[r, 0]
    y = year_of(lbl)
    if y is None:
        continue
    method = "old" if "旧" in str(lbl) else ("new" if ("新" in str(lbl) or y >= 2020) else "old")
    rec = {"year": y, "method": method, "label": str(lbl)}
    for k, c in idx.items():
        rec[k] = num(df.iat[r, c])
    rows.append(rec)
heads = pd.DataFrame(rows).sort_values(["year", "method"]).reset_index(drop=True)
heads.to_csv(D / "cattle_heads.csv", index=False)
# 内訳の点検：肉用種＋乳用種＝総頭数（四捨五入の差）、ホルスタイン種他＋交雑種＝乳用種
h = heads.dropna(subset=["beef_breed", "dairy_breed"])
checks.append({"check": "肉用種＋乳用種と総頭数の差の最大（頭）", "value": float((h.beef_breed + h.dairy_breed - h.total).abs().max()), "ok": bool((h.beef_breed + h.dairy_breed - h.total).abs().max() <= 2000)})
h2 = heads.dropna(subset=["holstein", "cross"])
checks.append({"check": "ホルスタイン種他＋交雑種と乳用種の差の最大（頭）", "value": float((h2.holstein + h2.cross - h2.dairy_breed).abs().max()), "ok": bool((h2.holstein + h2.cross - h2.dairy_breed).abs().max() <= 2000)})
# 元の表と照らす（見出しで選んだ列の値を、元の表の 2025 年の行から直接読み直す）
r25 = [r for r in range(df.shape[0]) if str(df.iat[r, 0]).startswith("令.7(2025)")][0]
for k in ["total", "beef_breed", "cross"]:
    checks.append({"check": f"2025年 {k} の再読み取り", "value": num(df.iat[r25, idx[k]]), "ok": num(df.iat[r25, idx[k]]) == float(heads[(heads.year == 2025)][k].iloc[0])})


# 2) 畜産物流通統計：と畜頭数・枝肉生産量（全国、暦年）
def read_ryutsu(name, unit_col):
    t = pd.read_excel(RAW / name, header=None)
    p = header_paths(t, 4, 6)
    sel = {
        "wagyu": (["成牛", "和牛", "小計"], None, []),
        "dairy_old": (["成牛", "乳牛（乳用種）", "小計"], None, []),
        "dairy": (["成牛", "乳牛/小計"], None, ["乳牛（乳用種）"]),
        "cross": (["成牛", "交雑牛", "小計"], None, []),
        "adult_total": (["成牛", "計"], "成牛/計", []),
    }
    ix = {k: pick(p, m, e, x) for k, (m, e, x) in sel.items()}
    for k, c in ix.items():
        checks.append({"check": f"{name} の列 {k}", "value": p[c], "ok": True})
    out = []
    for r in range(8, t.shape[0]):
        y = year_of(t.iat[r, 0])
        if y is None:
            continue
        rec = {"year": y}
        for k, c in ix.items():
            rec[k] = num(t.iat[r, c])
        out.append(rec)
    return pd.DataFrame(out)


sl = read_ryutsu("ryutsu_tochiku_tosu.xls", "頭").rename(columns=lambda c: c if c == "year" else f"{c}_head")
cw = read_ryutsu("ryutsu_edaniku.xls", "t").rename(columns=lambda c: c if c == "year" else f"{c}_t")
meat = sl.merge(cw, on="year", how="outer").sort_values("year")
meat.to_csv(D / "slaughter_carcass.csv", index=False)
m10 = meat[meat.year >= 2010]
checks.append({"check": "2010年以降 和牛＋乳牛＋交雑牛＋その他≒成牛計（枝肉t、その他を除いた差の最大）",
               "value": float((m10.adult_total_t - m10.wagyu_t - m10.dairy_t - m10.cross_t).max()), "ok": bool((m10.adult_total_t - m10.wagyu_t - m10.dairy_t - m10.cross_t).min() >= -5)})

# 3) 和牛計の中央卸売市場価格
t = pd.read_excel(RAW / "ryutsu_wagyu_price.xls", header=None)
p = header_paths(t, 4, 6)
ci = pick(p, ["1kg当たり卸売価格"]); cn = pick(p, ["取引成立頭数"], "取引成立頭数")
checks.append({"check": "和牛価格の列", "value": p[ci] + " / " + p[cn], "ok": True})
price = pd.DataFrame([{"year": year_of(t.iat[r, 0]), "wagyu_price_yen_kg": num(t.iat[r, ci]), "wagyu_traded_head": num(t.iat[r, cn])}
                      for r in range(8, t.shape[0]) if year_of(t.iat[r, 0])])
price.to_csv(D / "wagyu_price.csv", index=False)

# 4) 貿易統計：牛肉（HS 0201 生鮮・冷蔵、0202 冷凍）の輸出
ex = []
for f in sorted((RAW / "trade").glob("export_*.csv.gz")):
    raw = gzip.decompress(f.read_bytes()).decode("cp932")
    tr = pd.read_csv(io.StringIO(raw), dtype=str)
    tr["HS"] = tr["HS"].str.strip("'")
    b = tr[tr["HS"].str[:4].isin(["0201", "0202"])].copy()
    for c in ["Quantity2-Year", "Value-Year"]:
        b[c] = b[c].astype(float)
    assert set(b["Unit2"].str.strip()) == {"KG"}, b["Unit2"].unique()
    y = int(tr["Year"].iloc[0])
    for hs4, g in b.groupby(b["HS"].str[:4], sort=True):
        ex.append({"year": y, "hs4": hs4, "kg": g["Quantity2-Year"].sum(), "value_1000yen": g["Value-Year"].sum(), "n_codes": len(g)})
exp = pd.DataFrame(ex).sort_values(["year", "hs4"])
exp.to_csv(D / "beef_export_hs4.csv", index=False)
checks.append({"check": "貿易統計の年数", "value": int(exp.year.nunique()), "ok": int(exp.year.nunique()) == 17})
pd.DataFrame(checks).to_csv(R / "build_checks.csv", index=False)
print(pd.DataFrame(checks).to_string())
