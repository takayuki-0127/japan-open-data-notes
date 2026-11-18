"""03b 問い直し（結果を見てから足した）：
全国では2016年までの減り方がゆるく、2016年以降に速くなっていた。この「後半に速くなった」形が、
どの地方・どれだけの都道府県で見られるかを確かめる。調査の種類（基礎調査・活動調査）が混ざらないよう、
基礎調査どうし（2009→2014年と2014→2024年）でも比べる。
出力：results/requestion_timing.csv、results/requestion.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
df = pd.read_csv(D / "offices_long.csv", dtype={"pref_code": str, "ind": str})
pr = pd.read_csv(R / "pref_2009_2024.csv", dtype={"pref_code": str}).set_index("pref_code")
o = df[df.ind == "62"].pivot(index="pref_code", columns="year", values="offices")


def per_year(a, b, idx):
    return (o.loc[idx, b] - o.loc[idx, a]) / o.loc[idx, a] * 100 / (b - a)


def main():
    idx = pr.index
    t = pd.DataFrame(index=idx)
    t["pref"] = pr["pref"]; t["region"] = pr["region"]
    t["pct_per_year_2009_2016"] = per_year(2009, 2016, idx).round(3)
    t["pct_per_year_2016_2024"] = per_year(2016, 2024, idx).round(3)
    t["pct_per_year_2009_2014"] = per_year(2009, 2014, idx).round(3)
    t["pct_per_year_2014_2024"] = per_year(2014, 2024, idx).round(3)
    t.to_csv(R / "requestion_timing.csv")
    reg = []
    for rg, g in t.groupby("region", sort=False):
        cs = g.index
        row = {"region": rg}
        for a, b in [(2009, 2016), (2016, 2024), (2009, 2014), (2014, 2024)]:
            row[f"pct_per_year_{a}_{b}"] = round(float((o.loc[cs, b].sum() / o.loc[cs, a].sum() - 1) * 100 / (b - a)), 3)
        reg.append(row)
    reg = pd.DataFrame(reg)
    nat = {f"{a}_{b}": round(float((o.loc["00", b] / o.loc["00", a] - 1) * 100 / (b - a)), 3) for a, b in [(2009, 2016), (2016, 2024), (2009, 2014), (2014, 2024)]}
    q = {"nat_pct_per_year": nat,
         "n_pref_faster_after_2016": int((t["pct_per_year_2016_2024"] < t["pct_per_year_2009_2016"]).sum()),
         "n_pref_faster_after_2014_basic": int((t["pct_per_year_2014_2024"] < t["pct_per_year_2009_2014"]).sum()),
         "n_regions_faster_after_2016": int((reg["pct_per_year_2016_2024"] < reg["pct_per_year_2009_2016"]).sum()),
         "region": reg.set_index("region").to_dict(orient="index")}
    json.dump(q, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in q.items() if k != "region"}, ensure_ascii=False)); print(reg.to_string())


if __name__ == "__main__":
    main()
