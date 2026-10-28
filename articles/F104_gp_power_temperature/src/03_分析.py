"""03 分析：ガウス過程回帰で、東京の日ごとの電力需要を「時刻の成分」と「気温の成分」に分けて読み、
予測の当たり方と予測の幅（不確実性）を確かめる。

1. 読む：全期間（2016年4月〜2026年9月）にカーネル E を当てはめ、成分に分ける。気温の成分から
   「需要がいちばん少ない気温」と「1℃あたりの変化率」を事後サンプルで求め、F67 のスプライン回帰と比べる。
2. 予測：2024年4月〜2026年7月の毎月1日を起点に、直前2年で学習して90日先まで予測する（28回）。
   気温は (a) 実際の気温（当日の気温が分かっている前提）、(b) 平年の気温、(c) 過去の年の気温を
   シナリオとして混ぜる、の3通り。比べる相手はスプライン回帰（F67 型）。
3. 頑健性：カーネルの組み合わせ／学習期間（1年・3年）／気温のカーネル（Matern 5/2）／週ごとに粗くする／関西。
途中の結果は results/ に保存し、あれば読み直して省略する（再実行が速い）。
"""
import sys
import time
import json
import warnings
import numpy as np
import pandas as pd
import torch
import statsmodels.formula.api as smf
from common import DATA, RES, SEED
from gp import GP

warnings.filterwarnings("ignore")
torch.set_num_threads(2)
np.random.seed(SEED)
RES.mkdir(exist_ok=True)

KERNELS = {
    "A_時刻だけ": ["cal", "trend", "season", "short"],
    "B_気温だけ": ["cal", "temp"],
    "C_気温＋傾向": ["cal", "trend", "temp"],
    "D_気温＋傾向＋季節": ["cal", "trend", "season", "temp"],
    "E_D＋短期": ["cal", "trend", "season", "temp", "short"],
}
MAIN = "D_気温＋傾向＋季節"
H = 90
d = pd.read_csv(DATA / "gp_daily_tokyo.csv", parse_dates=["date"])
d["md"] = d.date.dt.strftime("%m-%d")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- 1. 読む
def part1():
    out = RES / "read_full.json"
    if out.exists():
        log("1 あり")
        return
    t0 = time.time()
    hp = RES / "hyper_full.json"
    g = GP(KERNELS["E_D＋短期"]).fit(d, iters=80, params=json.load(open(hp)) if hp.exists() else None)
    json.dump(g.hyper(), open(hp, "w"), indent=1)
    log("1 全期間 E", round(time.time() - t0), "秒", g.hyper())
    comps = pd.DataFrame({"date": d.date, "log_d": d.log_d, "temp_mean": d.temp_mean})
    for c in ["cal", "trend", "season", "temp", "short"]:
        comps[c] = g.component(c, d)
    comps["const"] = g.ymean
    comps.to_csv(RES / "components_full.csv", index=False)
    share = {c: float(np.var(comps[c])) for c in ["cal", "trend", "season", "temp", "short"]}
    share["noise"] = float(np.var(d.log_d - comps[["cal", "trend", "season", "temp", "short"]].sum(1) - g.ymean))
    curve = temp_curve(g, "全期間")
    # 季節の成分を入れない（気温だけ）で全期間
    hpb = RES / "hyper_full_B.json"
    gb = GP(KERNELS["B_気温だけ"]).fit(d, iters=80, params=json.load(open(hpb)) if hpb.exists() else None)
    json.dump(gb.hyper(), open(hpb, "w"), indent=1)
    curve_b = temp_curve(gb, "全期間_B")
    log("1 全期間 B", curve_b)
    json.dump({"hyper": g.hyper(), "var": share, "nll": g.nll_, **curve, "B": curve_b, "B_hyper": gb.hyper()}, open(out, "w"), ensure_ascii=False, indent=1)
    # 期間別（2016〜2018年度・2023〜2026年度上期）
    rows = []
    for lab, a, b in [("2016〜2018年度", "2016-04-01", "2019-04-01"), ("2023〜2026年度", "2023-04-01", "2026-10-01")]:
        s = d[(d.date >= a) & (d.date < b)]
        for k in ["D_気温＋傾向＋季節", "B_気温だけ"]:
            gg = GP(KERNELS[k]).fit(s)
            r = temp_curve(gg, f"{lab}_{k}", sub=s)
            rows.append({"期間": lab, "カーネル": k, **{x: r[x] for x in r if not x.startswith("grid")}})
            log("1 期間別", lab, k, r["min_temp"], r["hot"], r["cold"])
    pd.DataFrame(rows).to_csv(RES / "curve_by_period.csv", index=False)


