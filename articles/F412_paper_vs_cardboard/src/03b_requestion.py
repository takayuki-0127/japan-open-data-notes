"""問い直し：段ボールの使い道のうち、増えた量（減った量）が大きいのはどれか。
2013→2014年に段ボール側だけ段差があるので、2014年からの変化で比べる（2008年からの変化も参考に出す）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
USES = [("use_processed_food", "加工食品用（飲料を含む）"), ("use_produce", "青果物用"), ("use_mailorder", "通販・宅配・引越用"),
        ("use_machinery", "電気器具・機械器具用"), ("use_medicine", "薬品・洗剤・化粧品用"), ("use_ceramics", "陶磁器・ガラス製品・雑貨用"),
        ("use_textile", "繊維製品用"), ("use_nonpack", "包装用以外"), ("use_other", "その他の食料品・製箱用（残り）")]


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    a = pd.read_csv(D / "annual.csv", index_col=0)
    c = {k: a[f"consumption__{k}"] for k, _ in USES if k != "use_other"}
    tot = a["consumption__use_total"]
    c["use_other"] = tot - sum(c.values())
    rows = []
    for k, ja in USES:
        v = c[k]
        rows.append({"use": k, "name_ja": ja, "v2008": r6(v[2008]), "v2014": r6(v[2014]), "v2025": r6(v[2025]),
                     "change_2014_2025": r6(v[2025] - v[2014]), "change_2008_2025": r6(v[2025] - v[2008]),
                     "share_2014_pct": r6(v[2014] / tot[2014] * 100), "share_2025_pct": r6(v[2025] / tot[2025] * 100),
                     "ratio_2025_2014": r6(v[2025] / v[2014])})
    t = pd.DataFrame(rows)
    t.to_csv(R / "requestion_use_change.csv", index=False)
    rq = {"total_change_2014_2025": r6(tot[2025] - tot[2014]), "total_ratio_2025_2014": r6(tot[2025] / tot[2014]),
          "total_2014": r6(tot[2014]), "total_2025": r6(tot[2025]),
          "largest_increase_2014_2025": t.sort_values("change_2014_2025", ascending=False).iloc[0]["use"],
          "uses": {r["use"]: r for r in rows}}
    pos = t[t["change_2014_2025"] > 0]["change_2014_2025"].sum()
    rq["sum_of_increases_2014_2025"] = r6(pos)
    for k in ["use_processed_food", "use_mailorder"]:
        rq[f"{k}_share_of_increases"] = r6(t.set_index("use").loc[k, "change_2014_2025"] / pos)
    (R / "requestion.json").write_text(json.dumps(rq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(t[["name_ja", "v2014", "v2025", "change_2014_2025", "share_2014_pct", "share_2025_pct", "ratio_2025_2014"]].to_string())
    print({k: v for k, v in rq.items() if k != "uses"})


if __name__ == "__main__":
    main()
