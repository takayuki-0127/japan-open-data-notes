"""data/raw の Excel から、卒業年ごとの表 data/panel.csv を作る。
列は見出しの文字（「大学」「計」、「実数」「年度平均」など）で選ぶ。"""
import json, pathlib, re
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"


def school_rates():
    v = pd.read_excel(RAW / "gakko_shushoku_rate.xlsx", header=None)
    hdr = v.iloc[2:5].fillna("").astype(str)
    def col(school, sex):
        hits = [c for c in v.columns if hdr.iloc[0, c].strip() == school and hdr.iloc[2, c].strip() == sex]
        if len(hits) != 1:
            raise ValueError((school, sex, hits))
        return hits[0]
    ycol = 1
    out = {}
    for r in range(5, len(v)):
        y = v.iloc[r, ycol]
        try:
            y = int(str(y).strip())
        except ValueError:
            continue
        rec = {}
        for school, key in [("大学", "univ"), ("短期大学", "jc")]:
            for sex, sk in [("計", "t"), ("男", "m"), ("女", "f")]:
                x = v.iloc[r, col(school, sex)]
                rec[f"{key}_{sk}"] = float(x) if str(x).strip() not in ("…", "-", "", "nan") else None
        out[y] = rec
    return pd.DataFrame.from_dict(out, orient="index")


def bairitsu(fname, prefix):
    x = pd.read_excel(RAW / fname, header=None, sheet_name=None)
    name = [k for k in x if "パート含む" in k]
    if len(name) != 1:
        raise ValueError(name)
    v = x[name[0]]
    h2 = v.iloc[2].fillna("").astype(str).str.strip(); h3 = v.iloc[3].fillna("").astype(str).str.strip()
    def col(kind, lab):
        hits = [c for c in v.columns if h2[c] == kind and h3[c] == lab]
        if len(hits) != 1:
            raise ValueError((kind, lab, hits))
        return hits[0]
    cfy, ccy = col("実数", "年度平均"), col("実数", "年平均")
    out = {}
    for r in range(5, len(v)):
        m = re.match(r"^(\d{4})年$", str(v.iloc[r, 0]).strip())
        if not m:
            continue
        def f(c):
            try:
                return float(v.iloc[r, c])
            except (TypeError, ValueError):
                return None
        out[int(m.group(1))] = {f"{prefix}_fy": f(cfy), f"{prefix}_cy": f(ccy)}
    return pd.DataFrame.from_dict(out, orient="index")


def main():
    s = school_rates()
    yk = bairitsu("shokuan_yuko_kyujin_bairitsu.xlsx", "yuko")
    sk = bairitsu("shokuan_shinki_kyujin_bairitsu.xlsx", "shinki")
    lab = yk.join(sk, how="outer")
    # 卒業年 t に t-1 年度（と t-1 年、t 年度）の倍率を合わせる
    lab.index.name = "year"
    df = s.copy()
    df.index.name = "grad_year"
    for c in lab.columns:
        df[f"{c}_lag1"] = [lab[c].get(y - 1) for y in df.index]
        df[f"{c}_lag0"] = [lab[c].get(y) for y in df.index]
    df = df.sort_index()
    df.to_csv(BASE / "data" / "panel.csv", float_format="%.4f")
    checks = {"univ_t_2025": df.loc[2025, "univ_t"], "univ_t_2019": df.loc[2019, "univ_t"], "univ_t_2010": df.loc[2010, "univ_t"],
              "univ_t_1950": df.loc[1950, "univ_t"], "jc_t_2025": df.loc[2025, "jc_t"],
              "yuko_fy_2024": lab.loc[2024, "yuko_fy"], "yuko_fy_1963": lab.loc[1963, "yuko_fy"], "shinki_fy_2024": lab.loc[2024, "shinki_fy"],
              "years_rate": [int(df.index.min()), int(df.index.max())], "years_bairitsu": [int(lab.index.min()), int(lab.index.max())]}
    (BASE / "data" / "build_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
