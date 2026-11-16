"""失業率と求人倍率の関係：変化の相関、ベバリッジ曲線（10年ごと）、ハローワークの求職者と完全失業者の比（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def corr(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    return float(np.corrcoef(a[m], b[m])[0, 1])


def eq_u(q):
    """ln v = a + b ln u をあてはめ、v = u となる u（%）を返す。"""
    b, a = np.polyfit(np.log(q.u_rate), np.log(q.v_rate), 1)
    return float(np.exp(a / (1 - b))), float(b)


def main():
    RES.mkdir(exist_ok=True)
    d = pd.read_csv(ROOT / "data" / "annual.csv").set_index("year")
    d["v_rate"] = d.openings / 1e4 / (d.employed + d.openings / 1e4) * 100   # 欠員率（%）
    d["appl_per_unemp"] = d.applicants / 1e4 / d.unemployed                 # 有効求職者 ÷ 完全失業者
    d["openings_per_unemp"] = d.openings / 1e4 / d.unemployed               # 完全失業者あたりの有効求人
    d.round(5).to_csv(RES / "annual_indicators.csv")
    du, dr = d.u_rate.diff(), d.ratio.diff()
    c_same = corr(du.values, dr.values)
    c_lead = corr(du.values[1:], dr.values[:-1])   # 前の年の倍率の変化と今年の失業率の変化
    # 10年ごとのベバリッジ
    d["decade"] = (d.index // 10) * 10
    bev = []
    for dec, q in d.groupby("decade"):
        if len(q) < 5:
            continue
        ue, b = eq_u(q)
        bev.append(dict(decade=int(dec), n=len(q), eq_u=ue, slope=b, u_mean=float(q.u_rate.mean()), v_mean=float(q.v_rate.mean()), ratio_mean=float(q.ratio.mean())))
    bev = pd.DataFrame(bev)
    bev.round(4).to_csv(RES / "beveridge_by_decade.csv", index=False)
    a00 = float(d.loc[2000:2009, "appl_per_unemp"].mean()); a20 = float(d.loc[2020:2025, "appl_per_unemp"].mean())
    hyp = {
        "H1": dict(rule="変化どうしの相関が −0.6 以下なら支持", corr=c_same, verdict="支持" if c_same <= -0.6 else "外れ"),
        "H2": dict(rule="10年ごとの均衡失業率の目安の最大−最小が1ポイント以上なら支持", max=float(bev.eq_u.max()), min=float(bev.eq_u.min()),
                   diff=float(bev.eq_u.max() - bev.eq_u.min()), verdict="支持" if bev.eq_u.max() - bev.eq_u.min() >= 1 else "外れ"),
        "H3": dict(rule="有効求職者÷完全失業者の2020年代平均が2000年代平均より低ければ支持", y2000s=a00, y2020s=a20, verdict="支持" if a20 < a00 else "外れ"),
        "H4": dict(rule="前年の倍率の変化との相関（絶対値）が同じ年より強ければ支持", same=c_same, lead=c_lead, verdict="支持" if abs(c_lead) > abs(c_same) else "外れ"),
    }
    # 頑健性
    rob = []
    for a in [1964, 1970, 1990]:
        q = d.loc[a:]
        rob.append(dict(check=f"{a}年〜：失業率と有効求人倍率の変化の相関", value=corr(q.u_rate.diff().values, q.ratio.diff().values)))
    rob.append(dict(check="失業率と新規求人倍率の変化の相関（1964年〜）", value=corr(du.values, d.new_ratio.diff().values)))
    rob.append(dict(check="失業率と欠員率の変化の相関（1964年〜）", value=corr(du.values, d.v_rate.diff().values)))
    rob.append(dict(check="失業率と完全失業者あたり有効求人の変化の相関（1964年〜）", value=corr(du.values, d.openings_per_unemp.diff().values)))
    rob.append(dict(check="水準の相関：失業率と有効求人倍率（1963年〜）", value=corr(d.u_rate.values, d.ratio.values)))
    rob.append(dict(check="水準の相関：失業率と有効求人倍率（1990年〜）", value=corr(d.loc[1990:].u_rate.values, d.loc[1990:].ratio.values)))
    rb = pd.DataFrame(rob)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    v = lambda y, c: float(d.loc[y, c])
    main_ = dict(hypotheses=hyp, beveridge=bev.round(4).to_dict(orient="records"), robustness=rb.round(4).to_dict(orient="records"),
                 u_2025=v(2025, "u_rate"), ratio_2025=v(2025, "ratio"), u_max_year=int(d.u_rate.idxmax()), u_max=float(d.u_rate.max()),
                 ratio_max_year=int(d.ratio.idxmax()), ratio_max=float(d.ratio.max()), appl_per_unemp_2025=v(2025, "appl_per_unemp"),
                 appl_per_unemp_1990=v(1990, "appl_per_unemp"), appl_per_unemp_2002=v(2002, "appl_per_unemp"), appl_per_unemp_2009=v(2009, "appl_per_unemp"),
                 openings_per_unemp_2025=v(2025, "openings_per_unemp"), placements_1990=v(1990, "placements"), placements_2025=v(2025, "placements"),
                 applicants_2025=v(2025, "applicants"), unemployed_2025=v(2025, "unemployed"), openings_2025=v(2025, "openings"))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(hyp, ensure_ascii=False)); print(bev.round(2).to_string()); print(rb.round(3).to_string())
    print(d.loc[[1963, 1973, 1990, 2002, 2009, 2018, 2019, 2023, 2025], ["u_rate", "ratio", "v_rate", "appl_per_unemp", "openings_per_unemp"]].round(2).to_string())


if __name__ == "__main__":
    main()
