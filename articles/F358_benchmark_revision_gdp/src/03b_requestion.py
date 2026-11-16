"""問い直し（結果を見てから足した）。
名目GDPの水準が最近ほど大きく上に書き換わったので、「600兆円を初めて超えた年」「1997年の山を初めて超えた年」のような節目の年が、基準で変わるかを見る。"""
import pathlib, json
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main():
    t = pd.read_csv(RES / "gdp_revisions.csv").set_index("year")
    out = {}
    for k, col in [("old", "nominal_old"), ("new", "nominal_new")]:
        s = t[col]
        peak97 = float(s.loc[1997])
        out[f"{k}_1997"] = peak97
        out[f"{k}_first_above_1997"] = int(s[(s.index > 1997) & (s > peak97)].index.min())
        for th in [550000, 600000]:
            above = s[s >= th]
            out[f"{k}_first_above_{th//1000}"] = int(above.index.min()) if len(above) else None
        out[f"{k}_max_year"] = int(s.idxmax()); out[f"{k}_max"] = float(s.max())
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