def temp_curve(g, label, sub=None, ns=1000):
    sub = d if sub is None else sub
    grid = pd.DataFrame({"t": 0.0, "temp_mean": np.arange(-1, 33.01, 0.25)})
    m, S = g.component("temp", grid, n_samples=ns, seed=SEED)
    G = grid.temp_mean.values
    R = S - S.min(0)  # 各サンプルの最小値からの差（曲線の形の不確実性だけを見る）
    pd.DataFrame({"temp": G, "mean": m, "lo": np.percentile(S, 2.5, 1), "hi": np.percentile(S, 97.5, 1),
                  "rel_med": np.median(R, 1), "rel_lo": np.percentile(R, 2.5, 1), "rel_hi": np.percentile(R, 97.5, 1)}).to_csv(
        RES / f"temp_curve_{label}.csv", index=False)
    mins = G[S.argmin(0)]
    dS = np.gradient(S, G, axis=0) * 100  # %／℃
    hotT = sub.temp_mean[sub.temp_mean >= 26].values
    coldT = sub.temp_mean[sub.temp_mean <= 8].values
    idx = lambda T: np.clip(np.round((T + 1) / 0.25).astype(int), 0, len(G) - 1)
    hot = dS[idx(hotT)].mean(0)
    cold = dS[idx(coldT)].mean(0)
    q = lambda x: [round(float(np.median(x)), 2), round(float(np.percentile(x, 2.5)), 2), round(float(np.percentile(x, 97.5)), 2)]
    return {"min_temp": q(mins), "hot": q(hot), "cold": q(cold), "ratio": q(hot / -cold),
            "n_hot": int(len(hotT)), "n_cold": int(len(coldT)), "temp_l": round(g.hyper()["temp_l"], 2)}


# ---------------------------------------------------------------- 2. 予測
def scen_temps(te, o, data):
    """起点より前の各年について、同じ月日の気温を並べたシナリオ（年数 × 日数）"""
    past = data[data.date < o]
    years = sorted(set(past.date.dt.year))
    S = []
    for y in years:
        # 予測期間の各日について、y 年分ずらした日付の気温
        shift = te.date.dt.year - (te.date.min().year - 0)
        dates = te.date.apply(lambda x: x.replace(year=y + (x.year - te.date.min().year)) if not (x.month == 2 and x.day == 29) else x.replace(year=y + (x.year - te.date.min().year), day=28))
        v = past.set_index("date").temp_mean.reindex(dates.values).values
        if np.isnan(v).sum() == 0:
            S.append(v)
    return np.array(S)


def ols_fit(tr, te):
    f = "log_d ~ cr(temp_mean, df=8) + C(dow) + holiday + obon + nenmatsu + gw + t"
    m = smf.ols(f, data=tr).fit()
    p = m.get_prediction(te).summary_frame(alpha=0.05)
    sd = (p.obs_ci_upper - p.obs_ci_lower).values / (2 * 1.96)
    return p["mean"].values, sd


