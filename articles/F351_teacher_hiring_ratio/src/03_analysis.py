"""倍率＝受験者÷採用者 の変化を、受験者の変化と採用者の変化に分ける（対数）。新卒・既卒の寄与。頑健性（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def decomp(lt, ty, a, b):
    q = lt[lt.type == ty].set_index("year")
    A0, A1, H0, H1 = q.loc[a, "applicants"], q.loc[b, "applicants"], q.loc[a, "hires"], q.loc[b, "hires"]
    dR = np.log((A1 / H1) / (A0 / H0)); dA = np.log(A1 / A0); dH = -np.log(H1 / H0)
    return dict(type=ty, start=int(a), end=int(b), ratio_start=float(A0 / H0), ratio_end=float(A1 / H1), applicants_start=float(A0), applicants_end=float(A1),
                hires_start=float(H0), hires_end=float(H1), dlogR=float(dR), share_applicants=float(dA / dR), share_hires=float(dH / dR))


def main():
    RES.mkdir(exist_ok=True)
    lt = pd.read_csv(ROOT / "data" / "long_term.csv")
    lt["ratio"] = lt.applicants / lt.hires
    npv = pd.read_csv(ROOT / "data" / "new_vs_prior.csv")
    ug = pd.read_csv(ROOT / "data" / "univ_graduates.csv").set_index("year")
    # 区切りの年：1990年度以降で倍率が最も高い年度（山）と、その後で受験者が最も多い年度
    marks = {}
    rows = []
    for ty in ["小学校", "中学校", "高等学校", "特別支援学校", "養護教諭", "計"]:
        q = lt[(lt.type == ty) & (lt.year >= 1990)].set_index("year")
        peak = int(q.ratio.idxmax())
        amax = int(q.loc[peak:, "applicants"].idxmax())
        marks[ty] = dict(peak=peak, applicants_max=amax)
        for a, b, lab in [(peak, amax, "前半（倍率の山→受験者の山）"), (amax, 2025, "後半（受験者の山→2025）"), (peak, 2025, "全体（倍率の山→2025）")]:
            if a < b:
                rows.append(dict(period=lab, **decomp(lt, ty, a, b)))
    dc = pd.DataFrame(rows)
    dc.round(4).to_csv(RES / "decomposition.csv", index=False)
    s = dc[dc.type == "小学校"].set_index("period")
    p1, p2 = s.loc["前半（倍率の山→受験者の山）"], s.loc["後半（受験者の山→2025）"]

    # 新卒・既卒（小学校）
    e = npv[(npv.who == "受験者") & (npv.type == "小学校")].pivot(index="year", columns="kind", values="value")
    base = int(p2.start) if int(p2.start) in e.index else int(e.index.min())
    d_tot = e.loc[base, "計"] - e.loc[2025, "計"]
    d_prior = e.loc[base, "既卒"] - e.loc[2025, "既卒"]
    d_new = e.loc[base, "新卒"] - e.loc[2025, "新卒"]
    e.to_csv(RES / "elem_new_vs_prior_applicants.csv")
    hyp = {
        "H1": dict(rule="前半の倍率の下がりのうち、採用者の寄与が半分未満なら外れ", period=[int(p1.start), int(p1.end)], share_hires=float(p1.share_hires),
                   verdict="支持" if p1.share_hires >= 0.5 else "外れ"),
        "H2": dict(rule="後半の倍率の下がりのうち、受験者の寄与が半分未満なら外れ", period=[int(p2.start), int(p2.end)], share_applicants=float(p2.share_applicants),
                   verdict="支持" if p2.share_applicants >= 0.5 else "外れ"),
        "H3": dict(rule="小学校の受験者の減りのうち、既卒者の分が半分未満なら外れ", base=base, decline_total=float(d_tot), decline_prior=float(d_prior),
                   decline_new=float(d_new), share_prior=float(d_prior / d_tot), verdict="支持" if d_prior / d_tot >= 0.5 else "外れ"),
        "H4": dict(rule="新卒の受験者の減り方（割合）が受験者全体以上なら外れ", base=base, new_ratio=float(e.loc[2025, "新卒"] / e.loc[base, "新卒"]),
                   total_ratio=float(e.loc[2025, "計"] / e.loc[base, "計"]),
                   verdict="支持" if e.loc[2025, "新卒"] / e.loc[base, "新卒"] > e.loc[2025, "計"] / e.loc[base, "計"] else "外れ"),
    }
    # 頑健性
    rob = []
    for split in [2010, 2012, 2013]:
        for ty in ["小学校", "中学校", "高等学校", "計"]:
            pk = marks[ty]["peak"]
            if pk < split:
                a = decomp(lt, ty, pk, split); b = decomp(lt, ty, split, 2025)
                rob.append(dict(check=f"区切りを{split}年度に", type=ty, first_share_hires=a["share_hires"], second_share_applicants=b["share_applicants"]))
    rb = pd.DataFrame(rob)
    # 受験者を大学の卒業者で割る（小学校）
    q = lt[lt.type == "小学校"].set_index("year")
    pg = (q.applicants / ug.univ_grad.reindex(q.index) * 1000).rename("applicants_per_1000_univ_grad")
    pg.round(3).to_csv(RES / "elem_applicants_per_univ_grad.csv")
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    # 新卒・既卒：基準を2013年度に
    b2 = 2013
    alt = dict(base=b2, share_prior=float((e.loc[b2, "既卒"] - e.loc[2025, "既卒"]) / (e.loc[b2, "計"] - e.loc[2025, "計"])),
               new_ratio=float(e.loc[2025, "新卒"] / e.loc[b2, "新卒"]), total_ratio=float(e.loc[2025, "計"] / e.loc[b2, "計"]))
    # 全校種の新卒・既卒
    allt = npv[(npv.who == "受験者") & (npv.type == "計")].pivot(index="year", columns="kind", values="value")
    allt.to_csv(RES / "all_new_vs_prior_applicants.csv")
    hires_new = npv[(npv.who == "採用者") & (npv.type == "小学校")].pivot(index="year", columns="kind", values="value")
    hires_new.to_csv(RES / "elem_new_vs_prior_hires.csv")
    v = lambda ty, y, c: float(lt[(lt.type == ty) & (lt.year == y)][c].iloc[0])
    main_ = dict(marks=marks, hypotheses=hyp, decomposition=dc.round(4).to_dict(orient="records"), robustness=rb.round(4).to_dict(orient="records"),
                 new_prior_base2013=alt, elem_per1000_2012=float(pg.loc[2012]), elem_per1000_2025=float(pg.loc[2025]), elem_per1000_2000=float(pg.loc[2000]),
                 univ_grad_2012=float(ug.loc[2012, "univ_grad"]), univ_grad_2025=float(ug.loc[2025, "univ_grad"]),
                 all_prior_base=float(allt.loc[base, "既卒"]), all_prior_2025=float(allt.loc[2025, "既卒"]), all_new_base=float(allt.loc[base, "新卒"]), all_new_2025=float(allt.loc[2025, "新卒"]),
                 elem_hires_new_base=float(hires_new.loc[base, "新卒"]), elem_hires_new_2025=float(hires_new.loc[2025, "新卒"]),
                 elem_hires_prior_base=float(hires_new.loc[base, "既卒"]), elem_hires_prior_2025=float(hires_new.loc[2025, "既卒"]),
                 total_ratio_1979=v("計", 1979, "ratio"), total_ratio_2000=v("計", 2000, "ratio"), total_ratio_2025=v("計", 2025, "ratio"))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(marks, ensure_ascii=False)); print(dc.round(3).to_string()); print(json.dumps(hyp, ensure_ascii=False)); print(rb.round(3).to_string()); print(alt)
    print(e.to_string()); print({k: main_[k] for k in ["elem_per1000_2000", "elem_per1000_2012", "elem_per1000_2025", "elem_hires_new_base", "elem_hires_new_2025", "elem_hires_prior_base", "elem_hires_prior_2025"]})


if __name__ == "__main__":
    main()
