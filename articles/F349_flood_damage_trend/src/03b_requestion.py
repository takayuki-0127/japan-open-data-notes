"""問い直し（結果を見てから足した）。
1. 1961年からでは実質額は横ばいだが、1991年からに絞ると傾きが正になった。2000年代が低かっただけか、近年に上がっているのか？
   → 1991〜2023年、2001〜2023年の傾きと区間、2018・2019年を除いた傾き。
2. 「大きな年」（実質1兆円以上）は増えたか？ 10年ごとの回数。"""
import pathlib, json, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
spec = importlib.util.spec_from_file_location("ana", ROOT / "src" / "03_analysis.py")
ana = importlib.util.module_from_spec(spec); spec.loader.exec_module(ana)


def main():
    d = pd.read_csv(RES / "series.csv")
    out = {"windows": []}
    for a, b, ex in [(1991, 2023, ()), (2001, 2023, ()), (2001, 2023, (2018, 2019)), (1991, 2023, (2018, 2019)), (1961, 2023, (2018, 2019))]:
        u = d[(d.year >= a) & (d.year <= b) & (~d.year.isin(ex))]
        ci = ana.block_boot_ci(u.year, u.damage_real2015_oku)
        out["windows"].append(dict(window=f"{a}〜{b}" + ("（2018・2019年を除く）" if ex else ""), n=int(len(u)),
                                   real_ols_pct=ana.pct(ana.ols_slope(u.year, u.damage_real2015_oku)),
                                   real_ts_pct=ana.pct(ana.theil_sen(u.year, u.damage_real2015_oku)),
                                   ci_low_pct=ana.pct(ci[0]), ci_high_pct=ana.pct(ci[1])))
    m = d[(d.year >= 1961) & (d.year <= 2023)].copy()
    m["decade"] = ((m.year - 1961) // 10) * 10 + 1961
    big = m.groupby("decade").apply(lambda g: pd.Series(dict(n_years=len(g), n_big=int((g.damage_real2015_oku >= 10000).sum()),
                                                             big_years=" ".join(str(y) for y in g.year[g.damage_real2015_oku >= 10000]))), include_groups=False).reset_index()
    big.to_csv(RES / "requestion_big_years.csv", index=False)
    out["big_years_by_decade"] = big.to_dict(orient="records")
    out["n_big_total"] = int((m.damage_real2015_oku >= 10000).sum())
    # 2001〜2010年の平均と、2011〜2023年の平均（2018・2019年を除く／含む）
    out["mean_2001_2010"] = float(m[m.year.between(2001, 2010)].damage_real2015_oku.mean())
    out["mean_2011_2023"] = float(m[m.year.between(2011, 2023)].damage_real2015_oku.mean())
    out["mean_2011_2023_excl_2018_2019"] = float(m[m.year.between(2011, 2023) & ~m.year.isin([2018, 2019])].damage_real2015_oku.mean())
    out["mean_1961_2000"] = float(m[m.year.between(1961, 2000)].damage_real2015_oku.mean())
    pd.DataFrame(out["windows"]).round(4).to_csv(RES / "requestion_windows.csv", index=False)
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(pd.DataFrame(out["windows"]).round(2).to_string()); print(big.to_string())
    print({k: round(v, 1) for k, v in out.items() if k.startswith("mean")}, out["n_big_total"])


if __name__ == "__main__":
    main()
