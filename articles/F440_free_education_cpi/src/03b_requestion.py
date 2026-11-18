"""03b 問い直し（結果を見てから足した）：
(1) 2026年4月は、小学校の給食費の無償化も同じ月に始まった。高校の授業料と給食は、それぞれどれだけ押し下げたか。
(2) 2019年1月〜2026年9月の総合の前年同月比から、幼稚園・保育所・高校の授業料の5品目の寄与を除くと、どう見えるか。
   月ごとに、その時期の基準の表を使う（2019〜2020年：2015年基準、2021〜2025年：2020年基準、2026年：2025年基準）。"""
import csv, json, pathlib
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
spec = importlib.util.spec_from_file_location("a", pathlib.Path(__file__).with_name("03_analysis.py"))
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

FREE5 = ["8080", "8090", "9921", "8020", "8030"]


def basis_of(p):
    y = int(p[:4])
    return "2015" if y <= 2020 else ("2020" if y <= 2025 else "2025")


def main():
    v, w, nm = A.load("monthly")
    out = {}
    # (1) 2026年4月〜9月：高校と給食
    lunch = {}
    for basis in ["2025", "2020"]:
        hs = [A.contrib(v, w, basis, ["8020", "8030"], A.shift("202604", k)) for k in range(6)]
        lu = [A.contrib(v, w, basis, ["0044"], A.shift("202604", k)) for k in range(6)]
        lunch[basis] = {"hs_mean": A.r(sum(hs) / 6), "lunch_mean": A.r(sum(lu) / 6),
                        "lunch_mom_pct_202604": A.r(100 * (v[(basis, "0044")]["202604"] / v[(basis, "0044")]["202603"] - 1), 1),
                        "lunch_weight_per10000": A.r(10000 * w[(basis, "0044")] / w[(basis, "0001")], 1)}
    out["apr2026"] = lunch
    # (2) 前年同月比から5品目の寄与を除く
    rows = []
    p = "201901"
    while p <= "202609":
        b = basis_of(p)
        t = A.yoy(v, b, "0001", p)
        c = A.contrib(v, w, b, FREE5, p)
        cl = A.contrib(v, w, b, ["0044"], p)
        cp = A.contrib(v, w, b, ["8080", "8090", "9921"], p)
        ch = A.contrib(v, w, b, ["8020", "8030"], p)
        rows.append({"period": p, "basis": b, "total_yoy": A.r(t, 3), "c_free5": A.r(c, 4), "c_preschool": A.r(cp, 4), "c_hs": A.r(ch, 4),
                     "total_ex_free5": A.r(t - c, 3), "c_lunch": A.r(cl, 4)})
        p = A.shift(p, 1)
    with open(RES / "requestion_ex_free.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); wr.writeheader(); wr.writerows(rows)
    big = [x for x in rows if x["c_free5"] <= -0.1]
    out["months_free5_le_minus0_1"] = len(big)
    out["months_total"] = len(rows)
    # 2019年10月〜2020年9月：総合の前年比と、除いた値の平均
    def avg(a, b, key):
        s = [x[key] for x in rows if a <= x["period"] <= b]
        return A.r(sum(s) / len(s))
    out["avg_201910_202009"] = {"total": avg("201910", "202009", "total_yoy"), "ex": avg("201910", "202009", "total_ex_free5")}
    out["avg_202504_202512"] = {"total": avg("202504", "202512", "total_yoy"), "ex": avg("202504", "202512", "total_ex_free5")}
    out["avg_202604_202609"] = {"total": avg("202604", "202609", "total_yoy"), "ex": avg("202604", "202609", "total_ex_free5"),
                                "ex_and_lunch": A.r(sum(x["total_ex_free5"] - x["c_lunch"] for x in rows if "202604" <= x["period"] <= "202609") / 6)}
    # 2020年4月：総合の前年比が0以下になった月
    out["months_total_le0_2020"] = [x["period"] for x in rows if x["period"].startswith("2020") and x["total_yoy"] <= 0]
    out["months_ex_le0_2020"] = [x["period"] for x in rows if x["period"].startswith("2020") and x["total_ex_free5"] <= 0]
    with open(RES / "requestion.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")


if __name__ == "__main__":
    main()
