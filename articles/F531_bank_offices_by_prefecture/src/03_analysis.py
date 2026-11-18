"""03 分析：全国の推移、都道府県別・地方別の増減、人口あたり、仮説の判定、頑健性。
都道府県は北から南（都道府県コード順）に並べ、少ない順・減り方の順の順位は作らない。
出力：results/national.csv、results/pref_2009_2024.csv、results/region.csv、results/robustness.csv、results/main.json
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
df = pd.read_csv(D / "offices_long.csv", dtype={"pref_code": str, "ind": str})
pop = pd.read_csv(D / "population.csv", dtype={"pref_code": str})
YEARS = [2009, 2014, 2016, 2021, 2024]
REGION = {"北海道": ["01"], "東北": ["02", "03", "04", "05", "06", "07"], "関東": ["08", "09", "10", "11", "12", "13", "14"],
          "中部": ["15", "16", "17", "18", "19", "20", "21", "22", "23"], "近畿": ["24", "25", "26", "27", "28", "29", "30"],
          "中国": ["31", "32", "33", "34", "35"], "四国": ["36", "37", "38", "39"],
          "九州・沖縄": ["40", "41", "42", "43", "44", "45", "46", "47"]}
REG_OF = {c: r for r, cs in REGION.items() for c in cs}
METRO = ["関東", "中部", "近畿"]


def tab(ind, val="offices"):
    t = df[df["ind"] == ind].pivot(index="pref_code", columns="year", values=val)
    return t


def popt():
    return pop.pivot(index="pref_code", columns="year", values="pop_k")


def main():
    P = popt()
    m = {}
    # 全国
    nat = []
    for y in YEARS:
        row = {"year": y, "survey": df[df.year == y]["survey"].iloc[0], "pop_k": float(P.loc["00", y])}
        for ind in ["62", "63"]:
            o = float(tab(ind).loc["00", y]); w = float(tab(ind, "workers").loc["00", y])
            row[f"offices_{ind}"] = o; row[f"workers_{ind}"] = w
            row[f"per100k_{ind}"] = round(o / P.loc["00", y] * 100, 3)
            row[f"workers_per_office_{ind}"] = round(w / o, 2)
        nat.append(row)
    nat = pd.DataFrame(nat)
    nat.to_csv(R / "national.csv", index=False)
    n = nat.set_index("year")
    for ind in ["62", "63"]:
        m[f"nat_offices_{ind}"] = {int(y): int(v) for y, v in n[f"offices_{ind}"].items()}
        m[f"nat_change_{ind}_2009_2024_pct"] = round((n.loc[2024, f"offices_{ind}"] / n.loc[2009, f"offices_{ind}"] - 1) * 100, 1)
        m[f"nat_change_{ind}_2009_2024_n"] = int(n.loc[2024, f"offices_{ind}"] - n.loc[2009, f"offices_{ind}"])
        m[f"nat_workers_change_{ind}_2009_2024_pct"] = round((n.loc[2024, f"workers_{ind}"] / n.loc[2009, f"workers_{ind}"] - 1) * 100, 1)
        m[f"nat_per100k_{ind}"] = {int(y): float(v) for y, v in n[f"per100k_{ind}"].items()}
        m[f"nat_workers_per_office_{ind}"] = {int(y): float(v) for y, v in n[f"workers_per_office_{ind}"].items()}
    m["nat_change_62_2016_2024_n"] = int(n.loc[2024, "offices_62"] - n.loc[2016, "offices_62"])
    m["nat_pop_change_2009_2024_pct"] = round((P.loc["00", 2024] / P.loc["00", 2009] - 1) * 100, 1)
    # 年あたりの減り方
    o = n["offices_62"]
    m["per_year_change_62"] = {f"{a}-{b}": round(float((o[b] - o[a]) / (b - a)), 1) for a, b in zip(YEARS[:-1], YEARS[1:])}

    # 都道府県
    o62, w62, o63 = tab("62"), tab("62", "workers"), tab("63")
    pr = pd.DataFrame(index=[c for c in o62.index if c != "00"])
    pr.index.name = "pref_code"
    pr["pref"] = df.drop_duplicates("pref_code").set_index("pref_code")["area"].reindex(pr.index)
    pr["region"] = [REG_OF[c] for c in pr.index]
    for y in [2009, 2014, 2024]:
        pr[f"offices_{y}"] = o62.loc[pr.index, y]
        pr[f"per100k_{y}"] = (o62.loc[pr.index, y] / P.loc[pr.index, y] * 100).round(3)
    pr["change_pct"] = ((pr["offices_2024"] / pr["offices_2009"] - 1) * 100).round(2)
    pr["pop_change_pct"] = ((P.loc[pr.index, 2024] / P.loc[pr.index, 2009] - 1) * 100).round(2)
    pr["workers_change_pct"] = ((w62.loc[pr.index, 2024] / w62.loc[pr.index, 2009] - 1) * 100).round(2)
    pr["change_2014_2024_pct"] = ((pr["offices_2024"] / pr["offices_2014"] - 1) * 100).round(2)
    pr["coop_change_pct"] = ((o63.loc[pr.index, 2024] / o63.loc[pr.index, 2009] - 1) * 100).round(2)
    both = o62 + o63
    pr["both_change_pct"] = ((both.loc[pr.index, 2024] / both.loc[pr.index, 2009] - 1) * 100).round(2)
    pr = pr.sort_index()
    pr.to_csv(R / "pref_2009_2024.csv")
    m["n_pref_decline"] = int((pr["offices_2024"] < pr["offices_2009"]).sum())
    m["n_pref_increase"] = int((pr["offices_2024"] > pr["offices_2009"]).sum())
    m["n_pref_same"] = int((pr["offices_2024"] == pr["offices_2009"]).sum())
    m["prefs_not_decline"] = pr.loc[pr["offices_2024"] >= pr["offices_2009"], "pref"].tolist()
    m["pref_change_median_pct"] = round(float(pr["change_pct"].median()), 1)
    m["pref_change_min_pct"] = round(float(pr["change_pct"].min()), 1); m["pref_change_max_pct"] = round(float(pr["change_pct"].max()), 1)
    r = float(np.corrcoef(pr["pop_change_pct"], pr["change_pct"])[0, 1])
    m["corr_pop_offices"] = round(r, 3)
    m["spearman_pop_offices"] = round(float(pr["pop_change_pct"].rank().corr(pr["change_pct"].rank())), 3)
    nt = pr.drop(index="13")
    m["corr_pop_offices_excl_tokyo"] = round(float(np.corrcoef(nt["pop_change_pct"], nt["change_pct"])[0, 1]), 3)
    b = np.polyfit(pr["pop_change_pct"], pr["change_pct"], 1)
    m["slope_offices_on_pop"] = round(float(b[0]), 3); m["intercept_offices_on_pop"] = round(float(b[1]), 2)
    for y in [2009, 2024]:
        v = pr[f"per100k_{y}"]
        m[f"cv_per100k_{y}"] = round(float(v.std(ddof=0) / v.mean()), 4)
        m[f"per100k_min_{y}"] = round(float(v.min()), 2); m[f"per100k_max_{y}"] = round(float(v.max()), 2)
        m[f"per100k_mean_{y}"] = round(float(v.mean()), 2)

    # 地方
    reg = []
    for rg, cs in REGION.items():
        row = {"region": rg}
        for y in YEARS:
            row[f"offices_{y}"] = float(o62.loc[cs, y].sum()); row[f"pop_{y}"] = float(P.loc[cs, y].sum())
        row["change_pct"] = round((row["offices_2024"] / row["offices_2009"] - 1) * 100, 2)
        row["pop_change_pct"] = round((row["pop_2024"] / row["pop_2009"] - 1) * 100, 2)
        row["per100k_2009"] = round(row["offices_2009"] / row["pop_2009"] * 100, 3)
        row["per100k_2024"] = round(row["offices_2024"] / row["pop_2024"] * 100, 3)
        reg.append(row)
    reg = pd.DataFrame(reg)
    reg.to_csv(R / "region.csv", index=False)
    met = reg[reg.region.isin(METRO)]; oth = reg[~reg.region.isin(METRO)]
    m["metro_change_pct"] = round((met["offices_2024"].sum() / met["offices_2009"].sum() - 1) * 100, 2)
    m["other_change_pct"] = round((oth["offices_2024"].sum() / oth["offices_2009"].sum() - 1) * 100, 2)
    m["region_change_pct"] = dict(zip(reg.region, reg.change_pct))
    m["region_pop_change_pct"] = dict(zip(reg.region, reg.pop_change_pct))
    m["region_per100k_2009"] = dict(zip(reg.region, reg.per100k_2009)); m["region_per100k_2024"] = dict(zip(reg.region, reg.per100k_2024))
    # 地方の中での県の増減率の幅（最小・最大の値だけ。県名は付けず、順位も作らない）
    m["region_pref_change_range_pct"] = {rg: [round(float(pr.loc[cs, "change_pct"].min()), 1), round(float(pr.loc[cs, "change_pct"].max()), 1)] for rg, cs in REGION.items()}

    # 頑健性
    rob = []
    def add(label, s_change, pop_change=None):
        dec = int((s_change < 0).sum())
        cr = round(float(np.corrcoef(pop_change, s_change)[0, 1]), 3) if pop_change is not None else None
        rob.append({"check": label, "n_pref_decline": dec, "median_change_pct": round(float(s_change.median()), 1), "corr_with_pop": cr})
    add("基本：銀行業の事業所数 2009→2024年", pr["change_pct"], pr["pop_change_pct"])
    p1424 = ((P.loc[pr.index, 2024] / P.loc[pr.index, 2014] - 1) * 100)
    add("起点を2014年（同じ基礎調査）", pr["change_2014_2024_pct"], p1424)
    add("従業者数で見る", pr["workers_change_pct"], pr["pop_change_pct"])
    add("銀行業＋協同組織金融業", pr["both_change_pct"], pr["pop_change_pct"])
    add("協同組織金融業だけ", pr["coop_change_pct"], pr["pop_change_pct"])
    add("東京都を除く（46道府県）", nt["change_pct"], nt["pop_change_pct"])
    rob = pd.DataFrame(rob)
    # 小分類 622（中央銀行を除く）と 62 の差（2009・2014年だけ）
    o622 = tab("622")
    d = {y: int(o62.loc["00", y] - o622.loc["00", y]) for y in [2009, 2014]}
    m["offices_62_minus_622"] = d
    c62 = (o62.loc[pr.index, 2014] / o62.loc[pr.index, 2009] - 1) * 100
    c622 = (o622.loc[pr.index, 2014] / o622.loc[pr.index, 2009] - 1) * 100
    m["corr_62_622_change_2009_2014"] = round(float(np.corrcoef(c62, c622)[0, 1]), 4)
    m["nat_change_622_2009_2014_pct"] = round(float(o622.loc["00", 2014] / o622.loc["00", 2009] - 1) * 100, 2)
    m["nat_change_62_2009_2014_pct"] = round(float(o62.loc["00", 2014] / o62.loc["00", 2009] - 1) * 100, 2)
    rob.to_csv(R / "robustness.csv", index=False)
    m["robustness"] = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r_.items()} for r_ in rob.to_dict(orient="records")]

    m["H1"] = "支持" if m["n_pref_decline"] >= 40 else "外れ"
    m["H2"] = "支持" if m["corr_pop_offices"] > 0.3 else "外れ"
    m["H3"] = "支持" if m["metro_change_pct"] < m["other_change_pct"] else "外れ"
    m["H4"] = "支持" if m["cv_per100k_2024"] < m["cv_per100k_2009"] else "外れ"
    json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in m.items() if k != "robustness"}, ensure_ascii=False, indent=0))
    print(rob.to_string()); print(reg[["region", "offices_2009", "offices_2024", "change_pct", "pop_change_pct", "per100k_2009", "per100k_2024"]].to_string())


if __name__ == "__main__":
    main()
