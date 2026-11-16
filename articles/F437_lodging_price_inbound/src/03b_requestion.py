"""03b 問い直し：月ごとの相関は弱いのに、年で見ると宿泊料と訪日客がそろって動いて見えるのはなぜか。
(1) 年ごとの変化（対数差×100）の関係：2004〜2019年の傾き（訪日客が10増えたとき宿泊料がいくつ動くか）。
(2) 季節の形：月ごとの宿泊料と訪日客の、その年の平均との比の相関（2019年、2025年）。
(3) 2026年1〜9月：訪日客が前年を下回った月の宿泊料の前年同月比。
出力：results/requestion.json, results/annual_change.csv, results/season.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    a = pd.read_csv(R / "annual.csv").set_index("year").loc[2003:]
    ch = pd.DataFrame({"d_visitors": np.log(a.visitors).diff() * 100, "d_lodging": np.log(a.lodging_z).diff() * 100,
                       "d_real": np.log(a.real_lodging).diff() * 100}).loc[2004:]
    ch.round(4).to_csv(R / "annual_change.csv")
    pre = ch.loc[2004:2019]
    b = np.polyfit(pre.d_visitors, pre.d_lodging, 1); br = np.polyfit(pre.d_visitors, pre.d_real, 1)
    r = float(np.corrcoef(pre.d_visitors, pre.d_lodging)[0, 1])
    # 年ごとの変化を2つの時期で
    up = pre[pre.d_visitors > 15]
    se = []
    for yr in (2019, 2025):
        s = m.loc[yr * 100 + 1: yr * 100 + 12, ["lodging_z", "visitors"]]
        se.append(pd.DataFrame({"year": yr, "month": s.index % 100, "lodging_rel": s.lodging_z / s.lodging_z.mean() * 100, "visitors_rel": s.visitors / s.visitors.mean() * 100}))
    se = pd.concat(se); se.round(4).to_csv(R / "season.csv", index=False)
    sc = {yr: float(np.corrcoef(g.lodging_rel, g.visitors_rel)[0, 1]) for yr, g in se.groupby("year")}
    g25 = se[se.year == 2025].set_index("month")
    y = pd.read_csv(R / "yoy.csv").set_index("ym").loc[202601:202609]
    out = dict(slope_annual_2004_2019=float(b[0]), intercept_annual=float(b[1]), slope_real_2004_2019=float(br[0]), corr_annual_2004_2019=r,
               mean_d_lodging_when_vis_up15=float(up.d_lodging.mean()), n_vis_up15=int(len(up)),
               mean_d_lodging_other=float(pre[pre.d_visitors <= 15].d_lodging.mean()), n_other=int((pre.d_visitors <= 15).sum()),
               d_lodging_2024=float(ch.d_lodging[2024]), d_lodging_2025=float(ch.d_lodging[2025]), d_vis_2025=float(ch.d_visitors[2025]),
               pred_d_lodging_2025=float(b[0] * ch.d_visitors[2025] + b[1]),
               season_corr_2019=sc[2019], season_corr_2025=sc[2025],
               lodging_peak_month_2025=int(g25.lodging_rel.idxmax()), lodging_peak_rel_2025=float(g25.lodging_rel.max()),
               lodging_low_month_2025=int(g25.lodging_rel.idxmin()), lodging_low_rel_2025=float(g25.lodging_rel.min()),
               visitors_peak_month_2025=int(g25.visitors_rel.idxmax()), visitors_low_month_2025=int(g25.visitors_rel.idxmin()),
               n_2026_vis_down=int((y.vis < 0).sum()), lodging_yoy_when_vis_down_2026=float(y.lodging[y.vis < 0].mean()), n_2026=int(len(y)))
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(ch.round(1).to_string()); print(se.round(1).to_string()); print(y.round(1).to_string())


if __name__ == "__main__":
    main()
