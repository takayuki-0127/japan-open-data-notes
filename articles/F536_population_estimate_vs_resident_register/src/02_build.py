"""02_build.py：人口推計と住民基本台帳の都道府県別の表を読み、1つの縦長の CSV にする。
都道府県は表の中の都道府県コードで付け、同じ行の都道府県名の文字が一致することを確かめる（行の順では付けない）。
年・人口区分（総人口・日本人）・年齢は見出しの文字で探す。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PREF = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]


def norm(s):
    return re.sub(r"[\s*＊]+", "", unicodedata.normalize("NFKC", str(s))) if s is not None and str(s) != "nan" else ""


def code_of(v):
    s = norm(v).split(".")[0]
    if re.fullmatch(r"\d{1,6}", s):
        n = int(s[:2]) if len(s) in (5, 6) else int(s)
        return n if 1 <= n <= 47 else (0 if n == 0 else None)
    return None


def check_name(code, text):
    t = norm(text)
    assert t == norm(PREF[code - 1]) or t == norm(PREF[code - 1])[:-1], (code, text)  # 「北海道」や「東京都」など


def age_key(s):
    t = norm(s)
    if t in ("総数",):
        return "total"
    m = re.match(r"(\d+)歳?[~～]+(\d+)", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"(\d+)歳以上", t)
    return f"{m.group(1)}+" if m else None


rows = []  # source, kind, year, pref, age, value, unit


def add(src, kind, year, pref, age, val, unit):
    rows.append(dict(source=src, kind=kind, year=int(year), pref=int(pref), age=age, value=float(val), unit=unit))


# ---- 人口推計 長期時系列（補間補正、2000〜2020年） ----
x = pd.ExcelFile(RAW / "suikei_long_2000_2020.xlsx")
for s in x.sheet_names:
    kind = "total" if norm(s).startswith("総人口") else ("japanese" if norm(s).startswith("日本人") else None)
    d = pd.read_excel(x, s, header=None, dtype=object)
    yr = None
    for i in range(len(d)):
        ys = {j: int(norm(v)[:4]) for j, v in enumerate(d.iloc[i]) if re.fullmatch(r"(19|20)\d\d年?", norm(v))}
        vs = list(ys.values())
        if len(vs) >= 5 and all(b - a == 1 for a, b in zip(vs, vs[1:])):  # 年の行：連続した年が並ぶ
            yr = ys
            continue
        if yr is None:
            continue
        c = None
        for j in range(4):
            cc = code_of(d.iat[i, j]) if j in (1, 2) else None
            if cc:
                c, cj = cc, j
                break
        if not c:
            continue
        check_name(c, d.iat[i, cj + 1])
        for j, y in yr.items():
            v = pd.to_numeric(d.iat[i, j], errors="coerce")
            if pd.notna(v) and y <= 2019:  # 2020年は第5表2024年版（国勢調査）から取る
                add("suikei_revised", kind, y, c, "total", v * 1000, "千人")

# ---- 人口推計 第5表 2019年版（公表時の値）：縦に積まれたブロック ----
d = pd.read_excel(RAW / "suikei_t5_2019.xls", header=None, dtype=object)
kind = sex = None; yr = None
for i in range(len(d)):
    line = norm("".join(norm(v) for v in d.iloc[i, 6:17]))
    if "総人口" in line and ("男女計" in line or line.endswith("男") or line.endswith("女")):
        kind = "total"; sex = "計" if "男女計" in line else line[-1]
    if "日本人人口" in line and ("男女計" in line or line.endswith("男") or line.endswith("女")):
        kind = "japanese"; sex = "計" if "男女計" in line else line[-1]
    ys = {j: int(norm(v)[:4]) for j, v in enumerate(d.iloc[i]) if re.fullmatch(r"20\d\d年", norm(v))}
    if len(ys) >= 3:
        yr = ys
        continue
    c = code_of(d.iat[i, 8])
    if c and yr and sex == "計":
        check_name(c, d.iat[i, 9])
        for j, y in yr.items():
            v = pd.to_numeric(d.iat[i, j], errors="coerce")
            if pd.notna(v):
                add("suikei_original", kind, y, c, "total", v * 1000, "千人")

# ---- 人口推計 第5表 2024年版（縦長の形） ----
d = pd.read_excel(RAW / "suikei_t5_2024.xlsx", header=None, dtype=object)
h = [i for i in range(20) if norm(d.iat[i, 7]) == "人口区分"][0]
hdr = [norm(v) for v in d.iloc[h]]
ci = {k: hdr.index(k) for k in ["人口区分", "性別", "都道府県コード", "地域"]}
ycols = {j: int(v[:4]) for j, v in enumerate(hdr) if re.fullmatch(r"20\d\d年", v)}
for i in range(h + 1, len(d)):
    k = {"総人口": "total", "日本人人口": "japanese"}.get(norm(d.iat[i, ci["人口区分"]]))
    if k is None or norm(d.iat[i, ci["性別"]]) != "男女計":
        continue
    c = code_of(d.iat[i, ci["都道府県コード"]])
    if not c:
        continue
    check_name(c, d.iat[i, ci["地域"]])
    for j, y in ycols.items():
        add("suikei_revised" if y > 2020 else "suikei_census", k, y, c, "total", float(d.iat[i, j]) * 1000, "千人")

# ---- 人口推計 年齢5歳階級 2024年（縦長）・2020年（横長のブロック。最初のブロックが総人口・男女計） ----
d = pd.read_excel(RAW / "suikei_t10_2024.xlsx", header=None, dtype=object)
h = [i for i in range(20) if norm(d.iat[i, 7]) == "時間軸コード"][0]
hdr = [norm(v) for v in d.iloc[h]]
ci = {k: hdr.index(k) for k in ["人口区分", "性別", "都道府県コード", "地域"]}
acols = {j: age_key(v) for j, v in enumerate(d.iloc[h]) if age_key(v)}
for i in range(h + 1, len(d)):
    if norm(d.iat[i, ci["人口区分"]]) != "総人口" or norm(d.iat[i, ci["性別"]]) != "男女計":
        continue
    c = code_of(d.iat[i, ci["都道府県コード"]])
    if not c:
        continue
    check_name(c, d.iat[i, ci["地域"]])
    for j, a in acols.items():
        add("suikei_age", "total", 2024, c, a, float(d.iat[i, j]) * 1000, "千人")

d = pd.read_excel(RAW / "suikei_t10_2020.xls", header=None, dtype=object)
top = " ".join(norm(v) for v in d.iloc[0:11].values.ravel() if norm(v))
assert "総人口" in top and "男女計" in top
hr = [i for i in range(len(d)) if any(norm(v) == "総数" for v in d.iloc[i])][0]
acols = {j: age_key(v) for j, v in enumerate(d.iloc[hr]) if age_key(v)}
nxt = [i for i in range(hr + 1, len(d)) if any(norm(v) == "総数" for v in d.iloc[i])][0]
for i in range(hr + 1, nxt):
    c = code_of(d.iat[i, 2])
    if not c:
        continue
    check_name(c, d.iat[i, 3])
    for j, a in acols.items():
        v = pd.to_numeric(d.iat[i, j], errors="coerce")
        if pd.notna(v):
            add("suikei_age", "total", 2020, c, a, v * 1000, "千人")

# ---- 住民基本台帳（各年1月1日）：人口の「計」の列を見出しで探す ----
def juki_pop(path, kind, year):
    d = pd.read_excel(path, header=None, dtype=object)
    title = norm(d.iat[0, 0])
    assert "1月1日" in title, title
    # 「男」「女」「計」が並ぶ行の、最初の「計」の列
    for i in range(1, 8):
        r = [norm(v) for v in d.iloc[i]]
        if "男" in r and "女" in r and "計" in r:
            col = r.index("計"); break
    hdr_rows = [norm(v) for v in d.iloc[1:6, col - 2:col + 1].values.ravel()]  # 結合セルの「人口」は左端の列にある
    assert any("人口" in v for v in hdr_rows), hdr_rows
    namec = [j for j in range(4) if any(norm(v) == "都道府県名" for v in d.iloc[0:8, j])][0]
    for i in range(len(d)):
        c = code_of(d.iat[i, 0])
        if not c:
            continue
        check_name(c, d.iat[i, namec])
        add("juki", kind, year, c, "total", float(d.iat[i, col]), "人")


for y in range(2014, 2027):
    for kind in ["total", "japanese"]:
        f = [p for p in RAW.glob(f"juki_{kind}_{y}.*")][0]
        juki_pop(f, kind, y)

for y in [2020, 2021, 2024, 2025]:
    f = [p for p in RAW.glob(f"juki_age_{y}.*")][0]
    d = pd.read_excel(f, header=None, dtype=object)
    hr = [i for i in range(6) if any(norm(v) == "総数" for v in d.iloc[i])][0]
    acols = {j: age_key(v) for j, v in enumerate(d.iloc[hr]) if age_key(v)}
    sexc = [j for j in range(5) if any(norm(v) == "性別" for v in d.iloc[0:6, j])][0]
    for i in range(hr + 1, len(d)):
        c = code_of(d.iat[i, 0])
        if not c or norm(d.iat[i, sexc]) != "計":
            continue
        check_name(c, d.iat[i, 1])
        for j, a in acols.items():
            add("juki_age", "total", y, c, a, float(d.iat[i, j]), "人")

df = pd.DataFrame(rows)
# 長期時系列は2015年が2つのシートにある。後のシート（2015〜2020年）の値を使う
df = df.drop_duplicates(["source", "kind", "year", "pref", "age"], keep="last")
df = df.sort_values(["source", "kind", "year", "pref", "age"], kind="mergesort").reset_index(drop=True)
df.to_csv(ROOT / "data" / "population_long.csv", index=False)
print(df.groupby(["source", "kind"]).agg(n=("value", "size"), y0=("year", "min"), y1=("year", "max"), npref=("pref", "nunique")).to_string())
