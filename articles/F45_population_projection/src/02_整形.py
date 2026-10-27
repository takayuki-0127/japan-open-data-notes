"""社人研「日本の地域別将来推計人口」の Excel（2013・2018・2023年推計）を、扱いやすい CSV に直す。

出力（data/）
  pop_2023.csv, pop_2018.csv : 都道府県・市区町村 × 年 × 男女 の5歳階級別人口（a0, a1, …）
  surv_2023.csv, surv_2018.csv, nmig_2023.csv, nmig_2018.csv : 期間 × 男女 の生残率・純移動率（r0, r1, …）
  cwr_2023.csv, cwr_2018.csv : 年ごとの子ども女性比と0～4歳性比
  pop_2013_pref.csv, surv_2013_pref.csv, nmig_2013_pref.csv, cwr_2013_pref.csv : 2013年推計（都道府県のみ）
"""
import re
import numpy as np
import pandas as pd
from common import RAW, DATA


def clean_code(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def year_of(x):
    m = re.findall(r"(\d{4})", str(x))
    return "→".join(m) if m else None


def wide_pop(path, header_row, nage, male_col, female_col, vintage):
    d = pd.read_excel(path, header=None)
    d = d.iloc[header_row + 1:]
    d = d[d[0].map(clean_code).notna()]
    rows = []
    for _, r in d.iterrows():
        base = dict(code=clean_code(r[0]), kind=str(r[1]), pref=r[2],
                    muni=(r[3] if isinstance(r[3], str) else ""), year=int(year_of(r[4])))
        for sex, c0 in (("M", male_col), ("F", female_col)):
            vals = pd.to_numeric(r[c0:c0 + nage], errors="coerce").to_numpy(float)
            rows.append({**base, "sex": sex, **{f"a{i}": v for i, v in enumerate(vals)}})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / f"pop_{vintage}.csv", index=False)
    return out


def wide_rate(path, header_row, nrate, male_col, female_col, name, vintage):
    d = pd.read_excel(path, header=None)
    d = d.iloc[header_row + 1:]
    d = d[d[0].map(clean_code).notna()]
    rows = []
    for _, r in d.iterrows():
        base = dict(code=clean_code(r[0]), kind=str(r[1]), pref=r[2],
                    muni=(r[3] if isinstance(r[3], str) else ""), period=year_of(r[4]))
        for sex, c0 in (("M", male_col), ("F", female_col)):
            vals = pd.to_numeric(r[c0:c0 + nrate], errors="coerce").to_numpy(float)
            rows.append({**base, "sex": sex, **{f"r{i}": v for i, v in enumerate(vals)}})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / f"{name}_{vintage}.csv", index=False)
    return out


def cwr_table(path, header_row, vintage):
    d = pd.read_excel(path, header=None)
    d = d.iloc[header_row + 1:]
    d = d[d[0].map(clean_code).notna()]
    out = pd.DataFrame(dict(code=d[0].map(clean_code), kind=d[1].astype(str), pref=d[2],
                            muni=d[3].where(d[3].map(lambda v: isinstance(v, str)), ""),
                            year=d[4].map(lambda v: int(year_of(v))),
                            cwr=pd.to_numeric(d[5]), sr=pd.to_numeric(d[6])))
    out.to_csv(DATA / f"cwr_{vintage}.csv", index=False)
    return out


