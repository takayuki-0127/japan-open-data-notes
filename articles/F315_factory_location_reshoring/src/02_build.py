"""工場立地動向調査（2025年調査、経年掲載）と為替から分析用の表を作る（オフライン）。
- data/ritchi_by_industry.csv：measure（count, area_1000m2, capex_mil, new_count）× 業種 × 年（2006〜2025）
- data/usdjpy_annual.csv：ドル円の年平均"""
import pathlib, re
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
wb = openpyxl.load_workbook(RAW / "kojo_ritchi_2025.xlsx", read_only=True, data_only=True)
def era(lbl):
    s = str(lbl).replace("　", "").replace(" ", "")
    if s == "元年": return 2019
    n = int(re.match(r"(\d+)年", s).group(1))
    return 1988 + n if n >= 18 else 2018 + n
def clean(nm): return re.sub(r"\(※[^)]*\)", "", str(nm)).replace("　", "").strip()
recs = []
for sheet, measure in [("01", "count"), ("03", "area_1000m2"), ("13", "capex_mil")]:
    R = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
    years = [era(c) for c in R[2][3:23]]
    assert years[0] == 2006 and years[-1] == 2025, (sheet, years)
    for r in R[3:]:
        if r[0] is None and r[1] is None: continue
        if str(r[0]).startswith(("注", "※")): break
        name = "全業種合計" if "全" in str(r[0]) and "合" in str(r[0]) else clean(r[1])
        code = "TOTAL" if name == "全業種合計" else (str(r[0]) if r[0] is not None else "old")
        for y, v in zip(years, r[3:23]):
            recs.append(dict(measure=measure, code=code, name=name, year=y, value=pd.to_numeric(v, errors="coerce")))
R = [list(r) for r in wb["34-1,34-2"].iter_rows(values_only=True)]
starts = [(j, era(c)) for j, c in enumerate(R[2]) if c]
for r in R[6:58]:
    if r[0] is None and r[1] is None: continue
    if str(r[0]).startswith(("注", "※")): break
    name = "全業種合計" if "全" in str(r[0]) and "合" in str(r[0]) else clean(r[1])
    code = "TOTAL" if name == "全業種合計" else (str(r[0]) if r[0] is not None else "old")
    for j, y in starts:
        assert str(R[3][j + 1]).strip() == "新設" and str(R[4][j + 4]).strip() == "合計"
        recs.append(dict(measure="new_count", code=code, name=name, year=y, value=pd.to_numeric(r[j + 4], errors="coerce")))
d = pd.DataFrame(recs)
d.to_csv(DATA / "ritchi_by_industry.csv", index=False)
fx = pd.read_csv(RAW / "boj_usdjpy_monthly.csv")
fx["year"] = fx.ym // 100
fa = fx.groupby("year").agg(usdjpy=("usdjpy", "mean"), n=("usdjpy", "size")).reset_index()
fa = fa[fa.n == 12][["year", "usdjpy"]].round(4)
fa.to_csv(DATA / "usdjpy_annual.csv", index=False)
print(d.groupby("measure").size().to_dict()); print(d[d.code == "TOTAL"].pivot(index="year", columns="measure", values="value").tail(3)); print(fa.tail(3))
