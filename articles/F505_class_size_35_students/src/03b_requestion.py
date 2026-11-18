"""問い直し（結果を見てから足した）：36人以上の学級がなくなった分、学級はどの人数の幅に移ったのか。
「上限のすぐ下（31〜35人）に集まった」のか、「分かれて小さくなった」のかを、収容人員別学級数で見る。
出力：results/requestion.json、results/bins_2020_2025.csv"""
import json
import pandas as pd
from common import DATA, RES

ORDER = ["7人以下", "8～12人", "13～20人", "21～25人", "26～30人", "31～35人", "36～40人", "41～45人", "46人", "47人", "48人", "49人", "50人以上"]
SHOW = ["7人以下", "8～12人", "13～20人", "21～25人", "26～30人", "31～35人", "36人以上"]


def dist(sb, school, year):
    d = sb[(sb.school == school) & (sb.entity == "公立|単式学級") & (sb.year == year)].set_index("bin")["n"]
    total = float(d["計"])
    out = {b: float(d[b]) for b in ORDER[:6]}
    out["36人以上"] = float(sum(d[b] for b in ORDER[6:]))
    assert abs(sum(out.values()) - total) < 0.5
    return out, total


def main():
    sb = pd.read_csv(DATA / "sizebins.csv")
    rows, res = [], {}
    for school in ("es", "jh"):
        res[school] = {}
        for y0, y1 in [(2020, 2025), (2015, 2020)]:
            d0, t0 = dist(sb, school, y0)
            d1, t1 = dist(sb, school, y1)
            key = f"{y0}_{y1}"
            res[school][key] = {"total0": t0, "total1": t1,
                                "bins": {b: {"n0": d0[b], "n1": d1[b], "diff": d1[b] - d0[b],
                                             "share0": round(100 * d0[b] / t0, 2), "share1": round(100 * d1[b] / t1, 2)} for b in SHOW}}
            for b in SHOW:
                rows.append({"school": school, "period": key, "bin": b, "n0": int(d0[b]), "n1": int(d1[b]), "diff": int(d1[b] - d0[b]),
                             "share0": round(100 * d0[b] / t0, 2), "share1": round(100 * d1[b] / t1, 2)})
    es = res["es"]["2020_2025"]["bins"]
    res["summary"] = {
        "es_36plus_diff": es["36人以上"]["diff"], "es_31_35_diff": es["31～35人"]["diff"],
        "es_13_30_diff": es["13～20人"]["diff"] + es["21～25人"]["diff"] + es["26～30人"]["diff"],
        "es_le25_share0": round(sum(es[b]["share0"] for b in SHOW[:4]), 2), "es_le25_share1": round(sum(es[b]["share1"] for b in SHOW[:4]), 2),
    }
    pd.DataFrame(rows).to_csv(RES / "bins_2020_2025.csv", index=False)
    (RES / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"], ensure_ascii=False), json.dumps(res["es"]["2020_2025"]["bins"], ensure_ascii=False))
    print(json.dumps(res["jh"]["2020_2025"]["bins"], ensure_ascii=False))


if __name__ == "__main__":
    main()
