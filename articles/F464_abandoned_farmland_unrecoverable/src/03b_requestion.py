"""問い直し（結果を見てから足した）：2021年度からの「新たに発生」「再生された」と面積計の動きから、
面積計から外れた分（残差）を出す。残差 = 前年度の面積計 + 新たに発生 − 再生された − 今年度の面積計。
残差が正なら、発生と再生だけでは説明できない「台帳から外れた分」がある（非農地判断などが考えられるが、この表では中身は分からない）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "data"; R = ROOT / "results"
REG_ORDER = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def resid(g):
    g = g.sort_values("year").set_index("year")
    out = []
    for y in [2022, 2023, 2024]:
        out.append({"year": y, "new": g.new[y], "reclaimed": g.reclaimed[y], "total_prev": g.total[y - 1], "total": g.total[y],
                    "residual": g.total[y - 1] + g.new[y] - g.reclaimed[y] - g.total[y],
                    "B_change": g.B[y] - g.B[y - 1], "A_change": g.A[y] - g.A[y - 1]})
    return pd.DataFrame(out)


def main():
    p = pd.read_csv(D / "panel.csv")
    p = p[p.year >= 2021]
    nat = resid(p.groupby("year", as_index=False)[["total", "A", "B", "new", "reclaimed"]].sum())
    nat.to_csv(R / "requestion_national.csv", index=False)
    rows = []
    for k in REG_ORDER:
        r = resid(p[p.region == k].groupby("year", as_index=False)[["total", "A", "B", "new", "reclaimed"]].sum())
        rows.append({"region": k, "new_sum": int(r.new.sum()), "reclaimed_sum": int(r.reclaimed.sum()), "residual_sum": int(r.residual.sum()),
                     "total_2021": int(r.total_prev.iloc[0]), "residual_pct_of_2021_total": round(float(r.residual.sum() / r.total_prev.iloc[0] * 100), 1)})
    reg = pd.DataFrame(rows)
    reg.to_csv(R / "requestion_region.csv", index=False)
    pref = []
    for c, g in p.groupby("pref_code", sort=True):
        r = resid(g)
        pref.append({"pref_code": int(c), "pref": g.pref.iloc[0], "residual_sum": int(r.residual.sum())})
    pref = pd.DataFrame(pref)
    out = {"national": {str(int(r.year)): {"new": int(r.new), "reclaimed": int(r.reclaimed), "residual": int(r.residual),
                                           "A_change": int(r.A_change), "B_change": int(r.B_change)} for r in nat.itertuples()},
           "national_sum": {"new": int(nat.new.sum()), "reclaimed": int(nat.reclaimed.sum()), "residual": int(nat.residual.sum()),
                            "residual_per_year": int(round(nat.residual.mean())),
                            "residual_over_new_pct": round(float(nat.residual.sum() / nat.new.sum() * 100), 1),
                            "total_change": int(nat.total.iloc[-1] - nat.total_prev.iloc[0])},
           "n_pref_residual_positive": int((pref.residual_sum > 0).sum()),
           "region": {r.region: {"residual_sum": r.residual_sum, "residual_pct_of_2021_total": r.residual_pct_of_2021_total} for r in reg.itertuples()}}
    json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
