"""03 分析：X-13ARIMA-SEATS と STL で自分で季節調整し、公表の季節調整値と比べる

1. 鉱工業生産・出荷：経済産業省の説明どおりに設定（12年の計算期間、2曜日調整＋日本の祝日、年に1度の年間補正）
2. 労働力調査6系列：総務省の説明どおりに設定（前年12月までのデータで当年の季節指数を予測し、過去10年分を再計算）
3. 有効求人倍率：公表元の細かい設定は確認していないので、標準的な設定で比べる
4. 曜日・祝日・うるう年の効果の大きさ
5. STL との比較
6. 最新の月が加わったときの改定（毎月計算し直す方式 vs 年に1度だけ計算する方式）
出力: results/*.csv
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, run_x13, stl_adjust, compare, jp_holiday_var

RES.mkdir(exist_ok=True)
S = pd.read_csv(DATA / "series.csv", parse_dates=["date"])
G = {k: v.set_index("date").sort_index() for k, v in S.groupby("series")}
PF = pd.read_csv(DATA / "lfs_factors_pub.csv", parse_dates=["date"], index_col="date")
LFS = ["労働力人口", "就業者", "雇用者", "完全失業者", "非労働力人口", "完全失業率"]
IIP = ["鉱工業生産", "鉱工業出荷"]
IIP_SPEC = dict(td=True, holiday=True, lpyear=True, arima="auto", outliers=True)
LFS_SPEC = dict(td=False, holiday=False, arima="auto", outliers=True, sigmalim=(9.8, 9.9))  # 総務省の説明：管理限界 9.8σ〜9.9σ


def iip_vintage(y, spec=IIP_SPEC):
    """経済産業省の年間補正をまねて、年ごとに計算期間を変えた季節指数（季節要素×暦要素）をつなぐ。
    2018〜2022年：2011〜2022年のデータ（2020年基準の改定時）、2023年：2012〜2023年、
    2024年：2013〜2024年、2025年：2014〜2025年、2026年：2025年の計算の予測値"""
    plan = [(("2011-01", "2022-12"), range(2018, 2023)), (("2012-01", "2023-12"), [2023]),
            (("2013-01", "2024-12"), [2024]), (("2014-01", "2025-12"), [2025, 2026])]
    parts, models = [], {}
    for span, years in plan:
        r = run_x13(y, span=span, name="iip", **spec)
        if not r["ok"]:
            raise RuntimeError(r["err"])
        sf = r["sf"]
        parts.append(sf[sf.index.year.isin(list(years))])
        models[f"{span[0][:4]}-{span[1][:4]}"] = {"model": r["model"],
                                                  "reg": r["est"][r["est"].part == "reg"][["variable", "estimate", "se"]].to_dict("records")}
    return pd.concat(parts).sort_index(), models, r


def main():
    out_cmp, out_models = [], {}
    fac_rows = []

    # ---------- 1. 鉱工業
    for k in IIP:
        y = G[k]
        sf, models, r_last = iip_vintage(y.nsa)
        out_models[k] = models
        mine_sa = y.nsa / sf * 100
        pubf = y.nsa / y.sa_pub * 100
        for a, b, lab in [("2018-01", "2024-12", "2018〜2024年"), ("2025-01", "2025-12", "2025年"),
                          ("2026-01", "2026-08", "2026年（予測した季節指数）")]:
            c = compare(mine_sa, y.sa_pub, a, b)
            d = (sf - pubf)[a:b].abs()
            c.update({"系列": k, "期間": lab, "季節指数の差の平均": d.mean(), "季節指数の差の最大": d.max(), "設定": "公表元の説明どおり"})
            out_cmp.append(c)
        # 暦の要素を入れない場合（比較用）
        sf0, _, _ = iip_vintage(y.nsa, spec=dict(td=False, holiday=False, arima="auto", outliers=True))
        for a, b, lab in [("2018-01", "2024-12", "2018〜2024年"), ("2025-01", "2025-12", "2025年"),
                          ("2026-01", "2026-08", "2026年（予測した季節指数）")]:
            c = compare(y.nsa / sf0 * 100, y.sa_pub, a, b)
            c.update({"系列": k, "期間": lab, "季節指数の差の平均": (sf0 - pubf)[a:b].abs().mean(),
                      "季節指数の差の最大": (sf0 - pubf)[a:b].abs().max(), "設定": "曜日・祝日の調整なし"})
            out_cmp.append(c)
        f = pd.DataFrame({"原数値": y.nsa, "公表_季節調整値": y.sa_pub, "公表_季節指数（逆算）": pubf,
                          "自作_季節指数": sf, "自作_季節調整値": mine_sa,
                          "自作_季節要素": r_last["seas"], "自作_暦要素": r_last["cal"],
                          "自作_季節指数_暦なし": sf0})
        f["系列"] = k
        fac_rows.append(f["2011":])

    # ---------- 2. 労働力調査（1990年1月〜2025年12月で計算。2016〜2025年の再計算値と2026年の予測値が公表と比べられる）
    for k in LFS:
        y = G[k]
        r = run_x13(y.nsa, span=("1990-01", "2025-12"), name="lfs", **LFS_SPEC)
        out_models[k] = {"1990-2025": {"model": r["model"],
                                       "reg": r["est"][r["est"].part == "reg"][["variable", "estimate", "se"]].to_dict("records")}}
        sf = r["sf"]
        pub = PF[k]
        mine_sa = y.nsa / sf * 100
        rate = k == "完全失業率"
        for a, b, lab in [("2016-01", "2025-12", "2016〜2025年（再計算された期間）"), ("2026-01", "2026-08", "2026年（予測した季節指数）")]:
            c = compare(mine_sa, y.sa_pub, a, b, rate=rate, ndigits=1 if rate else None)
            d = (sf - pub)[a:b].abs()
            c.update({"系列": k, "期間": lab, "季節指数の差の平均": d.mean(), "季節指数の差の最大": d.max(), "設定": "公表元の説明どおり"})
            out_cmp.append(c)
        f = pd.DataFrame({"原数値": y.nsa, "公表_季節調整値": y.sa_pub, "公表_季節指数": pub,
                          "自作_季節指数": sf, "自作_季節調整値": mine_sa})
        f["系列"] = k
        fac_rows.append(f["2011":])

    # 失業率：直接調整と、季節調整済みの失業者÷労働力人口の比較（公表値は0.1%刻み）
    w = S.pivot(index="date", columns="series", values="sa_pub")
    ind = (w["完全失業者"] / w["労働力人口"] * 100).round(1)
    r = run_x13(G["完全失業率"].nsa, span=("1990-01", "2025-12"), **LFS_SPEC)
    direct = r["sa"].round(1)
    rate_chk = {"間接（失業者÷労働力人口）が公表値と一致した割合_2000-2026": float(((ind - w["完全失業率"])["2000":].abs() < 0.051).mean()),
                "直接（率をそのまま調整）が公表値と一致した割合_2016-2025": float(((direct - w["完全失業率"])["2016":"2025"].abs() < 0.051).mean())}

    # ---------- 3. 有効求人倍率（設定は確認していないので、標準的な2通り）
    y = G["有効求人倍率"]
    for lab, kw in [("対数・ARIMA自動・外れ値自動", dict(arima="auto", outliers=True)),
                    ("対数・ARIMA自動・外れ値自動・曜日祝日あり", dict(arima="auto", outliers=True, td=True, holiday=True))]:
        r = run_x13(y.nsa, span=("1990-01", "2025-12"), name="jobs", **kw)
        mine_sa = y.nsa / r["sf"] * 100
        for a, b, plab in [("2016-01", "2025-12", "2016〜2025年"), ("2026-01", "2026-08", "2026年（予測した季節指数）")]:
            c = compare(mine_sa, y.sa_pub, a, b, rate=True, ndigits=2)
            pubf = y.nsa / y.sa_pub * 100
            c.update({"系列": "有効求人倍率", "期間": plab, "季節指数の差の平均": (r["sf"] - pubf)[a:b].abs().mean(),
                      "季節指数の差の最大": (r["sf"] - pubf)[a:b].abs().max(), "設定": lab})
            out_cmp.append(c)
        out_models[f"有効求人倍率（{lab}）"] = {"model": r["model"]}
        f = pd.DataFrame({"原数値": y.nsa, "公表_季節調整値": y.sa_pub, "自作_季節指数": r["sf"], "自作_季節調整値": mine_sa})
        f["系列"] = "有効求人倍率" if "曜日" not in lab else "有効求人倍率（曜日祝日あり）"
        fac_rows.append(f["2011":])

    cmp = pd.DataFrame(out_cmp)
    cols = ["系列", "設定", "期間", "月数", "季節指数の差の平均", "季節指数の差の最大", "水準の差の平均", "水準の差の最大",
            "前月比の差の平均", "前月比の相関", "前月比の向きの一致率", "単位"]
    cmp[cols].round(3).to_csv(RES / "compare_with_published.csv", index=False)
    pd.concat(fac_rows).to_csv(RES / "factors_mine_vs_published.csv")
    (RES / "models.json").write_text(json.dumps({"models": out_models, "unemployment_rate_check": rate_chk},
                                                ensure_ascii=False, indent=1, default=float))
    print(cmp[cols].round(3).to_string())
    print(rate_chk)

    # ---------- 4. 曜日・祝日・うるう年の効果（鉱工業生産、2014〜2025年の計算）
    cal_rows = []
    for k in IIP + ["完全失業者", "就業者", "有効求人倍率"]:
        span = ("2014-01", "2025-12") if k in IIP else ("1990-01", "2025-12")
        r = run_x13(G[k].nsa, span=span, td=True, holiday=True, arima="auto", outliers=True)
        e = r["est"][r["est"].part == "reg"]
        for _, row in e.iterrows():
            if row["variable"] in ("Weekday", "hol"):
                cal_rows.append({"系列": k, "変数": "平日1日（土日との入れ替え）" if row["variable"] == "Weekday" else "平日の祝日1日",
                                 "係数": row["estimate"], "標準誤差": row["se"], "t値": row["estimate"] / row["se"]})
    cal = pd.DataFrame(cal_rows)
    # 解釈しやすい形：平日が1日増え土曜か日曜が1日減ると td1coef 変数は 1+2.5=3.5 増える
    cal["効果（%）"] = np.where(cal["変数"].str.startswith("平日1日"), (np.exp(cal["係数"] * 3.5) - 1) * 100,
                             (np.exp(cal["係数"]) - 1) * 100)
    cal.round(5).to_csv(RES / "calendar_effects.csv", index=False)
    print(cal.round(4).to_string())

    # 鉱工業生産の暦要素の月ごとの幅
    r = run_x13(G["鉱工業生産"].nsa, span=("2014-01", "2025-12"), **IIP_SPEC)
    calf = r["cal"]
    hv = jp_holiday_var("2014-01", calf.index[-1].strftime("%Y-%m"))
    cdf = pd.DataFrame({"暦要素": calf})
    idx = pd.period_range(calf.index[0], calf.index[-1], freq="M")
    cdf["平日数"] = [sum(1 for d in pd.date_range(p.start_time, p.end_time) if d.weekday() < 5) for p in idx]
    import holidays
    jp = holidays.Japan(years=range(2014, 2028))
    cdf["平日の祝日数"] = [sum(1 for d in pd.date_range(p.start_time, p.end_time) if d.weekday() < 5 and d.date() in jp) for p in idx]
    cdf["稼働日数（平日−平日の祝日）"] = cdf["平日数"] - cdf["平日の祝日数"]
    cdf.to_csv(RES / "iip_calendar_factor.csv")
    print("暦要素の範囲", round(calf.min(), 2), round(calf.max(), 2))

    # ---------- 5. STL との比較
    stl_rows = []
    for k, a, b in [("鉱工業生産", "2018-01", "2025-12"), ("就業者", "2016-01", "2025-12"), ("完全失業者", "2016-01", "2025-12")]:
        y = G[k]
        span = ("2014-01", "2025-12") if k in IIP else ("1990-01", "2025-12")
        yy = y.nsa[span[0]:span[1]]
        sa_stl, sf_stl = stl_adjust(yy)
        for lab, sa in [("STL", sa_stl)]:
            c = compare(sa, y.sa_pub, a, b)
            c.update({"系列": k, "方法": lab})
            stl_rows.append(c)
        spec = IIP_SPEC if k in IIP else LFS_SPEC
        r = run_x13(y.nsa, span=span, **spec)
        c = compare(y.nsa / r["sf"] * 100, y.sa_pub, a, b)
        c.update({"系列": k, "方法": "X-13（全期間を1回で計算）"})
        stl_rows.append(c)
        if k in IIP:
            r0 = run_x13(y.nsa, span=span, td=False, holiday=False, arima="auto", outliers=True)
            c = compare(y.nsa / r0["sf"] * 100, y.sa_pub, a, b)
            c.update({"系列": k, "方法": "X-13（曜日・祝日の調整なし）"})
            stl_rows.append(c)
        pd.DataFrame({"原数値": yy, "公表": y.sa_pub[span[0]:span[1]], "STL": sa_stl, "X-13": (y.nsa / r["sf"] * 100)[span[0]:span[1]]}
                     ).to_csv(RES / f"stl_vs_x13_{k}.csv")
    stl = pd.DataFrame(stl_rows)
    stl.round(3).to_csv(RES / "stl_vs_x13.csv", index=False)
    print(stl.round(3).to_string())

    # ---------- 6. 改定：最新月が加わると前月比はどれだけ変わるか
    rev_rows = []
    for k, spec, start in [("鉱工業生産", IIP_SPEC, "2014-01"), ("完全失業者", LFS_SPEC, "1990-01"), ("就業者", LFS_SPEC, "1990-01")]:
        y = G[k].nsa
        months = pd.date_range("2023-01-01", "2025-08-01", freq="MS")
        final = run_x13(y, span=(start, "2026-08"), **spec)["sa"]
        # 年に1度の方式：前年12月までで計算し、当年は予測した季節指数を使う
        yearly = {}
        for yr in [2022, 2023, 2024, 2025]:
            yearly[yr + 1] = run_x13(y, span=(start, f"{yr}-12"), **spec)["sf"]
        for t in months:
            r = run_x13(y, span=(start, t.strftime("%Y-%m")), **spec)
            first_mom = (r["sa"].iloc[-1] / r["sa"].iloc[-2] - 1) * 100
            fin_mom = (final.loc[t] / final.loc[t - pd.DateOffset(months=1)] - 1) * 100
            sf_y = yearly[t.year]
            y_sa = y / sf_y * 100
            proj_mom = (y_sa.loc[t] / y_sa.loc[t - pd.DateOffset(months=1)] - 1) * 100
            rev_rows.append({"系列": k, "月": t, "毎月計算_初回の前月比": first_mom, "年1回_初回の前月比": proj_mom,
                             "2026年8月までで計算した前月比": fin_mom})
    rev = pd.DataFrame(rev_rows)
    rev["毎月計算_改定幅"] = rev["2026年8月までで計算した前月比"] - rev["毎月計算_初回の前月比"]
    rev["年1回_改定幅"] = rev["2026年8月までで計算した前月比"] - rev["年1回_初回の前月比"]
    rev.round(4).to_csv(RES / "revisions.csv", index=False)
    summ = rev.groupby("系列").agg(毎月計算_改定幅の平均絶対値=("毎月計算_改定幅", lambda s: s.abs().mean()),
                                  年1回_改定幅の平均絶対値=("年1回_改定幅", lambda s: s.abs().mean()),
                                  毎月計算_向きが変わった割合=("毎月計算_改定幅", lambda s: np.nan),
                                  月数=("月", "count"))
    for k in summ.index:
        d = rev[rev["系列"] == k]
        summ.loc[k, "毎月計算_向きが変わった割合"] = (np.sign(d["毎月計算_初回の前月比"]) != np.sign(d["2026年8月までで計算した前月比"])).mean() * 100
        summ.loc[k, "年1回_向きが変わった割合"] = (np.sign(d["年1回_初回の前月比"]) != np.sign(d["2026年8月までで計算した前月比"])).mean() * 100
    summ.round(3).to_csv(RES / "revisions_summary.csv")
    print(summ.round(3).to_string())


if __name__ == "__main__":
    main()
