"""再婚を含む婚姻の割合、分解、夫と妻、再婚の年齢、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
OLD50 = ["50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳", "75～79歳", "80歳以上"]
OLD45 = ["45～49歳"] + OLD50


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def main():
    c = pd.read_csv(DATA / "combo.csv").set_index("year")
    ag = pd.read_csv(DATA / "age.csv")
    c["share_any_re"] = 100 * c.any_re / c.total
    c["share_husband_re"] = 100 * (c.re_both + c.husband_re_wife_first) / c.total
    c["share_wife_re"] = 100 * (c.re_both + c.husband_first_wife_re) / c.total
    c["share_person_re"] = 100 * (2 * c.re_both + c.husband_re_wife_first + c.husband_first_wife_re) / (2 * c.total)
    c.round(4).to_csv(RES / "yearly_shares.csv")
    out = {}
    out["share"] = {int(y): r(v, 1) for y, v in c.share_any_re.items()}
    first25 = int(c[c.share_any_re > 25].index.min())
    peak = int(c.share_any_re.idxmax())
    above = [int(y) for y in c[c.share_any_re > 25].index]
    out["first_above_25"] = first25; out["peak_year"] = peak; out["peak_share"] = r(c.share_any_re.max(), 1)
    out["years_above_25"] = above

    def decomp(y0, y1):
        dF = 100 * np.log(c.loc[y1, "first_both"] / c.loc[y0, "first_both"])
        dR = 100 * np.log(c.loc[y1, "any_re"] / c.loc[y0, "any_re"])
        return dict(first_change_pct=r(100 * (c.loc[y1, "first_both"] / c.loc[y0, "first_both"] - 1), 1),
                    re_change_pct=r(100 * (c.loc[y1, "any_re"] / c.loc[y0, "any_re"] - 1), 1),
                    dlog_first=r(dF, 1), dlog_re=r(dR, 1), dlogit_share=r(dR - dF, 1),
                    share0=r(c.loc[y0, "share_any_re"], 1), share1=r(c.loc[y1, "share_any_re"], 1))
    out["decomp_2000_2025"] = decomp(2000, 2025)
    since90 = c.loc[1990:]
    h3 = bool((since90.share_husband_re > since90.share_wife_re).all())
    out["husband_wife"] = {int(y): dict(husband=r(c.loc[y, "share_husband_re"], 1), wife=r(c.loc[y, "share_wife_re"], 1)) for y in (1970, 1990, 2000, 2010, 2025)}

    def old_share(sex, y, ages=OLD50):
        s = ag[(ag.kind == "再婚") & (ag.sex == sex) & (ag.year == y)].set_index("age").n
        known = s["総数"] - s["不詳"]
        return 100 * s[ages].sum() / known
    out["re_age50"] = {sex: {y: r(old_share(sex, y), 1) for y in (1990, 2000, 2010, 2025)} for sex in ("夫", "妻")}
    ages_tab = []
    for sex in ("夫", "妻"):
        for y in sorted(ag.year.unique()):
            if y >= 1990:
                ages_tab.append(dict(sex=sex, year=int(y), age50=old_share(sex, y), age45=old_share(sex, y, OLD45)))
    pd.DataFrame(ages_tab).round(3).to_csv(RES / "remarriage_age_share.csv", index=False)
    h4 = old_share("夫", 2025) - old_share("夫", 2000)

    rob = pd.DataFrame([
        dict(check="0 主：H2（2000→2025年）", value=f"初婚どうし {out['decomp_2000_2025']['first_change_pct']}%、再婚を含む {out['decomp_2000_2025']['re_change_pct']}%"),
        dict(check="1a H2 を1990→2025年で", value=f"初婚どうし {decomp(1990, 2025)['first_change_pct']}%、再婚を含む {decomp(1990, 2025)['re_change_pct']}%"),
        dict(check="1b H2 を2010→2025年で", value=f"初婚どうし {decomp(2010, 2025)['first_change_pct']}%、再婚を含む {decomp(2010, 2025)['re_change_pct']}%"),
        dict(check="2 H4 を妻で（50歳以上、2000→2025年）", value=f"{old_share('妻', 2000):.1f}% → {old_share('妻', 2025):.1f}%"),
        dict(check="3 H4 の線を45歳以上に（夫、2000→2025年）", value=f"{old_share('夫', 2000, OLD45):.1f}% → {old_share('夫', 2025, OLD45):.1f}%"),
        dict(check="4 再婚の人の割合（延べ人数、2025年）", value=f"{c.loc[2025, 'share_person_re']:.1f}%（最大 {c.share_person_re.max():.1f}%、{int(c.share_person_re.idxmax())}年）"),
    ])
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.to_dict(orient="records")

    # 問い直し：初婚どうしと再婚を含む婚姻の件数（2000年=100）
    rq = c.loc[1970:, ["first_both", "any_re"]].copy()
    rq["first_idx"] = 100 * rq.first_both / rq.loc[2000, "first_both"]
    rq["re_idx"] = 100 * rq.any_re / rq.loc[2000, "any_re"]
    rq.round(3).to_csv(RES / "requestion_counts.csv")
    out["requestion"] = dict(re_peak_year=int(c.loc[1970:].any_re.idxmax()), re_peak=r(c.loc[1970:].any_re.max(), 0),
                             first_peak_year=int(c.loc[1970:].first_both.idxmax()), first_peak=r(c.loc[1970:].first_both.max(), 0),
                             re_2025=r(c.loc[2025, "any_re"], 0), first_2025=r(c.loc[2025, "first_both"], 0),
                             re_2000=r(c.loc[2000, "any_re"], 0), first_2000=r(c.loc[2000, "first_both"], 0))
    out["hypotheses"] = {
        "H1": dict(value=first25, verdict="支持" if 2000 <= first25 <= 2009 else "外れ"),
        "H2": dict(value=[out["decomp_2000_2025"]["first_change_pct"], out["decomp_2000_2025"]["re_change_pct"]],
                   verdict="支持" if out["decomp_2000_2025"]["first_change_pct"] < out["decomp_2000_2025"]["re_change_pct"] else "外れ"),
        "H3": dict(value=h3, verdict="支持" if h3 else "外れ"),
        "H4": dict(value=r(h4, 1), verdict="支持" if h4 >= 10 else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "share"}, ensure_ascii=False))
    print(c.loc[1990:, ["share_any_re", "share_husband_re", "share_wife_re"]].round(1).T.to_string())


if __name__ == "__main__":
    main()
