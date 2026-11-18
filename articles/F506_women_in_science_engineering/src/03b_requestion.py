"""問い直し（結果を見てから足した）：工学の女性の入学者が増えた分は、どの学科で増えたのか。
とくに2020→2025年度（最近5年）と、上がり方が大きかった2024→2025年度を見る。
出力：results/requestion.json、results/eng_female_by_subfield.csv"""
import json
import pandas as pd
from common import DATA, RES

SUBS = ["機械工学", "電気通信工学", "土木建築工学", "応用化学", "応用理学", "原子力工学", "鉱山学", "金属工学", "繊維工学",
        "船舶工学", "航空工学", "経営工学", "工芸学", "その他"]


def main():
    e = pd.read_csv(DATA / "entrants.csv", keep_default_na=False)
    q = e[(e.level == "ug") & (e.table == "計") & (e.field == "工学") & (e["sub"] != "")]
    piv_f = q.pivot(index="sub", columns="year", values="female").reindex(SUBS)
    piv_t = q.pivot(index="sub", columns="year", values="total").reindex(SUBS)
    assert not piv_f.isna().any().any()
    rows, res = [], {}
    for y0, y1 in [(2010, 2025), (2020, 2025), (2024, 2025)]:
        tot = float(piv_f[y1].sum() - piv_f[y0].sum())
        res[f"{y0}_{y1}"] = {"female_change_total": int(tot), "by_sub": {}}
        for s in SUBS:
            d = float(piv_f.loc[s, y1] - piv_f.loc[s, y0])
            dt = float(piv_t.loc[s, y1] - piv_t.loc[s, y0])
            res[f"{y0}_{y1}"]["by_sub"][s] = {"female_change": int(d), "share_of_change": round(100 * d / tot, 1),
                                              "total_change": int(dt)}
            rows.append({"period": f"{y0}_{y1}", "sub": s, "female0": int(piv_f.loc[s, y0]), "female1": int(piv_f.loc[s, y1]),
                         "female_change": int(d), "share_of_change": round(100 * d / tot, 1),
                         "total0": int(piv_t.loc[s, y0]), "total1": int(piv_t.loc[s, y1]), "total_change": int(dt)})
    pd.DataFrame(rows).to_csv(RES / "eng_female_by_subfield.csv", index=False)
    # 大学院へのつながりの目安：修士の工学の女性の割合と、4年前の学部の工学の女性の割合
    top = e[(e["sub"] == "") & (e.table == "計") & (e.field == "工学")]
    def sh(level, y):
        t = top[(top.level == level) & (top.year == y)].iloc[0]
        return round(100 * t.female / t.total, 2)
    res["pipeline"] = {str(y): {"master": sh("master", y), "ug_4y_before": sh("ug", y - 4), "doctor": sh("doctor", y),
                                "master_2y_before": sh("master", y - 2)} for y in (2010, 2015, 2020, 2025)}
    (RES / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
