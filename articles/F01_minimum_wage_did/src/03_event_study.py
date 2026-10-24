"""イベントスタディ → results/event_study.csv, results/pretrend_test.csv

y_it = 県効果 + 年効果 + Σ_k β_k·(bite上位半分 × [年=k])   基準年 = 2015年（2016年度から年3%前後の引き上げが続いた直前）
連続版：bite を標準化（1標準偏差あたり）して同じ形で推定
事前トレンド検定：2008〜2014年の β_k がすべて0か（県クラスターの Wald 検定）
"""
import numpy as np, pandas as pd
from common import panel, fe_ols, RES

BASE = 2015


def es(df, y, treat, trends=False):
    d = df.copy()
    regs = []
    for k in sorted(d.year.unique()):
        if k == BASE:
            continue
        c = f"e{k}"; d[c] = d[treat] * (d.year == k); regs.append(c)
    m, _, _ = fe_ols(d, y, regs, trends=trends)
    ci = m.conf_int()
    rows = [{"year": BASE, "beta": 0.0, "lo95": 0.0, "hi95": 0.0, "p": np.nan}]
    for c in regs:
        rows.append({"year": int(c[1:]), "beta": m.params[c], "lo95": ci.loc[c, 0], "hi95": ci.loc[c, 1], "p": m.pvalues[c]})
    pre = [c for c in regs if int(c[1:]) < BASE]
    w = m.wald_test(" , ".join(f"{c} = 0" for c in pre), scalar=True)
    return pd.DataFrame(rows).sort_values("year"), float(w.statistic), float(w.pvalue)


def main():
    df = panel()
    sd = df.drop_duplicates("pref")["bite"].std()
    df["bite_z"] = (df["bite"] - df["bite"].mean()) / sd
    out, tests = [], []
    for y in ["emp_rate", "unemp_rate", "openings_rate", "log_emp"]:
        for treat, lab in [("high_bite", "上位半分ダミー"), ("bite_z", "bite 1標準偏差")]:
            r, F, p = es(df, y, treat)
            r["outcome"], r["treat"] = y, lab; out.append(r)
            tests.append({"outcome": y, "treat": lab, "pre_F": F, "pre_p": p})
    res = pd.concat(out); res.round(5).to_csv(RES / "event_study.csv", index=False)
    t = pd.DataFrame(tests); t.round(4).to_csv(RES / "pretrend_test.csv", index=False)
    b = df.drop_duplicates("pref")
    pd.DataFrame([{"bite_sd": sd, "bite_mean_high": b[b.high_bite == 1].bite.mean(), "bite_mean_low": b[b.high_bite == 0].bite.mean(),
                   "bite_min": b.bite.min(), "bite_max": b.bite.max(), "bite_median": b.bite.median()}]).round(4).to_csv(RES / "bite_summary.csv", index=False)
    print(t.round(3).to_string())
    print(res[(res.treat == "上位半分ダミー") & res.outcome.isin(["emp_rate", "unemp_rate"])].round(3).to_string())
    print("sd", round(sd, 4))


if __name__ == "__main__":
    main()