def parse_2013():
    """2013年推計：都道府県ごとのシート。90歳以上が最後の階級（19区分）。"""
    pop_rows, s_rows, m_rows, c_rows = [], [], [], []
    xp = pd.ExcelFile(RAW / "shicyoson13_3kekka_suikei_ken.xls")
    xi = pd.ExcelFile(RAW / "shicyoson13_4shihyo_shihyo_ken.xls")
    for sh in xp.sheet_names:
        code = int(sh.split()[0]); pref = sh.split()[1]
        d = xp.parse(sh, header=None)
        for sex, lab in (("M", "男"), ("F", "女")):
            r0 = d.index[d[0].astype(str).str.strip() == lab][0]
            years = [int(year_of(v)) for v in d.iloc[r0, 1:8]]
            block = d.iloc[r0 + 2:r0 + 2 + 19, 1:8].apply(pd.to_numeric).to_numpy(float)
            for j, y in enumerate(years):
                pop_rows.append(dict(code=code, kind="a", pref=pref, muni="", year=y, sex=sex,
                                     **{f"a{i}": block[i, j] for i in range(19)}))
        e = xi.parse(sh, header=None)
        for sex, lab in (("M", "男"), ("F", "女")):
            rs = e.index[e[0].astype(str).str.strip() == f"生残率・{lab}"][0]
            periods = [year_of(v) for v in e.iloc[rs + 1, 1:7]]
            sv = e.iloc[rs + 2:rs + 2 + 18, 1:7].apply(pd.to_numeric).to_numpy(float)
            mv = e.iloc[rs + 2:rs + 2 + 18, 9:15].apply(pd.to_numeric).to_numpy(float)
            for j, p in enumerate(periods):
                s_rows.append(dict(code=code, kind="a", pref=pref, muni="", period=p, sex=sex,
                                   **{f"r{i}": sv[i, j] for i in range(18)}))
                m_rows.append(dict(code=code, kind="a", pref=pref, muni="", period=p, sex=sex,
                                   **{f"r{i}": mv[i, j] for i in range(18)}))
        # 子ども女性比・0～4歳性比（シート下部：ラベルの行・年の行・値の行）
        rc = e.index[e[0].astype(str).str.contains("子ども女性比")][0]
        years = [int(year_of(v)) for v in e.iloc[rc + 1, 1:7]]
        cw = pd.to_numeric(e.iloc[rc + 2, 1:7]).to_numpy(float)
        srv = pd.to_numeric(e.iloc[rc + 2, 9:15]).to_numpy(float)
        for y, a, b in zip(years, cw, srv):
            c_rows.append(dict(code=code, kind="a", pref=pref, muni="", year=y, cwr=a, sr=b))
    pd.DataFrame(pop_rows).to_csv(DATA / "pop_2013_pref.csv", index=False)
    pd.DataFrame(s_rows).to_csv(DATA / "surv_2013_pref.csv", index=False)
    pd.DataFrame(m_rows).to_csv(DATA / "nmig_2013_pref.csv", index=False)
    pd.DataFrame(c_rows).to_csv(DATA / "cwr_2013_pref.csv", index=False)


def census2025():
    """令和7年国勢調査（不詳補完値）第2-7表：市区町村の男女・5歳階級別人口。95歳以上は95～99歳と100歳以上の合計。"""
    d = pd.read_excel(RAW / "census2025_age5_000040506659.xlsx", header=None, skiprows=12, dtype=str)
    d = d[(d[0] == "0_国籍総数") & d[1].isin(["1_男", "2_女"])]
    d = d[d[2].isin(["a", "1", "0", "2", "3"]) & ~d[8].astype(str).str.contains("旧")]
    rows = []
    for _, r in d.iterrows():
        v = pd.to_numeric(r[10:31], errors="coerce").fillna(0).to_numpy(float)
        ages = list(v[:19]) + [v[19] + v[20]]
        rows.append(dict(code=int(r[7]), kind=r[2], pref=str(r[6]).split("_")[1],
                         muni=str(r[8]).split("_", 1)[1], year=2025,
                         sex="M" if r[1] == "1_男" else "F", **{f"a{i}": x for i, x in enumerate(ages)}))
    out = pd.DataFrame(rows)
    out.loc[out.kind == "a", "muni"] = ""
    out["code"] = out.code.where(out.kind != "a", out.code)  # 都道府県は 1000 など（社人研と同じ）
    out.to_csv(DATA / "pop_census2025.csv", index=False)
    return out


if __name__ == "__main__":
    census2025()
    p23 = wide_pop(RAW / "shicyoson23_3kekka_suikei_kekka.xlsx", 4, 20, 28, 50, "2023")
    p18 = wide_pop(RAW / "shicyoson18_3kekka_suikei_kekka.xls", 3, 19, 27, 48, "2018")
    wide_rate(RAW / "shicyoson23_4shihyo_katei_suvr.xlsx", 4, 19, 5, 25, "surv", "2023")
    wide_rate(RAW / "shicyoson23_4shihyo_katei_nmigr.xlsx", 4, 19, 5, 25, "nmig", "2023")
    wide_rate(RAW / "shicyoson18_4shihyo_katei_suvr.xls", 3, 18, 5, 24, "surv", "2018")
    wide_rate(RAW / "shicyoson18_4shihyo_katei_nmigr.xls", 3, 18, 5, 24, "nmig", "2018")
    cwr_table(RAW / "shicyoson23_4shihyo_katei_cwr_0-4sr.xlsx", 4, "2023")
    cwr_table(RAW / "shicyoson18_4shihyo_katei_cwr_0-4sr_revised180621.xls", 3, "2018")
    parse_2013()
    print("2023:", p23.groupby("kind").code.nunique().to_dict())
    print("2018:", p18.groupby("kind").code.nunique().to_dict())
