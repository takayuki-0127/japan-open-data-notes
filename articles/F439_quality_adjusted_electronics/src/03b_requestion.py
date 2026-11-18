"""03b 問い直し（結果を見てから足した）：
パソコン2品目の指数が、品質を差し引かない「1台あたりの輸入額」と同じ率で動いていたら、総合の前年比はどれだけ違ったか。
2016〜2025年はその時期の基準（2015年・2020年）のウエイト、2006〜2015年は、2015年基準のウエイトの割合をその年の支出の割合とみなして近似する。"""
import csv, json, pathlib
from collections import defaultdict
from cpiload import read_cpi

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RAW, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "results"
PC = ["9078", "9079"]


def main():
    uv = {}
    with open(DATA / "trade_units.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["item"] == "computers":
                uv[int(r["year"])] = float(r["value_thousand_yen"]) / float(r["units"])
    rows = []
    for basis, years, note in [("2015", range(2006, 2016), "近似（2015年基準のウエイトの割合を、その年の支出の割合とみなした）"),
                               ("2015", range(2016, 2021), "その時期の基準"), ("2020", range(2021, 2026), "その時期の基準")]:
        names, codes, weights, body = read_cpi(RAW / f"cpi{basis}_item_annual.csv")
        jt = codes.index("0001")
        W = float(weights[jt])
        tab = {int(r[0]): r for r in body}
        for y in years:
            tprev = float(tab[y - 1][jt])
            act = cf = 0.0
            for c in PC:
                j = codes.index(c)
                a, b = float(tab[y - 1][j]), float(tab[y][j])
                wj = float(weights[j])
                if note.startswith("近似"):
                    act += wj / W * (b / a - 1) * 100
                    cf += wj / W * (uv[y] / uv[y - 1] - 1) * 100
                else:
                    act += wj * (b - a) / (W * tprev) * 100
                    cf += wj * a * (uv[y] / uv[y - 1] - 1) / (W * tprev) * 100
            rows.append({"year": y, "basis": basis, "note": note, "c_pc_actual": round(act, 4), "c_pc_if_unit_value": round(cf, 4), "diff": round(cf - act, 4)})
    with open(RES / "requestion_counterfactual.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)

    def mean(ys, key):
        v = [r[key] for r in rows if r["year"] in ys]
        return round(sum(v) / len(v), 3)
    out = {"diff_mean_2006_2015_approx": mean(range(2006, 2016), "diff"), "diff_mean_2016_2025": mean(range(2016, 2026), "diff"),
           "actual_mean_2006_2015_approx": mean(range(2006, 2016), "c_pc_actual"), "actual_mean_2016_2025": mean(range(2016, 2026), "c_pc_actual"),
           "diff_max_year": max(rows, key=lambda r: r["diff"])["year"], "diff_max": round(max(r["diff"] for r in rows), 3),
           "diff_min_year": min(rows, key=lambda r: r["diff"])["year"], "diff_min": round(min(r["diff"] for r in rows), 3)}
    with open(RES / "requestion.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")


if __name__ == "__main__":
    main()
