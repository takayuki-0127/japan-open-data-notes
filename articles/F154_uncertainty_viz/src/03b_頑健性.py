"""頑健性：読み方の仮定・点やコマの数・しきい値の選び方・例・電力の予測方法と水準を変えて、結論が動くかを見る"""
import importlib.util
import json
import numpy as np
import pandas as pd
from common import RAW, RES, SEED

spec = importlib.util.spec_from_file_location("ana", __file__.replace("03b_頑健性.py", "03_分析.py"))
ana = importlib.util.module_from_spec(spec); spec.loader.exec_module(ana)


def main():
    rng = np.random.default_rng(SEED)
    z, ex, extra = ana.load()
    allex = {**ex, **extra}
    rows = []
    # R1・R2・R4：4つの例すべてで、読み方3通り・点やコマ 10/20/50/100
    a = ana.part_a(allex, rng, ks=(10, 20, 50, 100), rules=("normal", "uniform", "inside_all"))
    m = ana.mae_table(a); m["setting"] = "基本のしきい値（確率2〜98%の問い）"; rows.append(m)
    # R3：しきい値の選び方 ①確率10〜90%の問いだけ ②しきい値を分位点 5〜95% から無作為に（各年20個）
    a2 = a[(a.truth >= 0.1) & (a.truth <= 0.9)]
    m2 = ana.mae_table(a2); m2["setting"] = "確率10〜90%の問いだけ"; rows.append(m2)
    ex_r = {}
    r2 = np.random.default_rng(SEED + 1)
    for name, (years, S, _) in allex.items():
        cs = np.unique(np.concatenate([np.percentile(S[:, j], r2.uniform(5, 95, 20)) for j in range(S.shape[1])]))
        ex_r[name] = (years, S, cs)
    a3 = ana.part_a(ex_r, rng, ks=(10, 20, 50, 100), rules=("normal", "uniform", "inside_all"), prange=(0.0, 1.0))
    m3 = ana.mae_table(a3); m3["setting"] = "しきい値を分位点5〜95%から無作為に"; rows.append(m3)
    rob = pd.concat(rows, ignore_index=True)
    rob.to_csv(RES / "R_format_mae_robustness.csv", index=False)
    print(rob.round(2).to_string())
    # HOP：±5ポイント以内に入る割合（コマ数別）、出生数2030年・60万人
    x = ex["出生数（2026〜30年）"][1][:, 4]; p = (x < 6e5).mean()
    hop = {k: float((np.abs(ana.read_hop(x, 6e5, k, np.random.default_rng(SEED)) - p) <= 0.05).mean()) for k in (10, 20, 50, 100, 200)}
    # R6：となり合う年の比較（平均寿命、すべての年）
    pr = []
    for name in ["平均寿命・女（2025〜70年）", "平均寿命・男（2025〜70年）"]:
        years, S, _ = allex[name]
        for gap in (1, 5):
            b = ana.part_b({name: allex[name]}, {name: [(y, y + gap) for y in years if y + gap <= years[-1]]})
            pr.append(dict(example=name, gap_years=gap, pairs=len(b), mean_truth=b.p_later_higher_truth.mean(),
                           mean_read_indep=b.p_read_as_independent.mean(),
                           share_overlap_but_truth_ge95=float(((b.p_later_higher_truth >= 0.95) & b.intervals_overlap).mean()),
                           mean_abs_gap_pt=float((b.p_later_higher_truth - b.p_read_as_independent).abs().mean() * 100)))
    for name in ["出生数（2026〜30年）", "出生数（2020〜25年、2019年までで予測）"]:
        years, S, _ = allex[name]
        b = ana.part_b({name: allex[name]}, {name: [(y, y + 1) for y in years[:-1]]})
        pr.append(dict(example=name, gap_years=1, pairs=len(b), mean_truth=b.p_later_higher_truth.mean(),
                       mean_read_indep=b.p_read_as_independent.mean(),
                       share_overlap_but_truth_ge95=float(((b.p_later_higher_truth <= 0.05) & b.intervals_overlap).mean()),
                       mean_abs_gap_pt=float((b.p_later_higher_truth - b.p_read_as_independent).abs().mean() * 100)))
    pr = pd.DataFrame(pr); pr.to_csv(RES / "R_pairs_all_years.csv", index=False); print(pr.round(3).to_string())
    # R5：電力の予測方法と水準
    pw = pd.read_csv(RAW / "f92_pred_tokyo.csv", parse_dates=["date"])
    dd = []
    for meth in ("conf", "qr", "lgbq"):
        for lv in (0.9, 0.95, 0.99):
            d, _ = ana.part_d(pw, f"{meth}_{lv}", lv); dd.append(d)
    dd = pd.DataFrame(dd); dd.to_csv(RES / "R_power_methods_levels.csv", index=False)
    print(dd[["method", "exceed_rate", "share_months_ge1", "share_months_ge1_indep", "share_months_ge3", "share_months_ge3_indep",
              "p_exceed_next_given_exceed", "max_in_month"]].round(3).to_string())
    json.dump(dict(hop_within5pt_births2030_600k=hop), open(RES / "R_hop_frames.json", "w"), ensure_ascii=False, indent=1)
    print(hop)


if __name__ == "__main__":
    main()
