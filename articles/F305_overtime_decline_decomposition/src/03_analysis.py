"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "hours_monthly_size.csv", dtype={"size": str})
a = pd.read_csv(ROOT / "data" / "hours_annual_industry.csv")
m["ym"] = m.year * 12 + m.month - 1
r3 = lambda x: round(float(x), 3)
YM = lambda y, mo: y * 12 + mo - 1
NAMES = {"C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス", "G": "情報通信", "H": "運輸・郵便", "I": "卸売・小売", "J": "金融・保険",
         "K": "不動産・物品賃貸", "L": "学術研究等", "M": "飲食サービス等", "N": "生活関連サービス等", "O": "教育・学習支援", "P": "医療・福祉",
         "Q": "複合サービス", "R": "その他のサービス"}

def ser(size, var, typ=1):
    return m[(m["size"] == size) & (m.type == typ)].set_index("ym").sort_index()[var]

def did(var="ot_hours", treat="4", ctrl="9", start=YM(2017, 4), end=YM(2020, 2), event=YM(2019, 3)):
    D = (np.log(ser(treat, var)) - np.log(ser(ctrl, var))).loc[start:end]
    X = pd.DataFrame(index=D.index); X["post"] = (D.index >= event).astype(float)
    mon = (D.index % 12) + 1
    for k in range(2, 13): X[f"m{k}"] = (mon == k).astype(float)
    X = sm.add_constant(X)
    r = sm.OLS(D, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    b = r.params["post"]
    return dict(var=var, treat=treat, ctrl=ctrl, start=f"{start // 12}-{start % 12 + 1:02d}", end=f"{end // 12}-{end % 12 + 1:02d}", n=int(r.nobs),
                coef_log=r3(b), pct=r3(100 * (np.exp(b) - 1)), se=r3(r.bse["post"]), p=r3(r.pvalues["post"]))

out = {}
h1 = did(); out["H1"] = h1
out["H1_verdict"] = "支持" if (h1["coef_log"] < 0 and h1["p"] < 0.05) else "外れ"
rob1 = [h1 | {"spec": "主 500人以上 − 5〜29人、2017/4〜2020/2"},
        did(ctrl="7") | {"spec": "R1 対照を30〜99人"},
        did(start=YM(2018, 4)) | {"spec": "R2 直前1年（2018/4〜）"},
        did(var="total_hours") | {"spec": "参考 総実労働時間"},
        did(treat="5") | {"spec": "参考 100〜499人 − 5〜29人"}]
# 2020年4月（中小）：5〜29人 − 500人以上 で同じ形（2019/4〜2021/3、ただしコロナと重なる）
rob1.append(did(treat="9", ctrl="4", start=YM(2019, 4), end=YM(2021, 3), event=YM(2020, 3)) | {"spec": "参考 2020年4月 5〜29人 − 500人以上（コロナと重なる）"})
pd.DataFrame(rob1).to_csv(RES / "robustness_h1.csv", index=False)
out["robustness_h1"] = rob1

# 年平均の分解（調査産業計、一般労働者）
def ann(ind, typ, y, v):
    return float(a[(a.ind == ind) & (a.type == typ) & (a.year == y)][v].iloc[0])
def decomp(y0, y1, ind="TL", typ=1):
    T0, T1 = ann(ind, typ, y0, "total_hours"), ann(ind, typ, y1, "total_hours")
    D0, D1 = ann(ind, typ, y0, "days"), ann(ind, typ, y1, "days")
    S0, S1 = ann(ind, typ, y0, "sched_hours"), ann(ind, typ, y1, "sched_hours")
    O0, O1 = ann(ind, typ, y0, "ot_hours"), ann(ind, typ, y1, "ot_hours")
    tot = 100 * np.log(T1 / T0); days = 100 * np.log(D1 / D0); perday = tot - days
    return dict(period=f"{y0}-{y1}", ind=ind, type=typ, total_start=T0, total_end=T1, total_change_h=r3(T1 - T0), total_logpct=r3(tot),
                days_start=D0, days_end=D1, days_logpct=r3(days), perday_start=r3(T0 / D0), perday_end=r3(T1 / D1), perday_logpct=r3(perday),
                days_share=r3(days / tot) if tot != 0 else None,
                sched_start=S0, sched_end=S1, sched_change_h=r3(S1 - S0), sched_pct=r3(100 * (S1 / S0 - 1)),
                ot_start=O0, ot_end=O1, ot_change_h=r3(O1 - O0), ot_pct=r3(100 * (O1 / O0 - 1)))
h2 = decomp(2015, 2025); out["H2"] = h2
out["H2_verdict"] = "支持" if (h2["days_share"] or 0) >= 0.5 else "外れ"
out["H3_verdict"] = "支持" if h2["ot_pct"] < h2["sched_pct"] else "外れ"
rob2 = [h2 | {"spec": "主 一般 2015→2025"}, decomp(2018, 2025) | {"spec": "R3a 一般 2018→2025"}, decomp(2019, 2023) | {"spec": "R3b 一般 2019→2023"},
        decomp(2015, 2025, typ=0) | {"spec": "R4 就業形態計 2015→2025"}]
pd.DataFrame(rob2).to_csv(RES / "robustness_h2_h3.csv", index=False)
out["robustness_h2_h3"] = rob2
# 年ごとの調査産業計（一般）
yy = a[(a.ind == "TL") & (a.type == 1)].copy(); yy["per_day"] = yy.total_hours / yy.days
yy[["year", "total_hours", "sched_hours", "ot_hours", "days", "per_day"]].round(3).to_csv(RES / "tl_general_by_year.csv", index=False)

# H4 産業
def h4(y0, y1):
    rows = []
    for i in NAMES:
        rows.append(dict(ind=i, name=NAMES[i], ot_start=ann(i, 1, y0, "ot_hours"), ot_end=ann(i, 1, y1, "ot_hours"),
                         total_start=ann(i, 1, y0, "total_hours"), total_end=ann(i, 1, y1, "total_hours"),
                         days_start=ann(i, 1, y0, "days"), days_end=ann(i, 1, y1, "days")))
    t = pd.DataFrame(rows); t["ot_change"] = t.ot_end - t.ot_start
    rho, p = stats.spearmanr(t.ot_start, t.ot_change)
    return t, dict(period=f"{y0}-{y1}", spearman=r3(rho), p=r3(p), n_ot_down=int((t.ot_change < 0).sum()))
t4, s4 = h4(2018, 2025); t4.round(3).to_csv(RES / "industry_2018_2025.csv", index=False)
out["H4"] = s4; out["H4_verdict"] = "支持" if (s4["spearman"] < 0 and s4["p"] < 0.10) else "外れ"
out["H4_R5_2015_2025"] = h4(2015, 2025)[1]
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if not k.startswith("robustness")}, ensure_ascii=False, indent=0))
print(pd.DataFrame(rob1)[["spec", "pct", "se", "p"]].to_string())
print(pd.DataFrame(rob2)[["spec", "total_logpct", "days_logpct", "perday_logpct", "days_share", "sched_pct", "ot_pct", "total_change_h", "sched_change_h", "ot_change_h"]].to_string())
print(t4.round(1).to_string())
