"""問い直し（結果を見てから足した）。
小学校の受験者の減りは、ほぼ全部が既卒者の減りだった。既卒者の多くは、前の年までに受けて採用されなかった人（再受験）と考えられる。
→ 既卒の受験者(t) を、前の年度の「受験者 − 採用者」（採用されなかった人の数）と比べる。採用が増えると、翌年に受け直す人の元になる数が減る。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main():
    lt = pd.read_csv(ROOT / "data" / "long_term.csv")
    npv = pd.read_csv(ROOT / "data" / "new_vs_prior.csv")
    out = {}
    tabs = []
    for ty in ["小学校", "中学校", "高等学校", "計"]:
        q = lt[lt.type == ty].set_index("year")
        notsel = (q.applicants - q.hires).shift(1).rename("not_hired_prev")
        e = npv[(npv.who == "受験者") & (npv.type == ty)].pivot(index="year", columns="kind", values="value")
        t = pd.concat([e, notsel], axis=1).dropna()
        t["prior_per_not_hired_prev"] = t["既卒"] / t.not_hired_prev
        t["type"] = ty
        tabs.append(t.reset_index().rename(columns={"index": "year"}))
        c = float(np.corrcoef(t["既卒"], t.not_hired_prev)[0, 1])
        # 変化どうしの相関（水準の相関は共通のトレンドで大きく出るため）
        dc = float(np.corrcoef(np.diff(np.log(t["既卒"])), np.diff(np.log(t.not_hired_prev)))[0, 1])
        b = float(np.polyfit(t.not_hired_prev, t["既卒"], 1)[0])
        out[ty] = dict(corr_level=c, corr_dlog=dc, slope=b, ratio_first=float(t.prior_per_not_hired_prev.iloc[0]), ratio_last=float(t.prior_per_not_hired_prev.iloc[-1]),
                       ratio_min=float(t.prior_per_not_hired_prev.min()), ratio_max=float(t.prior_per_not_hired_prev.max()),
                       not_hired_prev_first=float(t.not_hired_prev.iloc[0]), not_hired_prev_last=float(t.not_hired_prev.iloc[-1]),
                       first_year=int(t.index.min() if "year" not in t else t.year.min()), last_year=2025)
    tb = pd.concat(tabs, ignore_index=True)
    tb.round(4).to_csv(RES / "requestion_prior_vs_not_hired.csv", index=False)
    # 小学校の採用者に占める新卒の割合
    h = npv[(npv.who == "採用者") & (npv.type == "小学校")].pivot(index="year", columns="kind", values="value")
    out["elem_hires_new_share_2012"] = float(h.loc[2012, "新卒"] / h.loc[2012, "計"])
    out["elem_hires_new_share_2025"] = float(h.loc[2025, "新卒"] / h.loc[2025, "計"])
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))
    print(tb[tb.type == "小学校"].round(3).to_string())


if __name__ == "__main__":
    main()
