"""基準改定（2015年基準→2020年基準）による GDP の書き換え：名目の水準、実質・名目・デフレーターの伸び率、内訳（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OLD, NEW = "2015年基準", "2020年基準"


def main():
    RES.mkdir(exist_ok=True)
    v = pd.read_csv(ROOT / "data" / "vintages.csv")
    p = v.pivot_table(index=["kind", "item", "year"], columns="vintage", values="value").reset_index()
    g = p[p.item == "gdp"].copy()
    nom = g[g.kind == "nominal"].set_index("year"); real = g[g.kind == "real"].set_index("year"); defl = g[g.kind == "deflator"].set_index("year")
    t = pd.DataFrame(index=nom.index)
    t["nominal_old"] = nom[OLD]; t["nominal_new"] = nom[NEW]
    t["nominal_level_rev_pct"] = (nom[NEW] / nom[OLD] - 1) * 100
    t["nominal_level_rev_trillion"] = (nom[NEW] - nom[OLD]) / 1000
    for k, s in [("real", real), ("nominal", nom), ("deflator", defl)]:
        t[f"{k}_growth_old"] = s[OLD].pct_change() * 100
        t[f"{k}_growth_new"] = s[NEW].pct_change() * 100
        t[f"{k}_growth_rev"] = t[f"{k}_growth_new"] - t[f"{k}_growth_old"]
    t.round(4).to_csv(RES / "gdp_revisions.csv")
    # 内訳（名目、2024年と2019年）
    comp = p[(p.kind == "nominal") & (p.item != "gdp")].copy()
    comp["rev"] = comp[NEW] - comp[OLD]
    comp.loc[comp.item == "imports", "rev"] *= -1   # 輸入は GDP から差し引く
    cw = comp.pivot(index="year", columns="item", values="rev") / 1000
    cw["sum_components"] = cw.sum(axis=1)
    cw["gdp_rev"] = t.nominal_level_rev_trillion
    cw.round(4).to_csv(RES / "nominal_revision_by_component.csv")
    def ann(s, a, b):
        return float(((s.loc[b] / s.loc[a]) ** (1 / (b - a)) - 1) * 100)
    r_old = ann(real[OLD], 1994, 2024); r_new = ann(real[NEW], 1994, 2024)
    rg = t.real_growth_rev.loc[1995:2024]
    hyp = {
        "H1": dict(rule="2024年の名目GDPが3%以上上に書き換わったら支持", value=float(t.loc[2024, "nominal_level_rev_pct"]), verdict="支持" if t.loc[2024, "nominal_level_rev_pct"] >= 3 else "外れ"),
        "H2": dict(rule="実質の前年比の書き換えの絶対値の平均（1995〜2024年）が0.5ポイント以下なら支持", value=float(rg.abs().mean()), verdict="支持" if rg.abs().mean() <= 0.5 else "外れ"),
        "H3": dict(rule="名目の水準の書き換え（%）の平均が1994〜99年より2020〜24年の方が大きければ支持", y1990s=float(t.loc[1994:1999, "nominal_level_rev_pct"].mean()),
                   y2020s=float(t.loc[2020:2024, "nominal_level_rev_pct"].mean()),
                   verdict="支持" if t.loc[2020:2024, "nominal_level_rev_pct"].mean() > t.loc[1994:1999, "nominal_level_rev_pct"].mean() else "外れ"),
        "H4": dict(rule="1994〜2024年の実質の年率の平均の変化が0.1ポイント未満なら支持", old=r_old, new=r_new, diff=r_new - r_old, verdict="支持" if abs(r_new - r_old) < 0.1 else "外れ"),
    }
    rob = []
    for a, b in [(1995, 2019), (2010, 2024), (1995, 2024)]:
        q = t.loc[a:b]
        rob.append(dict(check=f"{a}〜{b}年", real_abs_mean=float(q.real_growth_rev.abs().mean()), nominal_abs_mean=float(q.nominal_growth_rev.abs().mean()),
                        deflator_abs_mean=float(q.deflator_growth_rev.abs().mean()), real_max_abs=float(q.real_growth_rev.abs().max()),
                        real_max_year=int(q.real_growth_rev.abs().idxmax())))
    top = int(rg.abs().idxmax())
    rob.append(dict(check=f"最大の書き換えの年（{top}年）を除く 1995〜2024年", real_abs_mean=float(rg.drop(top).abs().mean()), nominal_abs_mean=np.nan, deflator_abs_mean=np.nan,
                    real_max_abs=float(rg.drop(top).abs().max()), real_max_year=int(rg.drop(top).abs().idxmax())))
    rb = pd.DataFrame(rob)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    c24 = cw.loc[2024].drop(["sum_components", "gdp_rev"]).sort_values(key=lambda s: -s.abs())
    main_ = dict(hypotheses=hyp, robustness=rb.round(4).to_dict(orient="records"),
                 nominal_2024_old=float(t.loc[2024, "nominal_old"]), nominal_2024_new=float(t.loc[2024, "nominal_new"]),
                 rev_2024_trillion=float(t.loc[2024, "nominal_level_rev_trillion"]), rev_2024_pct=float(t.loc[2024, "nominal_level_rev_pct"]),
                 rev_1994_pct=float(t.loc[1994, "nominal_level_rev_pct"]), rev_2015_pct=float(t.loc[2015, "nominal_level_rev_pct"]), rev_2019_pct=float(t.loc[2019, "nominal_level_rev_pct"]),
                 rev_max_year=int(t.nominal_level_rev_pct.idxmax()), rev_max_pct=float(t.nominal_level_rev_pct.max()),
                 rev_min_year=int(t.nominal_level_rev_pct.idxmin()), rev_min_pct=float(t.nominal_level_rev_pct.min()),
                 components_2024=c24.round(3).to_dict(), sum_components_2024=float(cw.loc[2024, "sum_components"]),
                 real_growth_rev_max_year=top, real_growth_rev_max=float(rg.loc[top]),
                 sign_changes_real=int(((t.real_growth_old > 0) != (t.real_growth_new > 0)).loc[1995:2024].sum()),
                 sign_change_years=[int(y) for y in t.loc[1995:2024].index[((t.real_growth_old > 0) != (t.real_growth_new > 0)).loc[1995:2024]]])
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(hyp, ensure_ascii=False)); print(rb.round(3).to_string())
    print({k: v_ for k, v_ in main_.items() if k not in ("hypotheses", "robustness")})
    print(t[["nominal_level_rev_pct", "real_growth_old", "real_growth_new", "real_growth_rev"]].round(2).to_string())


if __name__ == "__main__":
    main()
