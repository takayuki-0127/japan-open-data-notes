"""4都市の転入超過を、同じ地方・東京圏・その他に分け、results/ に書く（オフライン）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
CITY = {"01100": "札幌市", "04100": "仙台市", "34100": "広島市", "40130": "福岡市"}
ORDER = list(CITY)
REGION = {"01100": [1], "04100": list(range(2, 8)), "34100": list(range(31, 36)), "40130": list(range(40, 48))}
OWN = {"01100": 1, "04100": 4, "34100": 34, "40130": 40}
TOKYO = [11, 12, 13, 14]
BIG3 = TOKYO + [21, 23, 24, 26, 27, 28]   # 東京圏＋名古屋圏（岐阜・愛知・三重）＋大阪圏（京都・大阪・兵庫）


def r0(x):
    return int(round(float(x)))


def split(F, nat, years):
    d = F[(F.nat == nat) & (F.year.isin(years))].copy()
    d["net"] = d["in"] - d.out
    out = {}
    for c in ORDER:
        x = d[d.city == c]
        n = len(years)
        reg = x[x.partner.isin(REGION[c])].net.sum() / n
        own = x[x.partner == OWN[c]].net.sum() / n
        tky = x[x.partner.isin(TOKYO)].net.sum() / n
        big3 = x[x.partner.isin(BIG3)].net.sum() / n
        tot = x.net.sum() / n
        out[c] = dict(city=CITY[c], total=tot, region=reg, region_own_pref=own, region_other_pref=reg - own, tokyo=tky,
                      other=tot - reg - tky, big3=big3, in_region=x[x.partner.isin(REGION[c])]["in"].sum() / n)
    return out


def main():
    RES.mkdir(exist_ok=True)
    F = pd.read_csv(ROOT / "data" / "flows.csv", dtype={"city": str})
    A = pd.read_csv(ROOT / "data" / "age_net_2025.csv", dtype={"city": str, "partner": str})
    out = {}
    main_ = split(F, "japanese", [2025])
    out["main_2025_japanese"] = {c: {k: (r0(v) if not isinstance(v, str) else v) for k, v in d.items()} for c, d in main_.items()}
    # 年ごと（日本人移動者）
    rows = []
    for y in range(2014, 2026):
        s = split(F, "japanese", [y])
        for c in ORDER:
            rows.append(dict(year=y, city=CITY[c], **{k: r0(v) for k, v in s[c].items() if k != "city"}))
    Y = pd.DataFrame(rows)
    Y.to_csv(RES / "yearly_japanese.csv", index=False)
    # 年齢（2025年、日本人移動者）
    a = A[(A.nat == "japanese")]
    ages = [x for x in a.age.unique() if x != "総数"]
    age_rows = []
    for c in ORDER:
        x = a[a.city == c]
        reg = x[x.partner.isin([str(p) for p in REGION[c]])].groupby("age").net.sum()
        tky = x[x.partner == "東京圏"].set_index("age").net
        tot = x[x.partner == "全国"].set_index("age").net
        for ag in ages:
            age_rows.append(dict(city=CITY[c], age=ag, total=r0(tot[ag]), region=r0(reg[ag]), tokyo=r0(tky[ag])))
    AG = pd.DataFrame(age_rows)
    AG.to_csv(RES / "age_2025_japanese.csv", index=False)
    t = AG[AG.age.isin(["20歳～24歳", "25歳～29歳"])].tokyo.sum(); tt = AG.tokyo.sum()
    out["tokyo_2029_share"] = round(100 * t / tt, 1)
    out["tokyo_by_age_4cities"] = {ag: int(AG[AG.age == ag].tokyo.sum()) for ag in ages}
    out["region_by_age_4cities"] = {ag: int(AG[AG.age == ag].region.sum()) for ag in ages}
    m = main_
    h1 = all(m[c]["region"] > 0 for c in ORDER); h2 = all(m[c]["tokyo"] < 0 for c in ORDER)
    h3 = sum(m[c]["total"] > 0 for c in ORDER)
    out["hypotheses"] = {
        "H1": dict(value={CITY[c]: r0(m[c]["region"]) for c in ORDER}, verdict="支持" if h1 else "外れ"),
        "H2": dict(value={CITY[c]: r0(m[c]["tokyo"]) for c in ORDER}, verdict="支持" if h2 else "外れ"),
        "H3": dict(value=int(h3), verdict="支持" if h3 >= 3 else "外れ"),
        "H4": dict(value=out["tokyo_2029_share"], verdict="支持" if out["tokyo_2029_share"] >= 50 else "外れ"),
    }
    # 頑健性
    rb = []
    def row(label, s, key="region"):
        return dict(check=label, **{CITY[c]: f"全体 {r0(s[c]['total']):+,}／同じ地方 {r0(s[c]['region']):+,}／東京圏 {r0(s[c]['tokyo']):+,}" for c in ORDER})
    rb.append(row("0 主：2025年、日本人移動者", m))
    rb.append(row("1 2025年、外国人を含む移動者", split(F, "all", [2025])))
    rb.append(row("2 2023〜2025年の3年平均、日本人移動者", split(F, "japanese", [2023, 2024, 2025])))
    rb.append(dict(check="3 同じ地方のうち自分の県（当該都市以外）を除く（2025年）", **{CITY[c]: f"他県から {r0(m[c]['region_other_pref']):+,}（自分の県から {r0(m[c]['region_own_pref']):+,}）" for c in ORDER}))
    rb.append(dict(check="4 東京圏の代わりに3大都市圏（2025年）", **{CITY[c]: f"{r0(m[c]['big3']):+,}" for c in ORDER}))
    pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rb
    # 問い直し：2014〜2016年平均と2023〜2025年平均の比較
    early = split(F, "japanese", [2014, 2015, 2016]); late = split(F, "japanese", [2023, 2024, 2025])
    out["requestion"] = {CITY[c]: {k: [r0(early[c][k]), r0(late[c][k])] for k in ("total", "region", "tokyo", "other", "in_region")} for c in ORDER}
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("main_2025_japanese", "hypotheses", "tokyo_2029_share", "requestion")}, ensure_ascii=False, indent=0))
    print(pd.DataFrame(rb).to_string()); print(AG.pivot(index="age", columns="city", values="tokyo").reindex(ages))


if __name__ == "__main__":
    main()
