"""03 分析：梅雨の時期の降水量（平年比）の変化・振れ幅・極端な年・期間の長さとの関係"""
import json, pathlib
import numpy as np, pandas as pd
from scipy.stats import theilslopes, kendalltau

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
REG = ["沖縄", "奄美", "九州南部", "九州北部", "四国", "中国", "近畿", "東海", "関東甲信", "北陸", "東北南部", "東北北部"]


def load(drop_south=False):
    d = pd.read_csv(ROOT / "data" / "panel.csv")
    d = d[(d.year >= 1951) & (d.year <= 2025)]
    if drop_south:
        d = d[~d.region.isin(["沖縄", "奄美"])]
    return d.copy()


def summarize(d, label, a=(1951, 1987), b=(1988, 2025), hi=150, lo=50, agg="mean"):
    A, B = d[d.year.between(*a)], d[d.year.between(*b)]
    regs = [r for r in REG if r in set(d.region)]
    ya = d.groupby("year").ratio.agg(agg)
    sd = pd.DataFrame({"sd0": A.groupby("region").ratio.std(), "sd1": B.groupby("region").ratio.std()}).reindex(regs)
    mk = []
    for r in regs:
        g = d[d.region == r]
        tau, p = kendalltau(g.year, g.ratio)
        mk.append((r, tau, p, theilslopes(g.ratio, g.year)[0] * 10))
    mk = pd.DataFrame(mk, columns=["region", "tau", "p", "theil10"])
    x = d.dropna(subset=["length"]).copy()
    x["r_dm"] = x.ratio - x.groupby("region").ratio.transform("mean")
    x["l_dm"] = x.length - x.groupby("region").length.transform("mean")
    return dict(label=label, mean0=float(ya[ya.index.to_series().between(*a)].mean()), mean1=float(ya[ya.index.to_series().between(*b)].mean()),
                n_up_sig=int(((mk.tau > 0) & (mk.p < 0.05)).sum()), n_up=int((mk.tau > 0).sum()), n_reg=len(regs),
                hi0=float((A.ratio >= hi).mean()), hi1=float((B.ratio >= hi).mean()),
                lo0=float((A.ratio <= lo).mean()), lo1=float((B.ratio <= lo).mean()),
                n_sd_up=int((sd.sd1 > sd.sd0).sum()), sd0_mean=float(sd.sd0.mean()), sd1_mean=float(sd.sd1.mean()),
                corr_len=float(np.corrcoef(x.r_dm, x.l_dm)[0, 1])), mk, sd


def main():
    d = load()
    m, mk, sd = summarize(d, "基本（12地域、1951〜1987年 → 1988〜2025年、150%・50%）")
    mk.round(4).to_csv(RES / "region_trends.csv", index=False)
    sd.round(3).to_csv(RES / "region_sd.csv")
    ya = d.groupby("year").agg(mean_ratio=("ratio", "mean"), n_hi=("ratio", lambda s: int((s >= 150).sum())),
                               n_lo=("ratio", lambda s: int((s <= 50).sum()))).reset_index()
    ya.round(3).to_csv(RES / "yearly.csv", index=False)
    rob = [m]
    rob.append(summarize(d, "30年ずつ（1951〜1980年 → 1996〜2025年）", a=(1951, 1980), b=(1996, 2025))[0])
    rob.append(summarize(load(True), "沖縄・奄美を除く10地域")[0])
    rob.append(summarize(d, "基準を140%・60%", hi=140, lo=60)[0])
    rob.append(summarize(d, "基準を160%・40%", hi=160, lo=40)[0])
    rob.append(summarize(d, "地域の中央値で", agg="median")[0])
    R = pd.DataFrame(rob)
    R.round(4).to_csv(RES / "robustness.csv", index=False)

    # 問い直し：とても多い年は、同じ年に何地域で重なったか（広い範囲の大雨の梅雨）
    many = ya[ya.n_hi >= 4][["year", "n_hi"]]
    # 期間の長さの変化（参考）と、梅雨明けを特定しなかった年
    x = d.copy()
    nolen = x[x.length.isna()].groupby(np.where(x[x.length.isna()].year <= 1987, "前半", "後半")).size().to_dict()
    out = dict(main=m, years_4plus_hi=many.values.tolist(),
               n_years_4plus_hi0=int((many.year <= 1987).sum()), n_years_4plus_hi1=int((many.year >= 1988).sum()),
               no_length=nolen,
               wettest=ya.sort_values("mean_ratio", ascending=False).head(5)[["year", "mean_ratio"]].round(1).values.tolist(),
               driest=ya.sort_values("mean_ratio").head(5)[["year", "mean_ratio"]].round(1).values.tolist())
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(R.round(3).to_string()); print(mk.round(3).to_string()); print(sd.round(1).to_string())


if __name__ == "__main__":
    main()
