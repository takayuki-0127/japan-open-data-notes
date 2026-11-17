"""03b_requestion.py : 問い直し（結果を見てから足した）。
(1) 民間調査（本人に聞いたお小遣い）と同じ期間（2010→2022年、名目）で比べると、家計調査のこづかいの減り方はどれだけ違うか。
(2) こづかいの減った分は、実質の消費支出の減少のどれだけにあたるか。こづかいを除いた消費支出はどう動いたか。
出力：results/requestion.json, results/requestion.csv
"""
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
POCKET = "こづかい(使途不明)"


def main():
    df = pd.read_csv(DATA / "kakei_pocket_long.csv")
    cpi = pd.read_csv(DATA / "cpi_annual.csv").set_index("year")["deflator_to_2025"]
    sbi = pd.read_csv(DATA / "raw" / "sbi_okozukai_male_employee.csv").set_index("year")["male_employee_okozukai_yen"]
    w = df.pivot_table(index=["group", "year"], columns="item", values="value")
    out = {"sbi_2010": int(sbi.loc[2010]), "sbi_2022": int(sbi.loc[2022]), "sbi_1990": int(sbi.loc[1990]),
           "sbi_change_2010_2022_pct": round(float((sbi.loc[2022] / sbi.loc[2010] - 1) * 100), 1)}
    rows = []
    for g in ("workers_all", "husband_only", "dual"):
        s = w.loc[g]
        v10, v22 = float(s.loc[2010, POCKET]), float(s.loc[2022, POCKET])
        out[f"{g}_2010"] = int(round(v10))
        out[f"{g}_2022"] = int(round(v22))
        out[f"{g}_change_2010_2022_pct"] = round((v22 / v10 - 1) * 100, 1)
        rows.append((g, v10, v22, (v22 / v10 - 1) * 100))
    rows.append(("sbi_male_employee", float(sbi.loc[2010]), float(sbi.loc[2022]), out["sbi_change_2010_2022_pct"]))
    pd.DataFrame(rows, columns=["series", "y2010", "y2022", "change_pct"]).to_csv(RES / "requestion.csv", index=False,
                                                                                 float_format="%.2f")
    # 勤労者世帯：実質の消費支出の変化のうち、こづかいの分
    s = w.loc["workers_all"].copy()
    s["defl"] = cpi
    real = lambda col, a, b: float((s.loc[a:b, col] * s.loc[a:b, "defl"]).mean())  # noqa: E731
    c0, c1 = real("消費支出", 2000, 2002), real("消費支出", 2023, 2025)
    p0, p1 = real(POCKET, 2000, 2002), real(POCKET, 2023, 2025)
    k0, k1 = real("交際費", 2000, 2002), real("交際費", 2023, 2025)
    out["cons_real_p0"] = int(round(c0))
    out["cons_real_p1"] = int(round(c1))
    out["cons_real_change"] = int(round(c1 - c0))
    out["pocket_real_change"] = int(round(p1 - p0))
    out["kosai_real_change"] = int(round(k1 - k0))
    out["pocket_share_of_cons_decline_pct"] = round((p1 - p0) / (c1 - c0) * 100, 1)
    out["cons_ex_pocket_change_pct"] = round(((c1 - p1) / (c0 - p0) - 1) * 100, 1)
    out["cons_ex_pocket_kosai_change_pct"] = round(((c1 - p1 - k1) / (c0 - p0 - k0) - 1) * 100, 1)
    out["cons_change_pct"] = round((c1 / c0 - 1) * 100, 1)
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
