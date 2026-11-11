"""F294 整形: 受給者数・受給率（65歳以上、性・5歳階級）、IPSS人口、費用額の年次を data/processed へ。"""
import pathlib, re
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
AGES = ["65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"]

# 1) 介護給付費等実態統計 図２データ（各年11月審査分）
rec = []
for fy, f in [(2014, "kyufu14_09.xls"), (2019, "kyufu19_09.xlsx"), (2025, "kyufu25_09.xlsx")]:
    df = pd.read_excel(RAW / f, sheet_name="図２データ", header=None)
    lab = df[1].astype(str)
    def row(key):
        i = lab[lab.str.contains(key, regex=False)].index[0]
        return [float(v) for v in df.iloc[i, 2:9]]
    um, uf, rm, rf = row("受給者数：男"), row("受給者数：女"), row("受給者割合：男"), row("受給者割合：女")
    for sex, u, r in [("男", um, rm), ("女", uf, rf)]:
        for a, uu, rr in zip(AGES, u, r):
            rec.append({"fy": fy, "sex": sex, "age": a, "users_k": uu, "rate_pct": rr,
                        "implied_pop_k": uu / rr * 100})
users = pd.DataFrame(rec)
users.to_csv(OUT / "users_rate_65plus.csv", index=False)

# 2) IPSS 令和5年推計 表1/4/7-9A（男女5歳階級、千人）。95-99と100+を足して95+。
def ipss(path):
    out = []
    for sh in pd.ExcelFile(path).sheet_names:
        df = pd.read_excel(path, sheet_name=sh, header=None)
        year = None
        for _, r in df.iterrows():
            c0 = str(r[0])
            m = re.search(r"\((\d{4})\)年", c0)
            if m:
                year = int(m.group(1)); continue
            if year is None:
                continue
            lab = c0.replace("　", "").replace(" ", "").replace("～", "-")
            if lab in ("65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95-99", "100+"):
                a = "95+" if lab in ("95-99", "100+") else lab
                out.append({"year": year, "age": a, "男": float(r[2]), "女": float(r[3])})
    d = pd.DataFrame(out).groupby(["year", "age"], as_index=False).sum()
    return d.melt(id_vars=["year", "age"], var_name="sex", value_name="pop_k")
pops = []
for var, f in [("中位", "ipss_1-9A.xlsx"), ("死亡高位", "ipss_4-9A.xlsx"), ("死亡低位", "ipss_7-9A.xlsx")]:
    d = ipss(RAW / f); d["variant"] = var; pops.append(d)
pop = pd.concat(pops)
pop.to_csv(OUT / "ipss_pop_65plus.csv", index=False)

# 3) 統計表６（kyufu25）: 年度別の年間実受給者数・費用額累計（総数／介護予防／介護）、2001〜2025年度
t6 = pd.read_excel(RAW / "kyufu25_09.xlsx", sheet_name="統計表６", header=None)
ser = []
for _, r in t6.iterrows():
    m = re.search(r"\((\d{4})\)年度", str(r[0]))
    if not m:
        continue
    num = lambda v: float(v) if str(v) not in ("・", "nan") else float("nan")
    ser.append({"fy": int(m.group(1)), "users_all_k": num(r[2]), "cost_all_m": num(r[3]),
                "users_yobo_k": num(r[5]), "cost_yobo_m": num(r[6]),
                "users_kaigo_k": num(r[8]), "cost_kaigo_m": num(r[9])})
ser = pd.DataFrame(ser)
ser.to_csv(OUT / "annual_series.csv", index=False)
# 各年の公表表と突き合わせ（kyufu14 表７、kyufu19 表６、kyufu24/25 表５）
known = {2014: 9303870, 2019: 10509517, 2020: 10778334, 2021: 11029131, 2022: 11191213,
         2023: 11513921, 2024: 11938109, 2025: 12220787}
for fy, v in known.items():
    assert int(ser.set_index("fy").cost_all_m[fy]) == v, fy
t5 = pd.read_excel(RAW / "kyufu25_09.xlsx", sheet_name="表５", header=None)
assert [int(v) for v in t5.iloc[5, 2:7]] == [known[y] for y in range(2021, 2026)]
cost = ser[["fy", "cost_all_m"]].rename(columns={"cost_all_m": "cost_million_yen"})
cost.to_csv(OUT / "cost_total.csv", index=False)
ser[["fy", "users_all_k"]].rename(columns={"users_all_k": "annual_users_k"}).to_csv(OUT / "annual_users.csv", index=False)
# 4) 受給者1人当たり費用額（総数、各年4月審査分、千円）。年は「審査の年」（4月審査分は前年度の3月の利用分）。
cpu = {}
for f, sh, y0 in [("kyufu14_09.xls", "表６", 2011), ("kyufu19_09.xlsx", "表５", 2016),
                  ("kyufu24_09.xlsx", "統計表３", 2021), ("kyufu25_09.xlsx", "統計表３", 2022)]:
    t = pd.read_excel(RAW / f, sheet_name=sh, header=None)
    for i, v in enumerate(t.iloc[5, 1:6]):
        cpu.setdefault(y0 + i, float(v))
pd.DataFrame({"year_of_review": list(cpu), "cost_per_user_k_yen_april": list(cpu.values())}).to_csv(OUT / "cost_per_user.csv", index=False)
print(users.groupby("fy").users_k.sum())
print(pop[pop.year.isin([2025, 2040])].groupby(["variant", "year"]).pop_k.sum())
