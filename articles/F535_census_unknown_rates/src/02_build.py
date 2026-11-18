"""data/raw の Excel から、年齢の不詳・配偶関係の不詳の表を作る。
都道府県の名前は「01000_北海道」のような地域名の文字から付ける（行の順には頼らない）。列は見出しの文字で選ぶ。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data"


def area(s):
    m = re.match(r"(\d{5})_(.+)", str(s).strip())
    if not m or not m.group(1).endswith("000"):
        return None, None
    return int(m.group(1)[:2]), m.group(2)


num = lambda v: float(pd.to_numeric(v, errors="coerce"))


# 1. 時系列 第5表（1920〜2020年、全国・都道府県、年齢3区分）
t = pd.read_excel(RAW / "ts05_age3_pref_1920_2020.xlsx", sheet_name=0, header=None)
hdr = t.index[t[0].astype(str).str.startswith("年次")][0]
rows = []
for _, r in t.iloc[hdr + 3:].iterrows():
    y = re.match(r"(\d{4})年", str(r[0]))
    code, name = area(r[2])
    if not y or code is None:
        continue
    rows.append({"year": int(y.group(1)), "pref_code": code, "pref": name,
                 "version": "imputed_2022" if str(r[3]).strip() == "※" else "original",
                 "total": num(r[4]), "a0_14": num(r[5]), "a15_64": num(r[6]), "a65": num(r[7])})
ts = pd.DataFrame(rows)
# 総数に年齢「不詳」を含む年（表の注1による）。それ以外の年は不詳を出さない
INCL = {1940, 1950, 1955, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020}
ts["unknown"] = np.where(ts.year.isin(INCL) & (ts.version == "original"), ts.total - ts.a0_14 - ts.a15_64 - ts.a65, np.nan)


# 2. 2025年（原数値・補完値）と2020年の遡及の補完値（第2-3表）
def t23(path, year, version):
    d = pd.read_excel(path, sheet_name=0, header=None)
    top, lab = d.iloc[5].astype(str), d.iloc[7].astype(str)
    col = lambda a, b: [c for c in d.columns if top[c] == a and lab[c] == b][0]
    C = {"total": col("人口", "00_総数"), "a0_14": col("人口", "R1_（再掲）15歳未満"), "a15_64": col("人口", "R2_（再掲）15～64歳"),
         "a65": col("人口", "R3_（再掲）65歳以上"), "pct65_pub": col("人口構成比［年齢別］", "3_65歳以上"),
         "pct0_14_pub": col("人口構成比［年齢別］", "1_15歳未満")}
    unk = [c for c in d.columns if top[c] == "人口" and "不詳" in lab[c]]
    out = []
    for _, r in d.iloc[11:].iterrows():
        code, name = area(r[3])
        if code is None or str(r[2]).strip() != "a":
            continue
        rec = {"year": year, "pref_code": code, "pref": name, "version": version,
               "nationality": str(r[0]).split("_")[1], "sex": str(r[1]).split("_")[1]}
        for k, c in C.items():
            rec[k] = num(r[c])
        rec["unknown"] = (0.0 if str(r[unk[0]]).strip() == "-" else float(r[unk[0]])) if unk else 0.0
        out.append(rec)
    return pd.DataFrame(out)


r7o = t23(RAW / "r7_t2-3_age_pref_original.xlsx", 2025, "original")
r7i = t23(RAW / "r7_t2-3_age_pref_imputed.xlsx", 2025, "imputed")
r2i = t23(RAW / "r2retro_t2-3_age_pref_imputed.xlsx", 2020, "imputed_2026retro")
detail = pd.concat([r7o, r7i, r2i], ignore_index=True)
detail.to_csv(OUT / "age_2025_2020_detail.csv", index=False, float_format="%.4f", lineterminator="\n")
tot = detail[(detail.nationality == "国籍総数") & (detail.sex == "総数")].drop(columns=["nationality", "sex", "pct65_pub", "pct0_14_pub"])
age = pd.concat([ts, tot], ignore_index=True).sort_values(["year", "version", "pref_code"])
age.to_csv(OUT / "age_unknown.csv", index=False, float_format="%.1f", lineterminator="\n")

# 3. 配偶関係（全国、時系列第4表＋2025年 第4-1表）
t4 = pd.read_excel(RAW / "ts04_marital_national_1920_2020.xlsx", sheet_name=0, header=None)
hdr = t4.index[t4[0].astype(str).str.startswith("年次")][0]
lab = t4.iloc[hdr + 1].astype(str)
cn = {k: [c for c in t4.columns if lab[c] == k][0] for k in ["総数", "未婚", "有配偶", "死別", "離別"]}
rows = []
for _, r in t4.iloc[hdr + 3:].iterrows():
    y = re.match(r"(\d{4})年", str(r[0]))
    if not y or str(r[4]).strip() == "※" or str(r[3]).startswith("（再掲）") or str(r[3]).strip() in ("", "nan", "80歳以上"):
        continue
    v = {k: pd.to_numeric(r[c], errors="coerce") for k, c in cn.items()}
    known = sum(0 if pd.isna(v[k]) else v[k] for k in ["未婚", "有配偶", "死別", "離別"])
    rows.append({"year": int(y.group(1)), "sex": {"男女": "総数"}.get(str(r[2]).strip(), str(r[2]).strip()),
                 "age": str(r[3]).strip(), "total": v["総数"], "unknown": v["総数"] - known if int(y.group(1)) >= 1950 else np.nan})
mar = pd.DataFrame(rows)

d = pd.read_excel(RAW / "r7_t4-1_marital_pref_original.xlsx", sheet_name=0, header=None)
lab = d.iloc[7].astype(str)
agecol = {}
for c in d.columns:
    m = re.match(r"\d+_(\d+)歳(以上)?$", lab[c])
    if m:
        agecol[c] = int(m.group(1))
tot_c = [c for c in d.columns if lab[c] == "00_総数"][0]
h0 = d.index[d[0].astype(str).str.strip() == "地域識別コード"][0]
b = d.iloc[h0 + 1:].copy()
b = b[(b[0].astype(str).str.strip() == "a") & (b[3].astype(str).str.startswith("0_"))]
rows, prow = [], []
for _, r in b.iterrows():
    code, name = area(r[2])
    sex = str(r[4]).split("_")[1]; mk = str(r[5]).split("_", 1)[1]
    if code is None:
        continue
    prow.append({"pref_code": code, "pref": name, "sex": sex, "marital": mk, "n15plus": num(r[tot_c])})
    if code == 0:
        for c, a in agecol.items():
            rows.append({"sex": sex, "marital": mk, "age1": a, "n": num(r[c])})
p25 = pd.DataFrame(prow)
p25w = p25.pivot_table(index=["pref_code", "pref", "sex"], columns="marital", values="n15plus").reset_index()
p25w = p25w.rename(columns={"総数": "total", "配偶関係「不詳」": "unknown"})[["pref_code", "pref", "sex", "total", "unknown"]]
p25w.to_csv(OUT / "marital_unknown_pref_2025.csv", index=False, float_format="%.1f", lineterminator="\n")
n25 = pd.DataFrame(rows)
def grp(a):
    if a >= 85: return "85歳以上"
    lo = a // 5 * 5
    return f"{lo}～{lo+4}歳"
n25["age"] = n25.age1.map(grp)
n25 = n25.pivot_table(index=["sex", "age"], columns="marital", values="n", aggfunc="sum").reset_index()
n25 = pd.DataFrame({"year": 2025, "sex": n25.sex, "age": n25.age, "total": n25["総数"], "unknown": n25["配偶関係「不詳」"]})
nat = p25w[p25w.pref_code == 0]
n25 = pd.concat([n25, pd.DataFrame({"year": 2025, "sex": nat.sex, "age": "総数", "total": nat.total, "unknown": nat.unknown})])
mar = pd.concat([mar, n25], ignore_index=True)
mar.to_csv(OUT / "marital_unknown_national.csv", index=False, float_format="%.1f", lineterminator="\n")
print(age.groupby(["year", "version"]).size().tail(8)); print(mar.groupby("year").size().tail(5)); print(p25w.shape)
