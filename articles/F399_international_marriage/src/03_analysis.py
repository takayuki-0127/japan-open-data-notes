"""国際結婚の割合、国籍別の寄与、夫外国と妻外国、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
NATS = ["韓国・朝鮮", "中国", "フィリピン", "タイ", "米国", "英国", "ブラジル", "ペルー", "その他の国"]


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def main():
    df = pd.read_csv(DATA / "marriage_nationality.csv")
    W = df.pivot_table(index="year", columns=["group", "nationality"], values="n", aggfunc="first")
    tot = W[("総数", "総数")]; intl = W[("夫妻の一方が外国", "総数")]; jj = W[("夫妻とも日本", "総数")]
    hw = W[("夫日本・妻外国", "総数")]; wh = W[("妻日本・夫外国", "総数")]
    Y = pd.DataFrame({"total": tot, "intl": intl, "share": 100 * intl / tot, "share_vs_jj": 100 * intl / jj,
                      "wife_foreign": hw, "husband_foreign": wh, "husband_foreign_share_of_intl": 100 * wh / intl})
    Y.round(4).to_csv(RES / "yearly.csv")
    out = {}
    peak = int(Y.share.idxmax())
    out["peak_year"] = peak; out["peak_share"] = r(Y.share.max(), 2); out["peak_count_year"] = int(Y.intl.idxmax()); out["peak_count"] = r(Y.intl.max(), 0)
    out["levels"] = {int(y): dict(intl=r(Y.loc[y, "intl"], 0), share=r(Y.loc[y, "share"], 2), wife_foreign=r(Y.loc[y, "wife_foreign"], 0),
                                  husband_foreign=r(Y.loc[y, "husband_foreign"], 0)) for y in (1970, 1990, 2000, 2006, 2015, 2019, 2025)}

    def contrib(group, y0, y1, avg=False):
        def val(n, y):
            if avg:
                return W.loc[y - 1:y + 1, (group, n)].mean()
            return W.loc[y, (group, n)]
        d_tot = val("総数", y1) - val("総数", y0)
        rows = []
        for n in NATS:
            d = val(n, y1) - val(n, y0)
            rows.append(dict(nationality=n, n0=val(n, y0), n1=val(n, y1), diff=d, share_of_change=100 * d / d_tot))
        return pd.DataFrame(rows), d_tot
    c06, dt = contrib("夫日本・妻外国", 2006, 2025)
    c06.round(3).to_csv(RES / "wife_nationality_contrib_2006_2025.csv", index=False)
    cn = c06.set_index("nationality")
    out["wife_contrib"] = {n: dict(n2006=r(x.n0, 0), n2025=r(x.n1, 0), share_of_change=r(x.share_of_change, 1)) for n, x in cn.iterrows()}
    out["wife_total_change"] = r(dt, 0)
    h2 = cn.loc["中国", "share_of_change"] + cn.loc["フィリピン", "share_of_change"]
    pct = lambda s, a, b: 100 * (s.loc[b] / s.loc[a] - 1)
    h3 = (pct(wh, 2006, 2025), pct(hw, 2006, 2025))

    def other_share(group, y):
        return 100 * W.loc[y, (group, "その他の国")] / W.loc[y, (group, "総数")]
    h4 = (other_share("夫日本・妻外国", 2006), other_share("夫日本・妻外国", 2025))
    out["wife_mix"] = {y: {n: r(100 * W.loc[y, ("夫日本・妻外国", n)] / W.loc[y, ("夫日本・妻外国", "総数")], 1) for n in NATS} for y in (2006, 2025)}
    out["husband_mix"] = {y: {n: r(100 * W.loc[y, ("妻日本・夫外国", n)] / W.loc[y, ("妻日本・夫外国", "総数")], 1) for n in NATS} for y in (2006, 2025)}

    # 頑健性
    ca, _ = contrib("夫日本・妻外国", 2006, 2024, avg=True)  # 2005〜07年平均 → 2023〜25年平均
    ca = ca.set_index("nationality")
    c19, _ = contrib("夫日本・妻外国", 2006, 2019); c19 = c19.set_index("nationality")
    avgpct = lambda s: 100 * (s.loc[2023:2025].mean() / s.loc[2005:2007].mean() - 1)
    rob = pd.DataFrame([
        dict(check="0 主（2006→2025年）", china_philippines_share=r(h2, 1), wife_foreign_pct=r(h3[1], 1), husband_foreign_pct=r(h3[0], 1), other_share=f"{h4[0]:.1f}→{h4[1]:.1f}"),
        dict(check="1 3年平均（2005〜07→2023〜25年）", china_philippines_share=r(ca.loc["中国", "share_of_change"] + ca.loc["フィリピン", "share_of_change"], 1),
             wife_foreign_pct=r(avgpct(hw), 1), husband_foreign_pct=r(avgpct(wh), 1), other_share=None),
        dict(check="2 コロナの前まで（2006→2019年）", china_philippines_share=r(c19.loc["中国", "share_of_change"] + c19.loc["フィリピン", "share_of_change"], 1),
             wife_foreign_pct=r(pct(hw, 2006, 2019), 1), husband_foreign_pct=r(pct(wh, 2006, 2019), 1), other_share=f"{h4[0]:.1f}→{other_share('夫日本・妻外国', 2019):.1f}"),
        dict(check="3 分母を夫妻とも日本の婚姻に（ピークの年と2025年）", china_philippines_share=None, wife_foreign_pct=None, husband_foreign_pct=None,
             other_share=f"{int(Y.share_vs_jj.idxmax())}年 {Y.share_vs_jj.max():.2f}% → 2025年 {Y.loc[2025, 'share_vs_jj']:.2f}%"),
        dict(check="4 H4 を夫外国の側で（その他の国の割合）", china_philippines_share=None, wife_foreign_pct=None, husband_foreign_pct=None,
             other_share=f"{other_share('妻日本・夫外国', 2006):.1f}→{other_share('妻日本・夫外国', 2025):.1f}"),
    ])
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")
    out["requestion"] = {int(y): r(Y.loc[y, "husband_foreign_share_of_intl"], 1) for y in (1970, 1980, 1990, 2006, 2015, 2025)}
    out["requestion_min_year"] = int(Y.loc[1990:].husband_foreign_share_of_intl.idxmin())
    out["hypotheses"] = {
        "H1": dict(value=peak, verdict="支持" if 2005 <= peak <= 2007 else "外れ"),
        "H2": dict(value=r(h2, 1), verdict="支持" if h2 >= 50 else "外れ"),
        "H3": dict(value=[r(h3[0], 1), r(h3[1], 1)], verdict="支持" if h3[0] > h3[1] else "外れ"),
        "H4": dict(value=[r(h4[0], 1), r(h4[1], 1)], verdict="支持" if h4[1] >= 2 * h4[0] else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
