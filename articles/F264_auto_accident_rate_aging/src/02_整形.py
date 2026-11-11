"""F264 02 整形：年齢層×年の 10万人当たり件数・件数・免許保有者数（件数÷率で戻す）の長い表を作る。"""
import csv, json, pathlib, re
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = BASE / "data" / "raw", BASE / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
AGES = ["16～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳",
        "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳", "75～79歳", "80～84歳", "85歳以上"]


def read_table(name):
    rows = list(csv.reader(open(RAW / f"{name}.csv", encoding="utf-8")))
    yrow = next(r for r in rows if r and r[0] == "西暦（暦年）")
    years = []
    for c in yrow[1:]:
        if c and c not in years:
            years.append(c)
    years = [int(y) for y in years]
    n = len(years)
    rec, extra = {}, {}
    for r in rows:
        lab = (r[0] if r else "").strip()
        if lab in AGES or lab == "合計":
            vals = [float(x) if re.fullmatch(r"-?[\d.]+", x.strip()) else None for x in r[1:1 + n]]
            rec[lab] = dict(zip(years, vals))
            # 表3-1-1 の最後の2列は最新年の免許保有者数・構成率
            if name.startswith("rate"):
                tail = [x.strip() for x in r[1 + n:] if x.strip() != ""]
                if len(tail) >= 5:
                    extra[lab] = float(tail[3])
    return years, rec, extra


def build(kind):
    parts, checks = [], []
    for ed in ["2019ed", "2025ed"]:
        yr, rate, lic_last = read_table(f"rate_{kind}_{ed}")
        _, cnt, _ = read_table(f"cnt_{kind}_{ed}")
        for a in AGES + ["合計"]:
            for y in yr:
                r, c = rate[a][y], cnt[a][y]
                parts.append(dict(kind=kind, edition=ed, year=y, age=a, rate=r, count=c,
                                  lic=(c / r * 1e5) if (r and c is not None) else None))
            if a in lic_last:
                checks.append(dict(kind=kind, edition=ed, year=yr[-1], age=a, lic_table=lic_last[a]))
    df = pd.DataFrame(parts)
    return df, pd.DataFrame(checks)


if __name__ == "__main__":
    alls, chks = [], []
    for k in ["all", "fatal"]:
        d, c = build(k)
        alls.append(d); chks.append(c)
    long = pd.concat(alls, ignore_index=True)
    chk = pd.concat(chks, ignore_index=True)
    long.to_csv(OUT / "police_age_year_long.csv", index=False)
    # 2つの版をつなぐ：2009〜2014 は 2019年版、2015〜2025 は 2025年版
    main = long[((long.edition == "2019ed") & (long.year <= 2014)) | ((long.edition == "2025ed") & (long.year >= 2015))]
    main.to_csv(OUT / "police_age_year_main.csv", index=False)
    # 照合：戻した保有者数と表の保有者数
    m = chk.merge(long[["kind", "edition", "year", "age", "lic"]], on=["kind", "edition", "year", "age"])
    m["rel_diff"] = m.lic / m.lic_table - 1
    m.to_csv(OUT / "check_licensees.csv", index=False)
    # 保険：自賠責の収支の推移
    rows = list(csv.reader(open(RAW / "giroj_jibaiseki_t1.csv", encoding="utf-8")))
    ins = []
    for r in rows:
        if r and re.fullmatch(r"\d{4}", r[0].strip()):
            f = lambda x: float(x) if x not in ("", None) else None
            ins.append(dict(fy=int(r[0]), contracts=f(r[1]), death_n=f(r[5]), injury_n=f(r[7]), paid_n=f(r[9])))
    ins = pd.DataFrame(ins)
    ins["freq_per_10k"] = ins.paid_n / ins.contracts * 1e4
    ins.to_csv(OUT / "giroj_jibaiseki_freq.csv", index=False)
    t17 = json.load(open(RAW / "giroj_nini_t17_totals.json", encoding="utf-8"))
    nn = []
    for t in t17:
        fy = int(re.search(r"<(\d{4})年度>", t["title"]).group(1))
        tot = t["total"]
        nn.append(dict(fy=fy, contracts=tot[3], premium_k=tot[4], paid_n=tot[5], paid_k=tot[6]))
    nn = pd.DataFrame(nn).sort_values("fy")
    nn["freq_per_10k"] = nn.paid_n / nn.contracts * 1e4
    nn.to_csv(OUT / "giroj_nini_freq.csv", index=False)
    print(main.groupby(["kind"]).year.agg(["min", "max", "count"]))
    print(m[["kind", "edition", "age", "rel_diff"]].assign(rel_diff=lambda x: x.rel_diff.round(4)).to_string())
    print(ins.tail(12).to_string())
    print(nn.to_string())
