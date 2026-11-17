"""03b 問い直し：ばらつきの大小は、「とても少ない年」と「とても多い年」のどちらで起きているのか。
全国の偏差が −200mm 以下（少雨の年）と +200mm 以上（多雨の年）の数を、30年ごとに数える。
出力：results/requestion.json, results/extreme_years.csv
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
P = [(1901, 1930), (1931, 1960), (1961, 1990), (1971, 2000), (1996, 2025)]


def main():
    nat = pd.read_csv(D / "national.csv").set_index("year").anom_mm
    rows = []
    for a, b in P:
        x = nat.loc[a:b]
        rows.append(dict(period=f"{a}-{b}", dry_le_m200=int((x <= -200).sum()), wet_ge_p200=int((x >= 200).sum())))
    t = pd.DataFrame(rows); t.to_csv(R / "extreme_years.csv", index=False)
    dry_years = [int(y) for y in nat.index[nat <= -200]]
    out = {"dry_years_all": dry_years, "wet_years_all": [int(y) for y in nat.index[nat >= 200]]}
    for r in rows:
        out[f"dry_{r['period']}"] = r["dry_le_m200"]; out[f"wet_{r['period']}"] = r["wet_ge_p200"]
    json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t); print(out)


if __name__ == "__main__":
    main()
