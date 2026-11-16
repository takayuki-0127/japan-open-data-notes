"""問い直し（結果を見てから足した）。
2019〜2025年の実質GDIとGDPの差は年0.07ポイントと小さく、差の大部分は1994〜2012年（年0.26ポイント）だった。
→ 交易条件（輸出デフレーター÷輸入デフレーター）の悪化を、輸出の値段の下がりと輸入の値段の上がりに分ける。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main():
    d = pd.read_csv(RES / "annual_indicators.csv").set_index("year")
    rows = []
    for a, b in [(1994, 2012), (2012, 2019), (2019, 2025), (1994, 2025)]:
        dx = np.log(d.loc[b, "defl_exports"] / d.loc[a, "defl_exports"]); dm = np.log(d.loc[b, "defl_imports"] / d.loc[a, "defl_imports"])
        dt = dx - dm
        rows.append(dict(start=a, end=b, tot_start=float(d.loc[a, "terms_of_trade"]), tot_end=float(d.loc[b, "terms_of_trade"]),
                         tot_logchange=float(dt), export_part=float(dx), import_part=float(-dm),
                         export_share=float(dx / dt) if dt != 0 else np.nan, import_share=float(-dm / dt) if dt != 0 else np.nan,
                         tg_pct_start=float(d.loc[a, "trading_gains_pct_gdp"]), tg_pct_end=float(d.loc[b, "trading_gains_pct_gdp"])))
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "requestion_terms_of_trade.csv", index=False)
    out = dict(rows=t.round(4).to_dict(orient="records"), tot_1994=float(d.loc[1994, "terms_of_trade"]), tot_2025=float(d.loc[2025, "terms_of_trade"]),
               tot_min_year=int(d.terms_of_trade.idxmin()), tot_min=float(d.terms_of_trade.min()))
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(t.round(3).to_string()); print(out["tot_1994"], out["tot_2025"], out["tot_min_year"], out["tot_min"])


if __name__ == "__main__":
    main()
