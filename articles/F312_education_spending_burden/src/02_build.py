"""家計調査 第4-6表（2002〜2025年）から、年×年齢×項目の表を作る（オフライン）。
出力：data/edu_by_age.csv、data/cpi_edu_annual.csv"""
import glob, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
CODES = {"8": "education", "8.1": "tuition", "8.2": "textbooks", "8.3": "cram"}
def key_of(code, name):
    name = name.replace(" ", "").replace("　", "")
    if code in CODES: return CODES[code]
    if name.startswith("世帯数分布"): return "hh_weight"
    if name.startswith("世帯人員"): return "hh_size"
    if name.startswith("18歳未満人員"): return "children"
    if name == "消費支出": return "consumption"
    return None
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_4-6_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    v = list(pd.read_excel(f, sheet_name=None, header=None).values())[0]
    S = lambda i, j: str(v.iloc[i, j]).strip() if pd.notna(v.iloc[i, j]) else ""
    if y <= 2019:
        ages = {S(7, j): j for j in range(11, v.shape[1], 4) if S(7, j) in AGES}
        assert list(ages) == AGES, (y, ages)
        for i in range(v.shape[0]):
            c7, c8 = S(i, 7), S(i, 8)
            k = CODES.get(c7) or key_of("", c7) or (key_of("", c8) if c7 == "" else None)
            if k is None: continue
            for a, j in ages.items():
                recs.append(dict(year=y, item=k, age=a, amount=pd.to_numeric(v.iloc[i, j], errors="coerce")))
    else:
        cols = {S(8, j): j for j in range(13, v.shape[1])}
        for i in range(v.shape[0]):
            k = key_of(S(i, 10), S(i, 11))
            if k is None: continue
            for a in AGES:
                recs.append(dict(year=y, item=k, age=a, amount=pd.to_numeric(v.iloc[i, cols[f"{a}・支出金額"]], errors="coerce")))
d = pd.DataFrame(recs).drop_duplicates(["year", "item", "age"], keep="first").sort_values(["item", "year", "age"]).reset_index(drop=True)
d.to_csv(DATA / "edu_by_age.csv", index=False)
t = pd.read_csv(RAW / "cpi_middle_class_index.csv", encoding="cp932", header=None, dtype=str)
h = t.iloc[0].tolist()
b = t.iloc[5:]; b = b[b[0].str.fullmatch(r"\d{6}")]
c = pd.DataFrame({"ym": b[0].astype(int)})
for nm, k in [("教育", "cpi_edu"), ("授業料等", "cpi_tuition"), ("補習教育", "cpi_cram"), ("総合", "cpi_all")]:
    c[k] = pd.to_numeric(b[h.index(nm)], errors="coerce").values
c["year"] = c.ym // 100
ca = c.groupby("year").agg(n=("cpi_edu", "count"), cpi_edu=("cpi_edu", "mean"), cpi_tuition=("cpi_tuition", "mean"), cpi_cram=("cpi_cram", "mean"), cpi_all=("cpi_all", "mean")).reset_index()
ca = ca[(ca.n == 12) & (ca.year >= 2002)].drop(columns="n")
ca.round(4).to_csv(DATA / "cpi_edu_annual.csv", index=False)
print(d.groupby("item").agg(n=("year", "count"), y0=("year", "min"), y1=("year", "max"), na=("amount", lambda s: s.isna().sum())))
