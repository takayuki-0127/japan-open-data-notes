"""03 分析：チェック（src/dq_check.py）が、どの汚れをどれだけ見つけ、汚れのない月にどれだけ誤って鳴るかを測る。

A. 汚れのないデータでの「ふだんとの比」（F246 の gen で乱数の種 0〜19 × FY2024・FY2025 の24か月 = 480か月分）
   - 参照の組み合わせ（a・b・c・ab・abc）と線 T ごとに、1か月あたり何件鳴るか（誤報）
   - 売上・客数・点数をまとめて f 倍にする汚れ（途中まで・2回足し込み）を、どの f から見つけられるか（汚れのない比に log f を足して判定）
   - カレンダーの月ごとの誤報（年末・お盆）、参照 a の週数（4・8・13週）
B. 10種類の汚れを入れて、8つのチェックを全部流す（480か月 × 10個 = 4,800個の汚れ）
   - 汚れの種類ごとに、見つけた割合と、どのチェックが拾ったか
   - 汚れのない月の誤報（チェックごと、1か月あたり）
   - 比べる相手：決めた範囲だけのチェック（売上 50万〜2,000万円など）
C. F247 で整えた mart（seed 0、確定）の24か月に流したときに鳴ったもの
D. 速報（締め1・3・5・10日）に流したとき：行の欠け（未着）と部門の合計が、確定とどれだけ違うか。本当の欠けを1つ入れたとき、速報と確定で見分けられるか
会社・数字はすべて架空（合成データ）。
"""
import json, pathlib, sys, time, warnings
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dq_check as q
import sim_common as S
warnings.filterwarnings("ignore")

ROOT = S.ROOT
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
TGRID = [1.2, 1.3, 1.5, 1.75, 2.0, 3.0, 5.0]
FGRID = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0]
MODES = ["a", "b", "c", "ab", "abc"]
POS3 = ["sales", "receipts", "items"]
t0 = time.time()
g = S.load_gen()
DATA = {s: S.gen_mart(g, s) for s in S.SEEDS}
print("gen", round(time.time() - t0, 1), "s")


def amin(R, c, mode, shift=0.0):
    """参照 mode のうち |log(値/参照)| のいちばん小さいもの（参照がなければ nan）"""
    A = np.abs(np.stack([R[f"{c}_l{t}"].values + shift for t in mode]))
    A = np.where(np.isnan(A), np.inf, A); a = A.min(0); a[np.isinf(a)] = np.nan
    return a


def ratio_table(weeks=8, seeds=S.SEEDS):
    rows = []
    for seed in seeds:
        fsd, cat = DATA[seed]
        for m in S.MONTHS:
            m0 = pd.Period(m, "M").start_time
            cur, cc, h, hc = q.split_month(fsd, cat, m)
            el = set(S.eligible_stores(h, cur, m0))
            ref = q.references(h, cur, q.RATIO, m0, weeks=weeks)
            x = cur[q.KEY + q.RATIO].merge(ref, on=q.KEY)
            out = x[q.KEY].copy(); out["seed"] = seed; out["month"] = m; out["eligible"] = x.store_id.isin(el).values
            for c in q.RATIO:
                for t in "abc":
                    out[f"{c}_l{t}"] = np.log(x[c] / x[f"{c}__{t}"])
            rows.append(out)
    return pd.concat(rows, ignore_index=True)


# ---------------- A ----------------
R = ratio_table()
nrun = len(S.SEEDS) * len(S.MONTHS)
recs = []
for mode in MODES:
    for c in q.RATIO:
        a = amin(R, c, mode)
        for T in TGRID:
            recs.append(dict(mode=mode, metric=c, T=T, false_alarms_per_month=float(np.nansum(a > np.log(T)) / nrun),
                             share_rows=float(np.nanmean(a > np.log(T))), no_ref=float(np.isnan(a).mean())))
    # 売上・客数・点数のどれかで鳴った店×日（1か月あたり）
    A3 = np.stack([amin(R, c, mode) for c in POS3])
    for T in TGRID:
        hit = np.nanmax(np.where(np.isnan(A3), -1, A3), 0) > np.log(T)
        recs.append(dict(mode=mode, metric="POS3_any", T=T, false_alarms_per_month=float(hit.sum() / nrun), share_rows=float(hit.mean()), no_ref=np.nan))
