"""問い直し（結果を見てから足した）：2021年以降を、2年の金利差が最も開いた月の前と後に分けると、
金利差とドル円の動きはどう対応していたのか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col=0)
m["lfx"] = 100 * np.log(m.usdjpy_avg)
main = json.load(open(R / "main.json", encoding="utf-8"))
b_pre = main["beta_pre2021"]["beta"]
per = pd.read_csv(R / "regression_by_period.csv")
b_in = float(per[(per.period == "2021〜2026") & (per.spread == "spread2")].beta.iloc[0])
post = m[(m.index >= "2021-01") & (m.index <= "2026-10")]
smax = post.spread2.idxmax()
segs = [("2021-01", smax), (smax, "2026-10")]
rows = []
for a, b in segs:
    act = m.loc[b, "lfx"] - m.loc[a, "lfx"]; dsp = m.loc[b, "spread2"] - m.loc[a, "spread2"]
    rows.append({"from": a, "to": b, "fx_from": m.loc[a, "usdjpy_avg"], "fx_to": m.loc[b, "usdjpy_avg"],
                 "spread_from": m.loc[a, "spread2"], "spread_to": m.loc[b, "spread2"], "d_spread": dsp,
                 "us2_from": m.loc[a, "us2"], "us2_to": m.loc[b, "us2"], "jp2_from": m.loc[a, "jp2"], "jp2_to": m.loc[b, "jp2"],
                 "actual_logpct": act, "fitted_pre2021": b_pre * dsp, "fitted_in2021_26": b_in * dsp})
seg = pd.DataFrame(rows)
seg.to_csv(R / "requestion_segments.csv", index=False, float_format="%.4f", lineterminator="\n")
# 2021年1月からの累積：実際と、金利差で説明できる分
path = pd.DataFrame({"actual": post.lfx - post.lfx.iloc[0],
                     "fitted_pre2021": b_pre * (post.spread2 - post.spread2.iloc[0]),
                     "fitted_in2021_26": b_in * (post.spread2 - post.spread2.iloc[0])})
path.to_csv(R / "requestion_path.csv", float_format="%.4f", lineterminator="\n")
main["requestion"] = {"spread_peak_month": smax, "beta_in_2021_26": b_in,
                      "segments": seg.round(4).to_dict(orient="records"),
                      "share_in2021_26_to_fxpeak": float(b_in * main["episode_2021_peak"]["d_spread"] / main["episode_2021_peak"]["actual_logpct"])}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=float)
print(seg.round(3).to_string()); print(main["requestion"]["share_in2021_26_to_fxpeak"])