def run_origins(data, origins, models, years=2, tag="", scen=True, temp_kernel="rbf", cal=None, step="D", h=H):
    out = RES / f"fc_{tag}.csv"
    done = pd.read_csv(out, parse_dates=["origin"]) if out.exists() else pd.DataFrame()
    have = set(zip(done.origin, done.model)) if len(done) else set()
    rows = []
    for o in origins:
        o = pd.Timestamp(o)
        tr = data[(data.date >= o - pd.DateOffset(years=years)) & (data.date < o)]
        end = o + (pd.Timedelta(days=h) if step == "D" else pd.Timedelta(weeks=h))
        te = data[(data.date >= o) & (data.date < end)].copy()
        if len(te) == 0:
            continue
        hh = ((te.date - o).dt.days // (1 if step == "D" else 7)).values
        y = te.log_d.values
        for k in models:
            if (o, k) in have:
                continue
            t0 = time.time()
            if k == "OLS_スプライン":
                m, s = ols_fit(tr, te)
                rows += pack(o, te, hh, y, k, m, s)
                continue
            kw = {"temp_kernel": temp_kernel}
            if cal is not None:
                kw["cal_cols"] = cal
            g = GP(KERNELS[k], **kw).fit(tr)
            m, s = g.predict(te)
            rows += pack(o, te, hh, y, k, m, s)
            if scen and "temp" in KERNELS[k]:
                S = scen_temps(te, o, d)
                if len(S):
                    te2 = te.copy()
                    te2["temp_mean"] = S.mean(0)
                    m2, s2 = g.predict(te2)
                    rows += pack(o, te, hh, y, k + "｜平年の気温", m2, s2)
                    rng = np.random.default_rng(SEED)
                    draws = []
                    for sc in S:
                        te2["temp_mean"] = sc
                        mm, ss = g.predict(te2)
                        draws.append(mm[None, :] + ss[None, :] * rng.standard_normal((200, len(mm))))
                    D = np.concatenate(draws)
                    rows += pack(o, te, hh, y, k + "｜気温シナリオ", np.median(D, 0), None,
                                 lo=np.percentile(D, 2.5, 0), hi=np.percentile(D, 97.5, 0), nsc=len(S))
            log(tag, o.date(), k, round(time.time() - t0, 1), "秒")
        if rows:
            done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
            done.to_csv(out, index=False)
            rows = []
    return done


def pack(o, te, hh, y, k, m, s, lo=None, hi=None, nsc=0):
    if lo is None:
        lo, hi = m - 1.96 * s, m + 1.96 * s
    return [dict(origin=o, date=dt, h=int(a), model=k, y=float(yy), m=float(mm), lo=float(l), hi=float(u), nsc=nsc)
            for dt, a, yy, mm, l, u in zip(te.date, hh, y, m, lo, hi)]


def score(fc, buckets=((0, 7), (7, 30), (30, 90)), unit="日"):
    fc = fc.copy()
    fc["ape"] = np.abs(np.exp(fc.m - fc.y) - 1) * 100
    fc["cov"] = ((fc.y >= fc.lo) & (fc.y <= fc.hi)).astype(float)
    fc["width"] = (np.exp(fc.hi) - np.exp(fc.lo)) / np.exp(fc.m) * 100
    rows = []
    for a, b in buckets + ((buckets[0][0], buckets[-1][1]),):
        s = fc[(fc.h >= a) & (fc.h < b)]
        for k, g in s.groupby("model"):
            rows.append(dict(model=k, horizon=f"{a + 1}〜{b}{unit}先", MAPE=g.ape.mean(), cover95=g["cov"].mean(),
                             width=g.width.mean(), n=len(g), origins=g.origin.nunique()))
    return pd.DataFrame(rows)


def boot_diff(fc, k1, k2, a=0, b=90, nb=2000):
    """起点ごとのブロックで、2つのモデルの MAPE の差（k1 − k2）の95%区間"""
    s = fc[(fc.h >= a) & (fc.h < b)].copy()
    s["ape"] = np.abs(np.exp(s.m - s.y) - 1) * 100
    p = s.pivot_table(index=["origin", "date"], columns="model", values="ape").dropna(subset=[k1, k2])
    per = p.groupby(level=0).agg({k1: "mean", k2: "mean"})
    diff = (per[k1] - per[k2]).values
    rng = np.random.default_rng(SEED)
    bs = [rng.choice(diff, len(diff)).mean() for _ in range(nb)]
    return round(float(diff.mean()), 2), round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3"]
    ORIG = pd.date_range("2024-04-01", "2026-07-01", freq="MS")
    if "2" in which:
        fc = run_origins(d, ORIG, ["A_時刻だけ", "B_気温だけ", "C_気温＋傾向", MAIN, "E_D＋短期", "OLS_スプライン"], tag="main")
        sc = score(fc)
        sc.to_csv(RES / "score_main.csv", index=False)
        log("\n" + sc.round(2).to_string())
    if "1" in which:
        part1()
    if "3" in which:
        # 学習期間
        for yrs in [1, 3]:
            fc = run_origins(d, ORIG, [MAIN, "B_気温だけ"], years=yrs, tag=f"train{yrs}y", scen=False)
        # 気温のカーネル
        KERNELS["D_Matern"] = KERNELS[MAIN]
        fc = run_origins(d, ORIG, ["D_Matern"], tag="matern", scen=False, temp_kernel="matern52")
        # 週ごと
        w = pd.read_csv(DATA / "gp_weekly_tokyo.csv", parse_dates=["week"]).rename(columns={"week": "date"})
        w["holiday"] = w.holiday / 7
        fc = run_origins(w, ORIG, ["A_時刻だけ", "B_気温だけ", MAIN, "E_D＋短期"], tag="weekly", scen=False,
                         cal=["holiday", "obon", "nenmatsu", "gw", "covid"], step="W", h=13)
        # 関西（2024年4月〜、1年で学習）
        k = pd.read_csv(DATA / "gp_daily_kansai.csv", parse_dates=["date"])
        fc = run_origins(k, pd.date_range("2025-04-01", "2026-07-01", freq="MS"),
                         ["A_時刻だけ", "B_気温だけ", MAIN, "OLS_スプライン"], years=1, tag="kansai", scen=False)
        rows = []
        for tag, unit, bk in [("train1y", "日", ((0, 7), (7, 30), (30, 90))), ("train3y", "日", ((0, 7), (7, 30), (30, 90))),
                              ("matern", "日", ((0, 7), (7, 30), (30, 90))), ("weekly", "週", ((0, 1), (1, 4), (4, 13))),
                              ("kansai", "日", ((0, 7), (7, 30), (30, 90)))]:
            s = score(pd.read_csv(RES / f"fc_{tag}.csv", parse_dates=["origin"]), bk, unit)
            s.insert(0, "setting", tag)
            rows.append(s)
        pd.concat(rows).to_csv(RES / "score_robust.csv", index=False)
        log("3 done")
