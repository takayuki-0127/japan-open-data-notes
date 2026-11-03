"""同じ予測の不確かさを、図の形ごとに「読み取れること」と「読み違えやすいこと」を数で比べる。

例：① 出生数 2026〜2030年（F55 のベイズ構造時系列、4,000本の道筋）
    ② 女性の平均寿命 2025〜2070年（F86 の Lee–Carter、5,000本）
    ③ 東京エリアの翌日ピーク需要の95%上限（F92、2020年4月〜2026年9月の2,374日）

A. しきい値を下回る確率を、図の形ごとの「読み方」で推し量ったときのずれ（正解はシミュレーションから数えた確率）
   - 点だけ：中央値がしきい値より下なら100%、上なら0%と読む
   - 95%区間（エラーバー）：区間を正規分布の±1.96σとみなして読む（頑健性で一様分布とみなす読み方も）
   - ファン図（2.5・10・25・50・75・90・97.5%）：帯の境目のあいだを直線でつないで読む
   - 分位点ドットプロット（20点）：しきい値より下の点を数える
   - HOP（Hypothetical Outcome Plots。1コマ1本の道筋を順に見せるアニメ、20コマ）：下回ったコマを数える（1,000回くり返した平均）
B. 2つの年の比較：区間（年ごとの幅）だけから、2つの年を独立とみなして読んだ確率と、道筋から数えた正しい確率
C. 帯と道筋：各年の95%の帯に、全期間おさまる道筋の割合。合計の区間と、年ごとの区間の端の合計
D. 「1日ごとの95%」と1か月：95%上限を超えた日の数を月ごとに数え、独立とみなしたときと比べる
"""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, binom
from common import RAW, DATA, RES, SEED

FAN_Q = np.array([2.5, 10, 25, 50, 75, 90, 97.5])
NREP = 1000


def load():
    z = np.load(DATA / "samples.npz")
    ex = {
        "出生数（2026〜30年）": (z["births_future_years"], z["births_future"].astype(float), np.arange(500000, 750001, 25000)),
        "平均寿命・女（2025〜70年）": (z["e0_years"], z["e0_f"].astype(float), np.arange(86, 99, 1.0)),
    }
    extra = {
        "平均寿命・男（2025〜70年）": (z["e0_years"], z["e0_m"].astype(float), np.arange(80, 93, 1.0)),
        "出生数（2020〜25年、2019年までで予測）": (z["births_past_years"], z["births_past"].astype(float), np.arange(600000, 900001, 25000)),
    }
    return z, ex, extra


def read_point(x, c):
    return float(np.median(x) < c)


def read_interval(x, c, rule="normal"):
    lo, mid, hi = np.percentile(x, [2.5, 50, 97.5])
    if rule == "normal":
        return float(norm.cdf((c - mid) / ((hi - lo) / 3.92)))
    if rule == "uniform":           # 区間の中は一様、外に2.5%ずつ
        if c <= lo: return 0.0125
        if c >= hi: return 0.9875
        return 0.025 + 0.95 * (c - lo) / (hi - lo)
    if rule == "inside_all":        # 区間の外はない、中は一様
        return float(np.clip((c - lo) / (hi - lo), 0, 1))
    raise ValueError(rule)


def read_fan(x, c):
    qs = np.percentile(x, FAN_Q)
    p = np.interp(c, qs, FAN_Q / 100, left=0.0, right=1.0)
    if c < qs[0]: p = 0.025 * max(0, 1 - (qs[0] - c) / (qs[1] - qs[0]))
    if c > qs[-1]: p = 1 - 0.025 * max(0, 1 - (c - qs[-1]) / (qs[-1] - qs[-2]))
    return float(p)


def read_dots(x, c, k=20):
    dots = np.percentile(x, (np.arange(k) + 0.5) / k * 100)
    return float((dots < c).mean())


def read_hop(x, c, k, rng, nrep=NREP):
    idx = rng.integers(0, len(x), size=(nrep, k))
    return (x[idx] < c).mean(axis=1)          # 1回ごとの推定（nrep 個）


