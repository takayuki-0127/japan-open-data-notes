"""国勢調査2020（都道府県×男女×各歳の労働力状態）と賃金構造基本統計調査2020（都道府県×男女×年齢階級の所定内給与額）を、
都道府県×男女×5歳階級（20〜64歳）のセルにそろえ、都道府県の説明変数（SSDSE-B 2020）を付ける。"""
import json, re, unicodedata
import numpy as np, pandas as pd
from common import RAW, DATA, AGES

# --- 国勢調査：就業状態 ---
rows = [r for r in json.load(open(RAW/"census2020_pref_lfs.json"))["rows"] if r and r[0] == "a"]
recs = []
for r in rows:
    pref = r[1].split("_")[1]
    if pref == "全国":
        continue
    sex = r[3].split("_")[1]
    m = re.match(r"\d+_(\d+)歳", r[4])
    if sex == "総数" or not m:
        continue
    age = int(m.group(1))
    if not 20 <= age <= 64:
        continue
    lo = (age // 5) * 5
    recs.append(dict(pref=pref, sex=sex, age=f"{lo}-{lo+4}", pop=r[5], emp=r[7], main=r[8], unk=r[17]))
c = pd.DataFrame(recs).groupby(["pref","sex","age"], as_index=False)[["pop","emp","main","unk"]].sum()
c["known"] = c["pop"] - c["unk"]
c["p_emp"] = c["emp"] / c["known"]      # 就業率（不詳を除く）
c["p_main"] = c["main"] / c["known"]    # 「主に仕事」の割合（家事のかたわら等を除く）
c["pref_s"] = c["pref"].str.replace(r"(都|府|県)$", "", regex=True).replace({"北海道": "北海道"})

# --- 賃金構造基本統計調査 ---
w = pd.read_csv(RAW/"wage2020_pref.tsv", sep="\t")
def agelab(s):
    s = unicodedata.normalize("NFKC", str(s))
    m = re.match(r"(\d+)~(\d+)歳", s)
    return f"{m.group(1)}-{m.group(2)}" if m else None
w["age"] = w["age"].map(agelab)
w = w[w["sex"].isin(["男","女"]) & w["age"].isin(AGES)].copy()
w["wage"] = w["shoteinai_kyuyo_k"].astype(float)   # 千円／月
w["workers"] = w["workers_10"].astype(float) * 10
w = w.rename(columns={"pref":"pref_s"})[["pref_s","sex","age","wage","workers"]]

cell = c.merge(w, on=["pref_s","sex","age"], how="inner")
assert len(cell) == 47*2*9, len(cell)

# --- 都道府県の変数（SSDSE-B 2020年度） ---
b = pd.read_csv(RAW/"SSDSE-B-2026.csv", encoding="cp932", skiprows=[1])
b = b[b["SSDSE-B-2026"] == 2020].copy()
b["pref"] = b["Prefecture"]
num = lambda s: pd.to_numeric(s, errors="coerce")
pv = pd.DataFrame({"pref": b["pref"]})
pv["log_pop"] = np.log(num(b["A1101"]))
pv["jobs_ratio"] = num(b["F3103"]) / num(b["F3102"])                       # 有効求人倍率（一般）
pv["univ_rate"] = num(b["E4602"]) / num(b["E4601"])                         # 高校卒業者の進学率
pv["cap_per_child"] = num(b["J2505"]) / num(b["A1301"])                     # 保育所等定員／15歳未満人口
pv["enroll_per_child"] = num(b["J2506"]) / num(b["A1301"])                  # 保育所等在所児／15歳未満人口
pv["tfr"] = num(b["A4103"])                                                 # 合計特殊出生率
pv["wait_per_cap"] = num(b["J250502"]) / num(b["J2505"])                    # 待機児童／定員
mw = pd.read_csv(RAW/"minimum_wage_2002_2026.csv")
mw["pref_s"] = mw["pref"]
pv["pref_s"] = pv["pref"].str.replace(r"(都|府|県)$", "", regex=True)
pv = pv.merge(mw[["pref_s","2020"]].rename(columns={"2020":"minwage"}), on="pref_s", how="left")
pv["log_minwage"] = np.log(pv["minwage"])
assert pv["minwage"].notna().all() and len(pv) == 47
cell = cell.merge(pv.drop(columns=["pref_s"]), on="pref", how="left")
cell.to_csv(DATA/"cells.csv", index=False)
pv.to_csv(DATA/"pref_vars.csv", index=False)
print(cell.groupby(["sex","age"])[["p_emp","p_main","wage"]].mean().round(3))
print(pv.describe().round(3).T)