A = pd.DataFrame(recs); A.to_csv(RES / "A_false_alarms_by_T_mode.csv", index=False, encoding="utf-8-sig")

E = R[R.eligible]
recs = []
for mode in MODES:
    for T in [1.3, 1.5, 2.0, 3.0]:
        for f in FGRID:
            A3 = np.stack([amin(E, c, mode, np.log(f)) for c in POS3])
            hit = np.nanmax(np.where(np.isnan(A3), -1, A3), 0) > np.log(T)
            recs.append(dict(mode=mode, T=T, factor=f, detect=float(hit.mean())))
B = pd.DataFrame(recs); B.to_csv(RES / "B_detect_by_factor.csv", index=False, encoding="utf-8-sig")

R["cal_month"] = R.month.str[5:]
recs = []
for mode in ["a", "ab", "abc"]:
    A3 = np.stack([amin(R, c, mode) for c in POS3])
    R["_hit"] = np.nanmax(np.where(np.isnan(A3), -1, A3), 0) > np.log(1.5)
    R["_w"] = amin(R, "waste", mode) > np.log(2.0)
    gm = R.groupby("cal_month")[["_hit", "_w"]].sum() / (len(S.SEEDS) * 2)
    for cm, r in gm.iterrows():
        recs.append(dict(mode=mode, cal_month=cm, pos3_flags=float(r["_hit"]), waste_flags=float(r["_w"])))
    if mode == "a":   # 参照 a だけのとき、どの日に鳴るか（12月）
        d = R[(R.cal_month == "12") & R["_hit"]].biz_date.dt.day.value_counts().sort_index()
        d.rename("flags").to_csv(RES / "C_dec_days_mode_a.csv", encoding="utf-8-sig")
C = pd.DataFrame(recs); C.to_csv(RES / "C_false_alarms_by_calendar_month.csv", index=False, encoding="utf-8-sig")

recs = []
for w in [4, 8, 13]:
    Rw = ratio_table(weeks=w, seeds=S.SEEDS[:5]); Ew = Rw[Rw.eligible]
    for mode in ["a", "abc"]:
        A3 = np.stack([amin(Rw, c, mode) for c in POS3])
        fa = (np.nanmax(np.where(np.isnan(A3), -1, A3), 0) > np.log(1.5)).sum() / (5 * len(S.MONTHS))
        D3 = np.stack([amin(Ew, c, mode, np.log(2)) for c in POS3])
        det = (np.nanmax(np.where(np.isnan(D3), -1, D3), 0) > np.log(1.5)).mean()
        recs.append(dict(weeks=w, mode=mode, pos3_false_alarms_per_month=float(fa), detect_x2=float(det),
                         waste_false_alarms_per_month=float(np.nansum(amin(Rw, "waste", mode) > np.log(2)) / (5 * len(S.MONTHS)))))
pd.DataFrame(recs).to_csv(RES / "D_window_weeks.csv", index=False, encoding="utf-8-sig")
print("A done", round(time.time() - t0, 1), "s")


# ---------------- B ----------------
def fixed_range(cur):
    """比べる相手：決めた範囲だけ（空・範囲の外）。範囲は、この会社の店×日の値がふだん入る幅を広めにとった"""
    lim = {"sales": (5e5, 2e7), "receipts": (100, 6000), "items": (1000, 60000), "labor_hours": (30, 1500), "waste": (1e4, 1e6)}
    hit = set()
    for c, (lo, hi) in lim.items():
        k = cur[c].isna() | (cur[c] < lo) | (cur[c] > hi)
        hit |= set(zip(cur.loc[k, "store_id"], cur.loc[k, "biz_date"]))
    return hit


