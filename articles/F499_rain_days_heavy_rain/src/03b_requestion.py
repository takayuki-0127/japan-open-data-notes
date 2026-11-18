"""03b 問い直し（結果を見てから足した）：
雨の日の減り方は、弱い雨（1mm以上10mm未満）の日と、10mm以上の日のどちらで起きたか。
年降水量がほぼ変わらないなら、雨の日1日あたりの雨量（年降水量÷≧1mm の日数）はどれだけ増えたか。
あわせて、30年ごとの平均の表（雨の日・弱い雨の日・≧10mm・≧100mm・1日あたりの雨量）を作る。
出力：results/requestion.json, results/period_table.csv
"""
import json, pathlib, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_analysis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

PERIODS = [(1901, 1930), (1931, 1960), (1961, 1990), (1991, 2020), (1996, 2025)]


def main():
    d = A.load()
    ys = pd.read_csv(RES / "yearly.csv").set_index("year")
    rows = []
    for p in PERIODS:
        rows.append({"period": f"{p[0]}-{p[1]}", **{v: round(A.pmean(ys[v], p), 3) for v in ["d1", "light", "d10", "d50", "d100", "total", "sdii"]}})
    pt = pd.DataFrame(rows)
    pt.to_csv(RES / "period_table.csv", index=False)
    P1, P2 = A.P1, A.P2
    dd1 = A.pmean(ys["d1"], P2) - A.pmean(ys["d1"], P1)
    dl = A.pmean(ys["light"], P2) - A.pmean(ys["light"], P1)
    d10 = A.pmean(ys["d10"], P2) - A.pmean(ys["d10"], P1)
    s1, s2 = A.pmean(ys["sdii"], P1), A.pmean(ys["sdii"], P2)
    bl = A.ols_nw(ys["light"]); b10 = A.ols_nw(ys["d10"]); bs = A.ols_nw(ys["sdii"])
    st = pd.read_csv(RES / "station_table.csv")
    r = {
        "d1_diff": round(dd1, 2), "light_diff": round(dl, 2), "d10_diff": round(d10, 2),
        "light_share_of_d1_decrease": round(dl / dd1, 3),
        "light_slope_per100y": round(bl[0], 2), "light_ci": [round(bl[1], 2), round(bl[2], 2)],
        "d10_slope_per100y": round(b10[0], 2), "d10_ci": [round(b10[1], 2), round(b10[2], 2)],
        "sdii_p1": round(s1, 2), "sdii_p2": round(s2, 2), "sdii_change_pct": round((s2 / s1 - 1) * 100, 1),
        "sdii_slope_per100y": round(bs[0], 2), "sdii_ci": [round(bs[1], 2), round(bs[2], 2)],
        "n_station_light_down": int((st.light_diff < 0).sum()), "n_station_sdii_up": int((st.sdii_diff > 0).sum()),
        "n_station_d10_down": int((st.d10_diff < 0).sum()),
        # 時期のずれ：1901〜30年→1961〜90年 の変化が、1901〜30年→1996〜2025年 の変化のどれだけか
        "d1_share_of_change_by_1961_1990": round((A.pmean(ys["d1"], (1961, 1990)) - A.pmean(ys["d1"], P1)) / dd1, 3),
        "d100_share_of_change_after_1961_1990": round((A.pmean(ys["d100"], P2) - A.pmean(ys["d100"], (1961, 1990))) / (A.pmean(ys["d100"], P2) - A.pmean(ys["d100"], P1)), 3),
    }
    (RES / "requestion.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(pt.to_string()); print(r)


if __name__ == "__main__":
    main()
