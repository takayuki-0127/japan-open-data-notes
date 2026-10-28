"""F83 02 整形：産業×年のパネル（名目GDP、実質GDP（2020年価格に換算）、就業者、労働時間）"""
import csv, io, json
import pandas as pd
from common import RAW, DATA, YEARS, MAJOR, MFG, norm, num

d = json.load(open(RAW, encoding="utf-8"))
NAMES = set(MAJOR + MFG)
rows = []

# 名目：暦年ごとのシート。列3が国内総生産（生産者価格表示）
for sh, txt in d["2024s2n_jp.xlsx"].items():
    lines = list(csv.reader(io.StringIO(txt)))
    yr = None
    for l in lines[:6]:
        for c in l:
            if "暦年" in c and "(" in c:
                yr = int(c.split("(")[1][:4])
    seen = set()
    for l in lines:
        if not l or not l[0]:
            continue
        n = norm(l[0])
        if n in NAMES and n not in seen:
            seen.add(n)
            rows.append(dict(year=yr, ind=n, var="nom", val=num(l[3])))
        if n == "経済活動計" and "nom_total" not in seen:
            seen.add("nom_total")
            rows.append(dict(year=yr, ind="経済活動計", var="nom", val=num(l[3])))

# 実質（連鎖、2020=100）：年ごとに 産出額・中間投入・国内総生産 の3列
lines = list(csv.reader(io.StringIO(d["2024s2rn_jp.xlsx"]["実質(連鎖方式)"])))
hdr = next(l for l in lines if any("暦年" in c and "(" in c for c in l))
ycol = {}
for j, c in enumerate(hdr):
    if "暦年" in c and "(" in c:
        ycol[int(c.split("(")[1][:4])] = j + 1  # 年の見出しは中間投入の列の上。国内総生産はその右
seen = set()
for l in lines:
    if not l or not l[0]:
        continue
    n = norm(l[0])
    if (n in NAMES or n == "経済活動計") and n not in seen:
        seen.add(n)
        for y, j in ycol.items():
            rows.append(dict(year=y, ind=n, var="ridx", val=num(l[j])))


def emp_sheet(name, var):
    lines = list(csv.reader(io.StringIO(d["2024s3_jp.xlsx"][name])))
    yl = next(l for l in lines if l and l[1:3] == ["1994", "1995"])
    cols = {int(c): j for j, c in enumerate(yl) if c.isdigit()}
    seen = set()
    for l in lines:
        if not l or not l[0]:
            continue
        n = norm(l[0])
        if n == "合計":
            n = "経済活動計"
        if (n in NAMES or n == "経済活動計") and n not in seen:
            seen.add(n)
            for y, j in cols.items():
                rows.append(dict(year=y, ind=n, var=var, val=num(l[j])))


emp_sheet("暦年（１）就業者", "emp")       # 万人
emp_sheet("暦年（３）労働時間数", "hours")  # 雇用者1人当たり年間（時間）

df = pd.DataFrame(rows).pivot_table(index=["ind", "year"], columns="var", values="val").reset_index()
# 実質GDP（2020年価格、10億円）＝ 2020年の名目 × 指数/100
n20 = df[df.year == 2020].set_index("ind")["nom"]
df["real"] = df["ind"].map(n20) * df["ridx"] / 100
df["level"] = df["ind"].map(lambda x: "total" if x == "経済活動計" else ("major" if x in MAJOR else "mfg"))
df = df[df.year.isin(YEARS)].sort_values(["level", "ind", "year"])
df.to_csv(DATA / "panel.csv", index=False, encoding="utf-8")
print(df.groupby("level").ind.nunique())
print(df[df.year.isin([1994, 2024]) & (df.level == "total")])
chk = df[df.level == "major"].groupby("year")[["nom", "emp"]].sum().join(
    df[df.level == "total"].set_index("year")[["nom", "emp"]], rsuffix="_tot")
print(chk.loc[[1994, 2008, 2024]])
