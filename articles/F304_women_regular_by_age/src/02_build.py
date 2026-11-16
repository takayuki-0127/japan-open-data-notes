"""労働力調査の2つの表から、年×性×年齢（5歳階級）の人口・雇用形態別雇用者数の表を作る（オフライン）。
出力：data/emptype_age_sex.csv"""
import pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
recs = []
for sheet, sex in (("男女計", "all"), ("男", "male"), ("女", "female")):
    v = pd.read_excel(RAW / "lfs_detail_10-2_emptype_by_age5.xlsx", sheet_name=sheet, header=None)
    blocks = []
    for j in range(2, v.shape[1]):
        lab = v.iloc[6, j]
        if isinstance(lab, str) and lab.strip():
            name = lab.replace("　", " ").split()[0]
            if "（" in lab or "(" in lab:
                continue
            blocks.append((j, name))
    for i in range(16, len(v)):
        m = re.search(r"(\d{4})", str(v.iloc[i, 1]))
        if not m:
            continue
        y = int(m.group(1))
        for j, name in blocks:
            g = lambda k: pd.to_numeric(v.iloc[i, j + k], errors="coerce")
            recs.append(dict(year=y, sex=sex, age=name, employed=g(0), employees=g(1), employees_ex_exec=g(2), regular=g(3), nonregular=g(4)))
e = pd.DataFrame(recs)
# 人口
pop = []
cols = {3: "15～19歳", 4: "20～24歳", 5: "25～29歳", 6: "30～34歳", 7: "35～39歳", 8: "40～44歳", 9: "45～49歳", 10: "50～54歳",
        11: "55～59歳", 12: "60～64歳", 13: "65歳以上", 14: "65～69歳", 15: "70～74歳", 16: "75歳以上", 2: "総数"}
for sheet, sex in (("総数", "all"), ("男", "male"), ("女", "female")):
    v = pd.read_excel(RAW / "lfs_basic_3-1_population_by_age5.xlsx", sheet_name=sheet, header=None)
    for i in range(9, len(v)):
        y = v.iloc[i, 1]
        if isinstance(y, (int, float)) and not pd.isna(y) and 2002 <= int(y) <= 2025:
            for j, a in cols.items():
                pop.append(dict(year=int(y), sex=sex, age=a, population=pd.to_numeric(v.iloc[i, j], errors="coerce")))
p = pd.DataFrame(pop)
d = e.merge(p, on=["year", "sex", "age"], how="left").sort_values(["sex", "age", "year"]).reset_index(drop=True)
d.to_csv(DATA / "emptype_age_sex.csv", index=False)
print(sorted(d.age.unique()), d.year.min(), d.year.max(), d.population.isna().sum())