det, fa, fr = [], [], []
for seed in S.SEEDS:
    fsd, cat = DATA[seed]
    rng = np.random.default_rng(1000 + seed)
    st = pd.read_csv(ROOT / "data" / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"], encoding="utf-8-sig")
    for m in S.MONTHS:
        m0 = pd.Period(m, "M").start_time
        cur, cc, h, hc = q.split_month(fsd, cat, m)
        f0, _ = q.run_checks(cur, cc, h, hc, st, m)
        fa.append(dict(seed=seed, month=m, **{k: int((f0.check == k).sum()) for k in q.CHECKS},
                       store_days=int(f0[["store_id", "biz_date"]].drop_duplicates().shape[0]), fixed_range=len(fixed_range(cur))))
        cur2, cc2, truth = S.inject(cur, cc, rng, S.eligible_stores(h, cur, m0))
        f1, _ = q.run_checks(cur2, cc2, h, hc, st, m)
        hitset = set(zip(f1.store_id, pd.to_datetime(f1.biz_date)))
        frs = fixed_range(cur2)
        for tr in truth:
            touch = set((tr["store_id"], pd.Timestamp(d)) for d in tr["dates"])
            ff = f1[[(s, pd.Timestamp(d)) in touch for s, d in zip(f1.store_id, f1.biz_date)]]
            det.append(dict(seed=seed, month=m, type=tr["type"], detected=int(len(ff) > 0), **{k: int((ff.check == k).any()) for k in q.CHECKS},
                            A=int((ff["重さ"] == "A").any()), fixed_range=int(len(touch & frs) > 0),
                            share_days_flagged=float(len(set(zip(ff.store_id, pd.to_datetime(ff.biz_date)))) / len(touch))))
DET = pd.DataFrame(det); FA = pd.DataFrame(fa)
DET.to_csv(RES / "E_injected_detail.csv.gz", index=False)
FA.to_csv(RES / "E_clean_flags_per_month.csv", index=False, encoding="utf-8-sig")
E1 = DET.groupby("type", sort=False)[["detected", "A", "fixed_range"] + list(q.CHECKS) + ["share_days_flagged"]].mean().reindex(S.TYPES)
E1.to_csv(RES / "E_detect_by_type.csv", encoding="utf-8-sig")
print("B done", round(time.time() - t0, 1), "s")

# ---------------- C ----------------
fsd, cat, st = q.load_mart(ROOT / "data" / "in")
recs, allf = [], []
for m in S.MONTHS:
    cur, cc, h, hc = q.split_month(fsd, cat, m)
    f, info = q.run_checks(cur, cc, h, hc, st, m)
    f["month"] = m; allf.append(f)
    recs.append(dict(month=m, rows=len(cur), flags=len(f), store_days=int(f[["store_id", "biz_date"]].drop_duplicates().shape[0]),
                     **{k: int((f.check == k).sum()) for k in q.CHECKS}, no_ref=",".join(map(str, info["参照なしの店"])),
                     no_ly=",".join(map(str, info["1年前の参照なしの店"]))))
MART = pd.DataFrame(recs); MART.to_csv(RES / "F_mart_by_month.csv", index=False, encoding="utf-8-sig")
pd.concat(allf).to_csv(RES / "F_mart_flags.csv", index=False, encoding="utf-8-sig")

# ---------------- D ----------------
V = ROOT / "data" / "versions"
recs = []
rng = np.random.default_rng(7)
for k in (1, 3, 5, 10):
    sf = pd.read_csv(V / f"fact_store_day_d{k}.csv.gz", parse_dates=["biz_date"])
    sc = pd.read_csv(V / f"fact_store_day_category_d{k}.csv.gz", parse_dates=["biz_date"])
    for m in S.MONTHS[12:]:
        cur, cc, _, _ = q.split_month(sf, sc, m)
        fcur, fcc, h, hc = q.split_month(fsd, cat, m)
        f_s, _ = q.run_checks(cur, cc, h, hc, st, m, mode="速報")
        f_k, _ = q.run_checks(fcur, fcc, h, hc, st, m)
        # 本当の欠けを1つ（届かないまま）入れたとき：速報では未着の中に混ざり、確定では欠けとして残る
        s = int(rng.choice(sorted(fcur.store_id.unique()))); d = pd.Timestamp(rng.choice(sorted(fcur.biz_date.unique())))
        drop = lambda x: x[~((x.store_id == s) & (x.biz_date == d))]
        f_s2, _ = q.run_checks(drop(cur), drop(cc), h, hc, st, m, mode="速報")
        f_k2, _ = q.run_checks(drop(fcur), drop(fcc), h, hc, st, m)
        recs.append(dict(close_day=k, month=m, rows_sokuho=len(cur), rows_kakutei=len(fcur),
                         pending_Q02=int((f_s["重さ"] == "保留").sum()), A_sokuho=int((f_s["重さ"] == "A").sum()),
                         Q08_sokuho=int((f_s.check == "Q08").sum()), B_sokuho=int((f_s["重さ"] == "B").sum()),
                         flags_kakutei=len(f_k), Q02_kakutei=int((f_k.check == "Q02").sum()),
                         true_missing_pending_sokuho=int((f_s2["重さ"] == "保留").sum()), true_missing_Q02_kakutei=int((f_k2.check == "Q02").sum())))
G = pd.DataFrame(recs); G.to_csv(RES / "G_sokuho_vs_kakutei.csv", index=False, encoding="utf-8-sig")

# ---------------- まとめ ----------------
def fa_at(mode, metric, T):
    return float(A[(A["mode"] == mode) & (A.metric == metric) & (A["T"] == T)].false_alarms_per_month.iloc[0])
summ = dict(
    runs=nrun, defects=len(DET),
    detect_overall=float(DET.detected.mean()), detect_by_type=E1.detected.round(4).to_dict(),
    detect_A_by_type=E1.A.round(4).to_dict(), fixed_range_by_type=E1.fixed_range.round(4).to_dict(),
    fixed_range_overall=float(DET.fixed_range.mean()),
    clean_flags_per_month=FA[list(q.CHECKS)].mean().round(3).to_dict(), clean_store_days_per_month=float(FA.store_days.mean()),
    clean_store_days_p90=float(FA.store_days.quantile(0.9)), clean_store_days_max=int(FA.store_days.max()),
    clean_months_zero=float((FA.store_days == 0).mean()), fixed_range_clean_per_month=float(FA.fixed_range.mean()),
    pos3_fa_T15={m: fa_at(m, "POS3_any", 1.5) for m in MODES}, pos3_fa_T13={m: fa_at(m, "POS3_any", 1.3) for m in MODES},
    waste_fa_T2={m: fa_at(m, "waste", 2.0) for m in MODES}, waste_fa_T15={m: fa_at(m, "waste", 1.5) for m in MODES},
    detect_x2_T15={m: float(B[(B["mode"] == m) & (B["T"] == 1.5) & (B.factor == 2.0)].detect.iloc[0]) for m in MODES},
    detect_x05_T15={m: float(B[(B["mode"] == m) & (B["T"] == 1.5) & (B.factor == 0.5)].detect.iloc[0]) for m in MODES},
    detect_x13_T15_abc=float(B[(B["mode"] == "abc") & (B["T"] == 1.5) & (B.factor == 1.3)].detect.iloc[0]),
    mart_flags_total=int(MART["flags"].sum()), mart_store_days_total=int(MART["store_days"].sum()), mart_months_zero=int((MART["flags"] == 0).sum()),
    sokuho=G.groupby("close_day")[["pending_Q02", "Q08_sokuho", "A_sokuho", "B_sokuho", "Q02_kakutei", "true_missing_pending_sokuho", "true_missing_Q02_kakutei"]].mean().round(3).to_dict("index"),
    seconds=round(time.time() - t0, 1))
(RES / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
