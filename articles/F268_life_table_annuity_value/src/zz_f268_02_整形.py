"""02 整形：簡易生命表（厚生労働省）の各歳の qx を取り出し、JMD の死亡率を写す。"""
import re
import numpy as np
import pandas as pd
from common import RAW, DATA, SEXES


def parse_mhlw(path):
    """各シート（男・女）から 0〜105歳の qx・lx・ex を取り出す。
    年によって表の形が違う（2019年は左右2段組み）ので、
    「年齢が整数・qx が数」の行を左から順に拾う。週・月の行は捨てる。"""
    x = pd.ExcelFile(path)
    out = []
    for sh in x.sheet_names:
        sex = "男" if "男" in sh else "女"
        d = pd.read_excel(path, sheet_name=sh, header=None)
        # 年齢・qx・lx・…・ex の並びの開始列を探す：「年齢」の見出しのある列
        starts = []
        for r in range(min(8, len(d))):
            for c in range(d.shape[1]):
                if str(d.iat[r, c]).strip() == "年齢":
                    starts.append(c)
        starts = sorted(set(starts))
        rows = []
        for c0 in starts:
            # その段の数値の列（年齢の右側で、数値が多い列）を順に取る
            block_end = next((s for s in starts if s > c0), d.shape[1])
            numcols = []
            for c in range(c0 + 1, block_end):
                col = pd.to_numeric(d.iloc[5:, c], errors="coerce")
                if col.notna().sum() >= 20:
                    numcols.append(c)
            qc, lc, ec = numcols[0], numcols[1], numcols[-1]
            phase = "pre"
            for r in range(3, len(d)):
                lab = d.iat[r, c0]
                lab2 = d.iat[r, c0 + 1] if c0 + 1 < d.shape[1] else None
                s = str(lab).strip()
                s2 = str(lab2).strip() if lab2 is not None else ""
                if s.endswith("週") or s.endswith("月") or "（週）" in s2 or "（月）" in s2:
                    phase = "sub"; continue
                m = re.fullmatch(r"(\d+)(年)?", s.replace(".0", ""))
                if not m:
                    continue
                age = int(m.group(1))
                if "（年）" in s2 or s.endswith("年"):
                    phase = "year"
                if phase == "sub":
                    # 2014・2019年の表では、週・月の行の年齢は「2」「3」「6」のように数字だけ
                    continue
                q = pd.to_numeric(d.iat[r, qc], errors="coerce")
                l = pd.to_numeric(d.iat[r, lc], errors="coerce")
                e = pd.to_numeric(d.iat[r, ec], errors="coerce")
                if pd.isna(q):
                    continue
                rows.append((age, float(q), float(l), float(e)))
        t = pd.DataFrame(rows, columns=["age", "qx", "lx", "ex"]).drop_duplicates("age").sort_values("age")
        t.insert(0, "sex", sex)
        out.append(t)
    return pd.concat(out, ignore_index=True)


if __name__ == "__main__":
    res = []
    for y, f in [(2014, "mhlw_kani_2014.xls"), (2019, "mhlw_kani_2019.xlsx"), (2024, "mhlw_kani_2024.xlsx")]:
        t = parse_mhlw(RAW / f)
        t.insert(0, "year", y)
        for sex in SEXES:
            ages = t[t.sex == sex].age.tolist()
            assert ages == list(range(0, 106)), (y, sex, ages[:5], ages[-5:], len(ages))
        res.append(t)
    mh = pd.concat(res, ignore_index=True)
    mh.to_csv(DATA / "mhlw_qx.csv", index=False)
    print(mh.groupby(["year", "sex"]).size())
    print(mh[mh.age.isin([0, 65, 105])].to_string())

    jmd = pd.read_csv(RAW / "jmd_mx_long_from_F86.csv")
    jmd = jmd[jmd.year >= 1960][["sex", "year", "age", "mx", "deaths", "exposure"]]
    jmd.to_csv(DATA / "jmd_mx.csv", index=False)
    print("JMD", jmd.year.min(), jmd.year.max(), jmd.age.max(), len(jmd))
