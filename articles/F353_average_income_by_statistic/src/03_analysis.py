"""2025年の「平均年収」を定義ごとに並べ、差を分ける。仮説の判定と頑健性（オフライン、乱数なし）。単位は万円/年。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def median_from_brackets(df, count_col, method="linear"):
    """給与階級（上限つき）の人数から中央値（万円）。階級の中で人数が均等（linear）または対数で均等（log）に並ぶとする。"""
    d = df[np.isfinite(df.upper_man)].sort_values("upper_man").copy()
    top = df[~np.isfinite(df.upper_man)][count_col].sum()
    n = d[count_col].sum() + top
    cum = 0.0; lo = 0.0
    for _, r in d.iterrows():
        hi = r.upper_man
        if cum + r[count_col] >= n / 2:
            f = (n / 2 - cum) / r[count_col]
            if method == "log" and lo > 0:
                return float(np.exp(np.log(lo) + f * (np.log(hi) - np.log(lo))))
            return float(lo + f * (hi - lo))
        cum += r[count_col]; lo = hi
    return np.nan


def share_below(df, count_col, x):
    d = df.sort_values("upper_man"); n = d[count_col].sum(); cum = 0.0; lo = 0.0
    for _, r in d.iterrows():
        hi = r.upper_man
        if x <= hi:
            return float((cum + r[count_col] * (x - lo) / (hi - lo)) / n)
        cum += r[count_col]; lo = hi
    return 1.0


def main():
    RES.mkdir(exist_ok=True)
    a = pd.read_csv(ROOT / "data" / "nta_brackets_2025.csv")
    yrs = pd.read_csv(ROOT / "data" / "nta_brackets_years.csv")
    mk = pd.read_csv(ROOT / "data" / "maikin_2025.csv").set_index(["size", "form"])
    br = lambda kind, sex: a[(a.kind == kind) & (a.sex == sex) & (a.bracket != "計")]
    tot = lambda kind, sex: a[(a.kind == kind) & (a.sex == sex) & (a.bracket == "計")].iloc[0]
    def mean_of(kind, sex):
        t = tot(kind, sex); return float(t.total_million / t.persons * 100)  # 百万円/人 → 万円
    full = mean_of("1年勤務", "計")
    t1, t2 = tot("1年勤務", "計"), tot("1年未満", "計")
    allp = float((t1.total_million + t2.total_million) / (t1.persons + t2.persons) * 100)
    med = median_from_brackets(br("1年勤務", "計"), "persons")
    med_log = median_from_brackets(br("1年勤務", "計"), "persons", "log")
    both = br("1年勤務", "計")[["bracket", "upper_man"]].copy()
    both["persons"] = br("1年勤務", "計").persons.values + br("1年未満", "計").persons.values
    med_all = median_from_brackets(both, "persons")
    mk12 = lambda s, f, col="cash_total": float(mk.loc[(s, f), col] * 12 / 1e4)
    defs = [
        ("国税庁：1年を通じて勤務した人の平均", full, "全体"),
        ("国税庁：1年未満勤続の人も含めた平均", allp, "全体"),
        ("国税庁：1年を通じて勤務した人の中央値", med, "中央値"),
        ("国税庁：1年勤務・2か所目以降の給与（乙欄）を除く平均", mean_of("1年勤務（乙欄除く）", "計"), "参考"),
        ("国税庁：1年勤務の男性の平均", mean_of("1年勤務", "男"), "男女"),
        ("国税庁：1年勤務の女性の平均", mean_of("1年勤務", "女"), "男女"),
        ("毎月勤労：5人以上・就業形態計 ×12", mk12("5人以上", "就業形態計"), "全体"),
        ("毎月勤労：30人以上・就業形態計 ×12", mk12("30人以上", "就業形態計"), "全体"),
        ("毎月勤労：5人以上・一般労働者 ×12", mk12("5人以上", "一般労働者"), "フルタイム"),
        ("毎月勤労：30人以上・一般労働者 ×12", mk12("30人以上", "一般労働者"), "フルタイム"),
        ("毎月勤労：5人以上・パートタイム ×12", mk12("5人以上", "パートタイム労働者"), "パート"),
        ("毎月勤労：5人以上・一般労働者の所定内給与 ×12（賞与・残業なし）", mk12("5人以上", "一般労働者", "scheduled"), "フルタイム"),
    ]
    df = pd.DataFrame(defs, columns=["definition", "annual_man", "group"])
    df.round(2).to_csv(RES / "definitions_2025.csv", index=False)
    overall = df[df.group == "全体"].annual_man
    mk_all, mk_gen = mk12("5人以上", "就業形態計"), mk12("5人以上", "一般労働者")
    hyp = {
        "H1": dict(rule="「全体の平均」とされる4つの数字の最大÷最小が1.5以上なら支持", max=float(overall.max()), min=float(overall.min()), ratio=float(overall.max() / overall.min()),
                   verdict="支持" if overall.max() / overall.min() >= 1.5 else "外れ"),
        "H2": dict(rule="国税庁の中央値が平均より70万円以上低ければ支持", mean=full, median=med, gap=full - med, verdict="支持" if full - med >= 70 else "外れ"),
        "H3": dict(rule="毎月勤労の一般−就業形態計の差が、国税庁平均−毎月勤労（就業形態計）の差より大きければ支持", part_gap=mk_gen - mk_all, nta_vs_mk=full - mk_all,
                   verdict="支持" if (mk_gen - mk_all) > abs(full - mk_all) else "外れ"),
        "H4": dict(rule="1年未満勤続を含めると50万円以上下がれば支持", full=full, all=allp, drop=full - allp, verdict="支持" if full - allp >= 50 else "外れ"),
    }
    # 毎月勤労の賞与・残業の分（一般労働者、5人以上）
    g = mk.loc[("5人以上", "一般労働者")]
    parts = dict(scheduled=float(g.scheduled * 12 / 1e4), overtime=float(g.overtime * 12 / 1e4), special=float(g.special * 12 / 1e4))
    # 頑健性
    rob = [dict(check="中央値：階級の中で直線に並ぶ（本線）", value=med), dict(check="中央値：階級の中で対数で並ぶ", value=med_log),
           dict(check="中央値：1年未満勤続を含む", value=med_all)]
    for sx in ["男", "女"]:
        rob.append(dict(check=f"{sx}性：平均", value=mean_of("1年勤務", sx)))
        rob.append(dict(check=f"{sx}性：中央値", value=median_from_brackets(br("1年勤務", sx), "persons")))
    # 2024年：国税庁は累年、毎月勤労は前年比から逆算
    y24 = yrs[(yrs.year == 2024) & (yrs.sex == "計")]
    t24 = y24[y24.bracket == "計"].iloc[0]
    nta24_mean = float(t24.total_million / t24.persons_thousand / 10)
    nta24_med = median_from_brackets(y24[y24.bracket != "計"], "persons_thousand")
    mk24_all = mk_all / (1 + mk.loc[("5人以上", "就業形態計"), "cash_total_yoy"] / 100)
    mk24_gen = mk_gen / (1 + mk.loc[("5人以上", "一般労働者"), "cash_total_yoy"] / 100)
    rob += [dict(check="2024年 国税庁 1年勤務の平均", value=nta24_mean), dict(check="2024年 国税庁 1年勤務の中央値", value=nta24_med),
            dict(check="2024年 毎月勤労 5人以上・就業形態計 ×12（前年比から逆算）", value=float(mk24_all)),
            dict(check="2024年 毎月勤労 5人以上・一般労働者 ×12（前年比から逆算）", value=float(mk24_gen))]
    rb = pd.DataFrame(rob)
    rb.round(2).to_csv(RES / "robustness.csv", index=False)
    main_ = dict(definitions=df.round(2).to_dict(orient="records"), hypotheses=hyp, maikin_general_parts=parts, robustness=rb.round(2).to_dict(orient="records"),
                 nta_full_mean=full, nta_all_mean=allp, nta_median=med, nta_median_log=med_log, mk_all=mk_all, mk_general=mk_gen,
                 mk_30_all=mk12("30人以上", "就業形態計"), mk_part=mk12("5人以上", "パートタイム労働者"),
                 nta_full_persons=float(t1.persons), nta_short_persons=float(t2.persons), nta_short_mean=mean_of("1年未満", "計"),
                 share_below_mean=share_below(br("1年勤務", "計"), "persons", full))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(df.round(1).to_string()); print(json.dumps(hyp, ensure_ascii=False)); print(parts); print(rb.round(1).to_string()); print(main_["share_below_mean"], main_["nta_short_mean"])


if __name__ == "__main__":
    main()