def part_a(ex, rng, ks=(20,), rules=("normal",), prange=(0.02, 0.98), years_sel=None):
    rows = []
    for name, (years, S, cs) in ex.items():
        sel = years if years_sel is None else [y for y in years if y in years_sel.get(name, years)]
        for y in sel:
            j = int(np.where(years == y)[0][0]); x = S[:, j]
            for c in cs:
                p = float((x < c).mean())
                if not (prange[0] <= p <= prange[1]):
                    continue
                r = dict(example=name, year=int(y), threshold=float(c), truth=p, point=read_point(x, c), fan=read_fan(x, c))
                for rule in rules:
                    r[f"interval_{rule}"] = read_interval(x, c, rule)
                for k in ks:
                    r[f"dots{k}"] = read_dots(x, c, k)
                    h = read_hop(x, c, k, rng)
                    r[f"hop{k}_mae"] = float(np.abs(h - p).mean())
                rows.append(r)
    return pd.DataFrame(rows)


def mae_table(df):
    fmt = [c for c in df.columns if c in ("point", "fan") or c.startswith("interval_") or c.startswith("dots")]
    out = []
    for name, g in df.groupby("example", sort=False):
        r = {"example": name, "n_questions": len(g)}
        for f in fmt:
            r[f] = float((g[f] - g.truth).abs().mean() * 100)
        for c in [c for c in df.columns if c.endswith("_mae")]:
            r[c.replace("_mae", "")] = float(g[c].mean() * 100)
        out.append(r)
    return pd.DataFrame(out)


def part_b(ex_all, pairs):
    rows = []
    for name, (years, S, _) in ex_all.items():
        for (y1, y2) in pairs[name]:
            i, j = int(np.where(years == y1)[0][0]), int(np.where(years == y2)[0][0])
            a, b = S[:, i], S[:, j]
            truth = float((b > a).mean())
            la, ma, ha = np.percentile(a, [2.5, 50, 97.5]); lb, mb, hb = np.percentile(b, [2.5, 50, 97.5])
            sa, sb = (ha - la) / 3.92, (hb - lb) / 3.92
            indep = float(norm.cdf((mb - ma) / np.sqrt(sa ** 2 + sb ** 2)))
            overlap = bool(max(la, lb) < min(ha, hb))
            rows.append(dict(example=name, year1=y1, year2=y2, p_later_higher_truth=truth, p_read_as_independent=indep,
                             intervals_overlap=overlap, corr=float(np.corrcoef(a, b)[0, 1]),
                             median1=float(ma), median2=float(mb)))
    return pd.DataFrame(rows)


def part_c(ex_all):
    rows = []
    for name, (years, S, _) in ex_all.items():
        lo95, hi95 = np.percentile(S, [2.5, 97.5], axis=0)
        lo80, hi80 = np.percentile(S, [10, 90], axis=0)
        in95 = (S >= lo95) & (S <= hi95); in80 = (S >= lo80) & (S <= hi80)
        for H in sorted(set([1, 2, 3, 5, 6, 10, 20, 30, 46]) & set(range(1, len(years) + 1))):
            rows.append(dict(example=name, horizon_years=H, last_year=int(years[H - 1]),
                             share_paths_inside95_all_years=float(in95[:, :H].all(axis=1).mean()),
                             share_paths_inside80_all_years=float(in80[:, :H].all(axis=1).mean())))
    return pd.DataFrame(rows)


def sums(S, years):
    tot = S.sum(axis=1)
    lo, med, hi = np.percentile(S, [2.5, 50, 97.5], axis=0)
    return dict(years=f"{years[0]}〜{years[-1]}", sum_median=float(np.median(tot)), sum_of_medians=float(med.sum()),
                sum_p025=float(np.percentile(tot, 2.5)), sum_of_p025=float(lo.sum()),
                sum_p975=float(np.percentile(tot, 97.5)), sum_of_p975=float(hi.sum()),
                width_ratio=float((hi.sum() - lo.sum()) / (np.percentile(tot, 97.5) - np.percentile(tot, 2.5))))


