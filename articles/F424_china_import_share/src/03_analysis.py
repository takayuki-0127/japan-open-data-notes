"""03 分析：中国の割合（総額・品目別）、2015→2025年の変化、ASEAN への移り、集中度、頑健性。
出力：results/main.json, results/total_share.csv, results/item_shares.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
LEAF = ["'007'", "'003'", "'009'", "'01103'", "'01101'", "'20701'", "'21505'", "'21501'", "'20307'", "'30301'", "'30303'",
        "'3050103'", "'3050101'", "'30101'", "'50101'", "'507'", "'613'", "'615'", "'617'", "'609'", "'611'", "'605'",
        "'70101'", "'7010505'", "'7010507'", "'70311'", "'70304'", "'70305'", "'70301'", "'70307'", "'70313'",
        "'70501'", "'70503'", "'70505'", "'81101'", "'807'", "'803'", "'805'"]
PARTNERS = ["china", "asean", "korea", "usa", "eu", "middle_east", "russia"]
TOTAL = "'0'～'9'"


def shares(d):
    w = d.pivot_table(index=["code", "year"], columns="partner", values="value_thousand_yen", aggfunc="sum")
    s = w[PARTNERS].div(w["world"], axis=0) * 100
    s["other"] = 100 - s[PARTNERS].sum(axis=1)
    s["hhi"] = (s[PARTNERS + ["other"]] ** 2).sum(axis=1) / 1e4
    s["world"] = w["world"]
    return s


def compare(s, items, y0, y1, thr=30, avg=0):
    def val(c, y, col):
        if avg:
            return s.loc[(c, slice(y - avg, y + avg)), col].mean()
        return s.loc[(c, y), col]
    rows = []
    for c in items:
        rows.append(dict(code=c, cn0=val(c, y0, "china"), cn1=val(c, y1, "china"), as0=val(c, y0, "asean"), as1=val(c, y1, "asean"),
                         w1=val(c, y1, "world")))
    t = pd.DataFrame(rows)
    hi = t[t.cn0 >= thr]
    down = t[t.cn1 < t.cn0]
    return t, dict(n_items=len(t), n_hi=len(hi), n_hi_down=int((hi.cn1 < hi.cn0).sum()),
                   share_hi_down=float((hi.cn1 < hi.cn0).mean() * 100) if len(hi) else np.nan,
                   n_down=len(down), n_down_asean_up=int((down.as1 > down.as0).sum()),
                   share_down_asean_up=float((down.as1 > down.as0).mean() * 100) if len(down) else np.nan,
                   wavg_change=float(np.average(t.cn1 - t.cn0, weights=t.w1)))


def main():
    d = pd.read_csv(D / "imports_long.csv")
    items = pd.read_csv(D / "items.csv").set_index("code")
    s = shares(d)
    tot = s.loc[TOTAL].copy()
    # 鉱物性燃料を除く総額
    w = d.pivot_table(index=["code", "year"], columns="partner", values="value_thousand_yen", aggfunc="sum")
    ex = w.loc[TOTAL] - w.loc["'3'"]
    tot["china_ex_fuel"] = ex.china / ex.world * 100
    tot["asean_ex_fuel"] = ex.asean / ex.world * 100
    tot.round(4).to_csv(R / "total_share.csv")
    t, c = compare(s, LEAF, 2015, 2025)
    t["item"] = items.loc[t.code, "press_name"].values
    t["change"] = t.cn1 - t.cn0
    t["asean_change"] = t.as1 - t.as0
    t.round(3).to_csv(R / "item_shares.csv", index=False)
    pk = int(tot.china.idxmax())
    g = lambda code, y: float(s.loc[(code, y), "china"])
    main = dict(china_share_2025=float(tot.loc[2025, "china"]), china_share_2015=float(tot.loc[2015, "china"]),
                china_share_peak_year=pk, china_share_peak=float(tot.china.max()), china_share_1988=float(tot.loc[1988, "china"]),
                china_share_2000=float(tot.loc[2000, "china"]), asean_share_2015=float(tot.loc[2015, "asean"]), asean_share_2025=float(tot.loc[2025, "asean"]),
                china_ex_fuel_2025=float(tot.loc[2025, "china_ex_fuel"]), china_ex_fuel_peak_year=int(tot.china_ex_fuel.idxmax()),
                china_ex_fuel_peak=float(tot.china_ex_fuel.max()),
                hhi_total_2015=float(tot.loc[2015, "hhi"]), hhi_total_2025=float(tot.loc[2025, "hhi"]),
                **{k: v for k, v in c.items()},
                computer_2015=g("'7010505'", 2015), computer_2025=g("'7010505'", 2025),
                telecom_2015=g("'70307'", 2015), telecom_2025=g("'70307'", 2025),
                phone_2025=g("'7030703'", 2025), clothes_2015=g("'807'", 2015), clothes_2025=g("'807'", 2025),
                bags_2025=g("'805'", 2025), furniture_2025=g("'803'", 2025))
    main["H1"] = "支持" if pk != 2025 else "外れ"
    main["H2"] = "支持" if c["share_hi_down"] > 50 else "外れ"
    main["H3"] = "支持" if c["share_down_asean_up"] > 50 else "外れ"
    main["H4"] = "支持" if main["computer_2025"] >= 40 and main["telecom_2025"] >= 40 else "外れ"
    rob = [dict(check="本線（2015年 対 2025年、しきい値30%）", **c)]
    _, c2 = compare(s, LEAF, 2015, 2024, avg=1); rob.append(dict(check="3年平均（2014〜16年 対 2023〜25年）", **c2))
    for thr in (20, 40):
        _, c3 = compare(s, LEAF, 2015, 2025, thr=thr); rob.append(dict(check=f"しきい値{thr}%", **c3))
    _, c4 = compare(s, [x for x in LEAF if not x.startswith("'30") and not x.startswith("'3050")], 2015, 2025); rob.append(dict(check="燃料の品目を除く", **c4))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(t.sort_values("cn0", ascending=False)[["item", "cn0", "cn1", "as0", "as1", "w1"]].round(1).to_string())


if __name__ == "__main__":
    main()
