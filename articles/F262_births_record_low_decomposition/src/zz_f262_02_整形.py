"""02 整形：年齢5歳階級別の出生数と女性人口（日本人）を年ごとの表にする

出力
- data/processed/births_by_age.csv  ：year, a15..a45（15〜19歳 … 45〜49歳）, total_all（年齢不詳を含む総数）, source
  14歳以下は15〜19歳に、50歳以上は45〜49歳に含める（人口動態統計の年齢別出生率・合計特殊出生率と同じ扱い）
- data/processed/asfr_ipss.csv      ：表4-7 の年齢別出生率（女性人口千対、小数1桁）
- data/processed/women_by_age.csv   ：year, a15..a45（人）, source（estimate=人口推計 千人単位を人に, census2025=国勢調査不詳補完値, implied=出生数÷出生率）
"""
import pathlib, re, warnings
import pandas as pd
warnings.filterwarnings("ignore")
B = pathlib.Path(__file__).resolve().parents[1]
R, P = B / "data" / "raw", B / "data" / "processed"
P.mkdir(parents=True, exist_ok=True)
AG = ["a15", "a20", "a25", "a30", "a35", "a40", "a45"]
num = lambda s: float(str(s).replace(",", "")) if re.match(r"^-?[\d,\.]+$", str(s).strip()) else None

# ---- IPSS 表4-7：出生数（実数）と率
txt = (R / "ipss_2026_T04.txt").read_text()
sec = txt.split("### T04-07_1")[1].split("###")[0].splitlines()
births, rates, mode = [], [], None
for line in sec:
    cells = [c.strip() for c in line.split("\t") if c.strip() != ""]
    if not cells:
        continue
    if cells[0].startswith("実"):
        mode = "b"; continue
    if cells[0].startswith("率"):
        mode = "r"; continue
    if re.match(r"^\d{4}$", cells[0]) and mode:
        vals = [c for c in cells[1:] if c not in ("2)",)]
        vals = [num(v) for v in vals]
        if len(vals) == 8 and all(v is not None for v in vals):
            row = {"year": int(cells[0]), "total": vals[0], **dict(zip(AG, vals[1:]))}
            (births if mode == "b" else rates).append(row)
bi = pd.DataFrame(births); ri = pd.DataFrame(rates)
assert bi.year.is_unique and ri.year.is_unique and len(bi) == len(ri)

# ---- 2025：厚労省 確定数 第6表（14歳以下・50歳以上を含めて並べ直す）
x = pd.ExcelFile(R / "mhlw_kakutei25_06_hyoR07.xlsx")
t6 = pd.read_excel(x, "第６表", header=None)
lab = t6[1].astype(str).str.replace(r"\s", "", regex=True)
hdr = t6.iloc[6].astype(str).tolist()
c25 = [i for i, h in enumerate(hdr) if "７年（'25）" in h.replace(" ", "")][0]
c24 = [i for i, h in enumerate(hdr) if "６年（'24）" in h.replace(" ", "")][0]
def pick(col, key):
    i = lab[lab.str.startswith(key)].index[0]; v = t6.iat[i, col]
    return 0.0 if str(v).strip() in ("-", "nan") else float(v)
def mh(col):
    d = {"total": pick(col, "総数")}
    for k, a in zip(["15～19", "20～24", "25～29", "30～34", "35～39", "40～44", "45～49"], AG):
        d[a] = pick(col, k)
    d["a15"] += pick(col, "14歳以下"); d["a45"] += pick(col, "50歳以上")
    return d
m24, m25 = mh(c24), mh(c25)
# 2024 は IPSS と厚労省の値がそろうことを確かめる（IPSS 表4-7は14歳以下・50歳以上を含めた値）
b24 = bi[bi.year == 2024].iloc[0]
for a in AG + ["total"]:
    assert abs(b24[a] - m24[a]) < 0.5, (a, b24[a], m24[a])
bi = pd.concat([bi, pd.DataFrame([{"year": 2025, **m25}])], ignore_index=True)
bi["source"] = ["ipss_T04-07"] * (len(bi) - 1) + ["mhlw_kakutei2025_T6"]
bi.rename(columns={"total": "total_all"}).to_csv(P / "births_by_age.csv", index=False)
ri.to_csv(P / "asfr_ipss.csv", index=False)

# ---- 女性人口：人口推計（日本人・女、千人）
rows = []
xt = pd.ExcelFile(R / "estat_pop_t3_2000_2020.xlsx")
for sh in [s for s in xt.sheet_names if s.startswith("日本人人口") and "女" in s and "男女" not in s]:
    df = pd.read_excel(xt, sh, header=None)
    yr_row = [i for i in range(20) if any(re.match(r"^20\d\d", str(v)) for v in df.iloc[i].tolist())][0]
    yrs = {j: int(str(v)[:4]) for j, v in enumerate(df.iloc[yr_row].tolist()) if re.match(r"^20\d\d", str(v))}
    lab0 = df[0].astype(str).str.replace(r"\s", "", regex=True)
    for j, y in yrs.items():
        d = {"year": y}
        for k, a in zip(["15～19", "20～24", "25～29", "30～34", "35～39", "40～44", "45～49"], AG):
            i = lab0[lab0.str.startswith(k)].index[0]; d[a] = float(df.iat[i, j]) * 1000
        rows.append(d)
for y in [2021, 2022, 2023, 2024]:
    df = pd.read_excel(R / f"estat_pop_y{y}.xlsx", header=None)
    h = [i for i in range(15) if "時間軸コード" in [str(v) for v in df.iloc[i].tolist()]][0]
    cols = [str(v) for v in df.iloc[h].tolist()]
    r = df[(df.iloc[:, cols.index("人口区分")].astype(str) == "日本人人口") & (df.iloc[:, cols.index("地域")].astype(str).str.strip() == "全国")
           & (df.iloc[:, cols.index("性別")].astype(str) == "女")].iloc[0]
    d = {"year": y}
    for k, a in zip(["15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳"], AG):
        d[a] = float(r.iloc[cols.index(k)]) * 1000
    rows.append(d)
wp = pd.DataFrame(rows).drop_duplicates("year", keep="last").sort_values("year")  # 2015 は2つの表に重複（同じ値）
wp["source"] = "estimate"
# 2025：諸率の算出に用いた人口（国勢調査 不詳補完値、人）
pp = pd.read_excel(x, "人口", header=None)
lab1 = pp[1].astype(str).str.replace(r"\s", "", regex=True)
d = {"year": 2025}
for k, a in zip(["15～19", "20～24", "25～29", "30～34", "35～39", "40～44", "45～49"], AG):
    i = lab1[lab1 == k].index[0]; d[a] = float(pp.iat[i, 4])
d["source"] = "census2025"
single = pp[[7, 8]].dropna(); single = single[single[7].astype(str).str.strip().str.match(r"^\d+歳?$")]
assert abs(single[8].astype(float).sum() - sum(d[a] for a in AG)) < 1, "2025 各歳と5歳階級の合計が合わない"
wp = pd.concat([wp, pd.DataFrame([d])], ignore_index=True)
# 逆算：出生数 ÷ 出生率（千対）
imp = bi.merge(ri, on="year", suffixes=("_b", "_r"))
wi = pd.DataFrame({"year": imp.year, **{a: imp[a + "_b"] / imp[a + "_r"] * 1000 for a in AG}}); wi["source"] = "implied"
pd.concat([wp, wi], ignore_index=True).to_csv(P / "women_by_age.csv", index=False)
print(bi.tail(3).to_string()); print(wp.tail(4).to_string()); print(len(bi), len(ri), len(wp), len(wi))