def part_d(p, col="conf_0.95", level=0.95):
    p = p.copy(); p["exceed"] = p.actual > p[col]
    p["ym"] = p.date.dt.to_period("M")
    g = p.groupby("ym").agg(days=("exceed", "size"), n_exceed=("exceed", "sum"), season=("season", lambda s: s.mode()[0]))
    q = 1 - level
    g["p_ge1_indep"] = 1 - (1 - q) ** g.days
    rate = p.exceed.mean()
    e = p.exceed.values
    cond = float(e[1:][e[:-1]].mean()) if e[:-1].sum() else np.nan
    runs = []
    r = 0
    for v in e:
        if v: r += 1
        else:
            if r: runs.append(r)
            r = 0
    if r: runs.append(r)
    summ = dict(method=col, level=level, days=int(len(p)), exceed_rate=float(rate),
                months=int(len(g)), share_months_ge1=float((g.n_exceed >= 1).mean()),
                share_months_ge1_indep=float(g.p_ge1_indep.mean()),
                share_months_ge3=float((g.n_exceed >= 3).mean()),
                share_months_ge3_indep=float(np.mean([1 - binom.cdf(2, d, q) for d in g.days])),
                max_in_month=int(g.n_exceed.max()), p_exceed_next_given_exceed=cond,
                longest_run=int(max(runs) if runs else 0), share_exceed_in_runs_ge2=float(sum(x for x in runs if x >= 2) / max(1, sum(runs))))
    for s, gg in p.groupby("season"):
        summ[f"exceed_rate_{s}"] = float(gg.exceed.mean())
    return summ, g.reset_index()


def main():
    rng = np.random.default_rng(SEED)
    z, ex, extra = load()
    allex = {**ex, **extra}
    # A
    a = part_a(ex, rng)
    a.to_csv(RES / "A_probability_questions.csv", index=False)
    m = mae_table(a); m.to_csv(RES / "A_format_mae.csv", index=False)
    print(m.round(2).to_string())
    # 例：出生数 2030年に60万人を下回る確率
    x = ex["出生数（2026〜30年）"][1][:, 4]
    ex1 = dict(truth=float((x < 6e5).mean()), point=read_point(x, 6e5), interval_normal=read_interval(x, 6e5),
               fan=read_fan(x, 6e5), dots20=read_dots(x, 6e5), hop20_example=read_hop(x, 6e5, 20, np.random.default_rng(SEED), 1).tolist()[0],
               p025=float(np.percentile(x, 2.5)), p50=float(np.median(x)), p975=float(np.percentile(x, 97.5)),
               hop20_within5pt=float((np.abs(read_hop(x, 6e5, 20, np.random.default_rng(SEED)) - (x < 6e5).mean()) <= 0.05).mean()))
    # B
    pairs = {
        "出生数（2026〜30年）": [(2026, 2027), (2027, 2028), (2028, 2029), (2029, 2030), (2026, 2030)],
        "平均寿命・女（2025〜70年）": [(2045, 2046), (2045, 2050), (2050, 2060), (2025, 2035), (2045, 2070)],
        "平均寿命・男（2025〜70年）": [(2045, 2046), (2045, 2050), (2050, 2060), (2025, 2035), (2045, 2070)],
        "出生数（2020〜25年、2019年までで予測）": [(2020, 2021), (2022, 2023), (2024, 2025), (2020, 2025)],
    }
    b = part_b(allex, pairs); b.to_csv(RES / "B_pair_comparisons.csv", index=False)
    print(b.round(3).to_string())
    # C
    c = part_c(allex); c.to_csv(RES / "C_band_vs_paths.csv", index=False)
    print(c.round(3).to_string())
    yb, Sb, _ = ex["出生数（2026〜30年）"]; yp, Sp, _ = extra["出生数（2020〜25年、2019年までで予測）"]
    sm = pd.DataFrame([dict(example="出生数（2026〜30年）", **sums(Sb, yb)),
                       dict(example="出生数（2020〜22年、2019年までで予測）", **sums(Sp[:, :3], yp[:3]))])
    sm.to_csv(RES / "C_sums.csv", index=False); print(sm.round(0).to_string())
    # D
    p = pd.read_csv(RAW / "f92_pred_tokyo.csv", parse_dates=["date"])
    d, g = part_d(p)
    g["ym"] = g.ym.astype(str); g.to_csv(RES / "D_power_monthly_exceed.csv", index=False)
    print(json.dumps(d, ensure_ascii=False, indent=1))
    json.dump(dict(births2030_below600k=ex1, power=d), open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
