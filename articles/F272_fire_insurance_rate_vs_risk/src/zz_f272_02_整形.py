"""02 整形：各年度版の第2表（火災保険 住宅物件都道府県別統計表）を縦長の表にする。
k_YYYY.xlsx は YYYY 年度版で、中身は YYYY-1 年度の統計。
2015〜2017年度版（2014〜2016年度）は1年契約だけの集計、2018年度版（2017年度）からは全契約の集計。"""
import pathlib, re
import openpyxl, pandas as pd
B = pathlib.Path(__file__).resolve().parents[1]
PREF = ["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川","新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄"]
def norm(s):
    s = re.sub(r"[\s　]", "", str(s))
    s = re.sub(r"(都|府|県)$", "", s) if s not in ("京都",) else s
    if s == "京都府": s = "京都"
    return s
def num(v):
    if v is None or (isinstance(v, str) and v.strip() in ("X", "x", "－", "-", "")): return None
    return float(v)
out = []
for y in range(2015, 2026):
    wb = openpyxl.load_workbook(B / "data" / "raw" / f"k_{y}.xlsx", read_only=True, data_only=True)
    sh = [n for n in wb.sheetnames if re.sub(r"\s", "", n) in ("第２表", "第2表")][0]
    rows = list(wb[sh].iter_rows(values_only=True))
    title = rows[1][0]
    scope = "1年契約" if "1年契約" in "".join(str(r[0]) for r in rows if r[0]) or "１年契約" in "".join(str(r[0]) for r in rows if r[0]) else "全契約"
    seen = set()
    for r in rows[7:]:
        if r[0] is None: continue
        k = norm(r[0])
        if k == "京都府": k = "京都"
        if k in PREF or k in ("分類不能", "合計", "計"):
            k = "合計" if k in ("合計", "計") else k
            if k in seen: continue
            seen.add(k)
            out.append(dict(fy=y - 1, edition=y, scope=scope, pref=k, n_new=num(r[1]), amount_mil=num(r[2]),
                            prem_k=num(r[3]), n_claim=num(r[4]), claim_k=num(r[5])))
    miss = [p for p in PREF if p not in seen]
    assert not miss, (y, miss)
df = pd.DataFrame(out)
# 都道府県の和と合計の照合（X で伏せた支払は除いて比べる）
for (fy), g in df.groupby("fy"):
    p = g[g.pref.isin(PREF + ["分類不能"])]; t = g[g.pref == "合計"].iloc[0]
    for c in ["n_new", "amount_mil", "prem_k", "n_claim"]:
        assert abs(p[c].sum() - t[c]) <= max(2, 1e-6 * t[c]) + 5, (fy, c, p[c].sum(), t[c])
(B / "data" / "processed").mkdir(parents=True, exist_ok=True)
df.to_csv(B / "data" / "processed" / "fire_pref_fy2014_2024.csv", index=False)
x = df[df.pref.isin(PREF)]
print(df.groupby(["fy", "scope"]).size().to_string())
print("X（伏せ字）の支払保険金:", x.claim_k.isna().sum(), "件", x[x.claim_k.isna()][["fy", "pref"]].values.tolist())
