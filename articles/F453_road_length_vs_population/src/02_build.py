"""道路の全国の推移（表1-1）、都道府県別（表4、2時点）、人口（人口推計）を取り出して data/ に CSV で置く。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s)))
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
COL = {"expressway": 1, "national": 8, "prefectural": 17, "municipal": 23, "general": 26}


def num(x):
    return float(x) if isinstance(x, (int, float)) and not pd.isna(x) else None


# 表1-1：行のラベル → 時点
v = pd.read_excel(RAW / "road_t1_1_2025.xlsx", header=None)
era, recs, prev_fy = None, [], None
for i in range(len(v)):
    lab = v.iloc[i, 0]
    if pd.isna(lab):
        continue
    s = n(lab)
    m = re.match(r"^(昭和|平成|令和)?(元|\d+)?(\(初\))?$", s)
    if not m or (m.group(2) is None and m.group(3) is None):
        continue
    if m.group(1):
        era = m.group(1)
    if m.group(2):
        fy = ERA[era] + (1 if m.group(2) == "元" else int(m.group(2)))
    else:
        fy = prev_fy  # 「（初）」だけの行は、直前の年度のラベルの続き
    prev_fy = fy
    row = v.iloc[i]
    if num(row[COL["general"]]) is None:
        continue  # 上段の率の行
    start = m.group(3) is not None
    t = fy + (0.25 if start else 1.25)  # 年度当初＝その年の4月、年度末＝翌年の3月末（≒4月）
    vals = {k: num(row[c]) for k, c in COL.items()}
    # 単位は km と m が混ざる（同じ行の中でも列ごとに違うことがある）。列ごとの大きさで m を判定して km に直す
    TH = {"expressway": 1e5, "national": 1e6, "prefectural": 1e6, "municipal": 1e7, "general": 1e7}
    recs.append(dict(t=t, fy=fy, point="start" if start else "end", **{k: (x / 1000 if x is not None and x > TH[k] else x) for k, x in vals.items()}))
nat = pd.DataFrame(recs).drop_duplicates("t", keep="last").sort_values("t")
nat.to_csv(ROOT / "data" / "road_national.csv", index=False, float_format="%.3f")

# 表4：都道府県（政令指定都市は県に足す）
def t4(path):
    w = pd.read_excel(path, header=None)
    out = {}
    for i in range(len(w)):
        s = n(w.iloc[i, 0]) if isinstance(w.iloc[i, 0], str) else ""  # 下の方の日付の行（前年までの合計）は使わない
        m = re.match(r"^(\d{2})(\d{2})?(.+)$", s)
        val = num(w.iloc[i, 8])
        if not m or val is None:
            continue
        code = int(m.group(1))
        kind = "city" if m.group(2) else "pref"
        out.setdefault(code, {"pref_only": 0.0, "with_city": 0.0, "name": None})
        if kind == "pref":
            out[code]["pref_only"] += val; out[code]["name"] = m.group(3)
        out[code]["with_city"] += val
    d = pd.DataFrame(out).T
    d.index.name = "code"
    assert len(d) == 47
    tot = next(num(w.iloc[i, 8]) for i in range(len(w)) if isinstance(w.iloc[i, 0], str) and n(w.iloc[i, 0]) == "合計")
    assert abs(d.with_city.sum() - tot) < 1, (d.with_city.sum(), tot)  # 県＋政令市の合計が表の合計と一致
    return d


a, b = t4(RAW / "road_t4_2016.xls"), t4(RAW / "road_t4_2025.xlsx")
pref = pd.DataFrame({"name": b.name, "road_2016ed_km": a.with_city.astype(float) / 1000, "road_2025ed_km": b.with_city.astype(float) / 1000,
                     "road_pref_only_2016ed_km": a.pref_only.astype(float) / 1000, "road_pref_only_2025ed_km": b.pref_only.astype(float) / 1000})

# 人口（千人）
def pop_wide(path, sheet=0):
    w = pd.read_excel(path, header=None, sheet_name=sheet)
    isyr = lambda x: (not pd.isna(x)) and re.fullmatch(r"(19|20)\d\d年?", str(x).strip().split(".")[0]) is not None
    yr_row = next(i for i in range(15) if sum(isyr(x) for x in w.iloc[i]) >= 5)
    years = {j: int(str(x).strip().split(".")[0].rstrip("年")) for j, x in enumerate(w.iloc[yr_row]) if isyr(x)}
    rows = {}
    for i in range(yr_row + 1, len(w)):
        cells = w.iloc[i].tolist()
        lab = "".join(n(c) for c in cells[:4] if isinstance(c, str))
        code = cells[1]
        if lab.startswith("全国"):
            key = 0
        elif isinstance(code, (int, float)) and not pd.isna(code) and 1 <= code <= 47:
            key = int(code)
        else:
            continue
        if key in rows:
            continue
        rows[key] = {y: num(cells[j]) for j, y in years.items()}
    return pd.DataFrame(rows).T


p1 = pop_wide(RAW / "pop_pref_1920_2000.xlsx")
# 2000〜2020年の表は総人口のシートが2つ（2000〜2015年、2015〜2020年）に分かれている
xl = pd.ExcelFile(RAW / "pop_pref_2000_2020.xlsx")
tot_sheets = [s for s in xl.sheet_names if s.startswith("総人口")]
p2 = pd.concat([pop_wide(RAW / "pop_pref_2000_2020.xlsx", sheet=s) for s in tot_sheets], axis=1)
p2 = p2.loc[:, ~p2.columns.duplicated()]
# 2020〜2024年（縦長の表）
w = pd.read_excel(RAW / "pop_pref_2020_2024.xlsx", header=None)
hdr = next(i for i in range(15) if any(n(c) == "地域" for c in w.iloc[i] if isinstance(c, str)))
H = [n(c) if isinstance(c, str) else c for c in w.iloc[hdr]]
cy = {j: int(re.search(r"(\d{4})", str(c)).group(1)) for j, c in enumerate(w.iloc[hdr]) if re.search(r"^\d{4}年", n(c) if isinstance(c, str) else "")}
c_code = H.index("都道府県コード"); c_sex = H.index("性別"); c_kind = H.index("人口区分")
rows = {}
for i in range(hdr + 1, len(w)):
    r = w.iloc[i]
    if n(r[c_kind]) != "総人口" or n(r[c_sex]) != "男女計":
        continue
    key = int(str(r[c_code])[:2])
    rows[key] = {y: num(r[j]) for j, y in cy.items()}
p3 = pd.DataFrame(rows).T
pop = p1.join(p2.drop(columns=[c for c in p2.columns if c in p1.columns]), how="outer").join(p3.drop(columns=[c for c in p3.columns if c in p1.columns or c in p2.columns]), how="outer")
pop = pop.reindex(sorted(pop.columns), axis=1)
pop.index.name = "code"
pop.to_csv(ROOT / "data" / "population_thousand.csv", float_format="%.1f")
pref.to_csv(ROOT / "data" / "road_pref.csv", float_format="%.3f")
print(nat.tail(8).to_string()); print(pop.loc[[0, 1, 13, 47], [1955, 2000, 2008, 2015, 2020, 2023, 2024]]); print(pref.head(3), pref.sum(numeric_only=True))
