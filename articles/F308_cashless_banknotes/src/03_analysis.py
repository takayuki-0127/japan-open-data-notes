"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
b = pd.read_csv(ROOT / "data" / "boj_monthly.csv")
e = pd.read_csv(ROOT / "data" / "emoney_annual.csv").set_index("year")
r3 = lambda x: round(float(x), 3)
full = b.groupby("year").month.count(); yrs = full[full == 12].index
ann = b[b.year.isin(yrs)].groupby("year").agg(notes_avg=("MABS2AN116", "mean"), coins_avg=("MABS2AN117", "mean"), call=("STRACLUCON", "mean"))
dec = b[(b.month == 12)].set_index("year")[["MACCV2", "MACCV2@01", "MACCV2@02", "MACCV201D5", "MACCV2@03", "MACCV2@05"]]
dec.columns = ["total", "y10000", "y5000", "y2000", "y1000", "y500"]
A = ann.join(dec, how="left")
A["share_10000"] = 100 * A.y10000 / A.total
for k, face in (("y10000", 10000), ("y5000", 5000), ("y1000", 1000)):
    A[f"count_{k}_100m"] = A[k] * 1e8 / face / 1e8  # 億枚
A["g_notes"] = 100 * np.log(A.notes_avg).diff()
A.round(4).to_csv(RES / "annual_table.csv")
lg = lambda c, a, z: 100 * np.log(A.loc[z, c] / A.loc[a, c])
out = {}
out["notes_avg"] = {str(y): r3(A.loc[y, "notes_avg"]) for y in (2010, 2015, 2019, 2023, 2024, 2025)}
out["H1"] = dict(growth_2015_2025=r3(lg("notes_avg", 2015, 2025)), growth_2015_2023=r3(lg("notes_avg", 2015, 2023)), growth_2023_2025=r3(lg("notes_avg", 2023, 2025)))
out["H1_verdict"] = "支持" if out["H1"]["growth_2015_2025"] > 0 else "外れ"
peak = A.notes_avg.idxmax(); out["peak_year"] = int(peak); out["peak_value"] = r3(A.notes_avg.max())
out["H2"] = dict(share_2010=r3(A.loc[2010, "share_10000"]), share_2025=r3(A.loc[2025, "share_10000"]), change=r3(A.loc[2025, "share_10000"] - A.loc[2010, "share_10000"]))
out["H2_verdict"] = "支持" if out["H2"]["change"] >= 2 else "外れ"
out["H4"] = dict(g_10000=r3(lg("y10000", 2015, 2025)), g_1000=r3(lg("y1000", 2015, 2025)), g_5000=r3(lg("y5000", 2015, 2025)))
out["H4"]["gap"] = r3(out["H4"]["g_1000"] - out["H4"]["g_10000"])
out["H4_verdict"] = "支持" if out["H4"]["gap"] <= -10 else "外れ"
# H3
D = A.join(e, how="inner")
D["d_use"] = D.use_share.diff(); D["g_amount"] = 100 * np.log(D.use_share * D.use_amount).diff()
D["d_call"] = D.call.diff()
D.round(4).to_csv(RES / "h3_table.csv")
def reg(y0=2011, y1=2025, xs=("d_use",)):
    x = D.loc[y0:y1].dropna(subset=["g_notes", *xs])
    m = sm.OLS(x.g_notes, sm.add_constant(x[list(xs)])).fit(cov_type="HC3")
    return dict(period=f"{y0}-{y1}", x="+".join(xs), n=int(m.nobs), coef=r3(m.params[xs[0]]), se=r3(m.bse[xs[0]]), p=r3(m.pvalues[xs[0]]), r2=r3(m.rsquared),
                **({"coef_call": r3(m.params[xs[1]]), "p_call": r3(m.pvalues[xs[1]])} if len(xs) > 1 else {}))
h3 = reg(); out["H3"] = h3
out["H3_verdict"] = "支持" if (h3["coef"] < 0 and h3["p"] < 0.10) else "外れ"
rob = [h3 | {"spec": "主"}, reg(xs=("d_use", "call")) | {"spec": "R2 コールレートを加える"},
       reg(xs=("g_amount",)) | {"spec": "R3 利用の広さ×金額の伸び"}, reg(y1=2023) | {"spec": "R4 2023年まで（新しい銀行券の前）"}]
out["robustness_h3"] = rob
out["R1"] = dict(growth_2010_2025=r3(lg("notes_avg", 2010, 2025)), dec_total_2015_2025=r3(lg("total", 2015, 2025)),
                 g_10000_2010_2025=r3(lg("y10000", 2010, 2025)), g_1000_2010_2025=r3(lg("y1000", 2010, 2025)))
out["emoney"] = {str(y): [r3(e.loc[y, "use_share"]), r3(e.loc[y, "use_amount"])] for y in (2010, 2015, 2020, 2025)}
out["call_avg"] = {str(y): r3(A.loc[y, "call"]) for y in (2015, 2023, 2024, 2025)}
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
print(A.loc[2008:, ["notes_avg", "g_notes", "total", "share_10000", "y1000", "call"]].round(2).to_string())
