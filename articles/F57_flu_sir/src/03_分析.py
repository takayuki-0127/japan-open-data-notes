"""シーズンごとに SIR を当てはめ、再生産数・山の高さと時期・予測の当たり方を調べる。

モデル
- M1：1つの SIR（β は一定）
- M2：1つの SIR ＋ 年末年始（12/27〜1/7）の β の倍率 h
- M3：2つの SIR（型の違う2つの流行を足す、感受性者は別々）＋ h
いずれも y_週 = c × 新しい感染 ＋ b（下限の報告）を、log(y+0.3) の残差で当てはめる。
感染期間 D=3日（γ=1/3）、SEIR では潜伏 L=1.5日を足す。
"""
import json, sys
import numpy as np
import pandas as pd
from common import DATA, RES
from sir import fit, holiday_mask, final_size, rt_from_growth, simulate

SEASONS = ["2012/13", "2013/14", "2014/15", "2015/16", "2016/17", "2017/18", "2018/19", "2019/20",
           "2022/23", "2023/24", "2024/25", "2025/26"]
PRE = SEASONS[:8]


def to_sw(season, wk):
    s0 = int(season[:4])
    sw = wk - 36 if wk >= 36 else wk + 52 - 36
    if wk == 53:
        sw = 17
    elif wk < 36 and s0 in (2015, 2020, 2026):
        sw += 1
    return sw


def series(df, season, col="per"):
    g = df[df.season == season]
    y = np.full(53, np.nan)
    for wk, p in zip(g.week, g[col]):
        sw = to_sw(season, wk)
        if sw < 53:
            y[sw] = p
    return y


def growth_rt(y, mean=3.0, sd=1.5):
    """立ち上がり（y が初めて 1 以上になった週〜山の週）の R。3週移動平均の最大と中央値。"""
    pk = int(np.nanargmax(y))
    st = int(np.argmax(np.nan_to_num(y) >= 1.0))
    seg = y[st:pk + 1]
    if len(seg) < 3:
        return np.nan, np.nan
    rt = rt_from_growth(seg, mean, sd)
    rt3 = pd.Series(rt).rolling(3, min_periods=2).mean()
    return float(rt3.max()), float(np.nanmedian(rt))


def main_reff(f):
    """M3 なら、累積の感染が大きいほうの株の Reff0 を「主な山」とする。"""
    st = f["strains"]
    if len(st) == 1:
        return st[0][0], 1.0
    hol = np.zeros(10)  # 使わない
    sizes = [final_size(R) for R, _ in st]
    i = int(np.argmax(sizes))
    return st[i][0], sizes[i] / (sum(sizes) or 1)


def run_national():
    nat = pd.read_csv(DATA / "flu_national_weekly.csv")
    rows, curves = [], {}
    for s in SEASONS:
        y = series(nat, s)
        hol = holiday_mask(int(s[:4]))
        fits = {}
        for name, ns, uh in [("M1", 1, False), ("M2", 1, True), ("M3", 2, True)]:
            fits[name] = fit(y, hol, nstrain=ns, use_h=uh, starts=10, seed=1)
        pk = int(np.nanargmax(y))
        rtmax, rtmed = growth_rt(y)
        r = dict(season=s, peak_obs=float(np.nanmax(y)), peak_week_obs=pk, total_obs=float(np.nansum(y)),
                 rt_growth_max=rtmax, rt_growth_med=rtmed)
        for name, f in fits.items():
            R, share = main_reff(f)
            r.update({
                f"{name}_R": f["strains"][0][0] if name != "M3" else R,
                f"{name}_rmse": f["rmse"], f"{name}_aic": f["aic"],
                f"{name}_peak": float(f["pred"].max()), f"{name}_peak_week": int(np.argmax(f["pred"])),
                f"{name}_h": f["h"]})
            if name == "M3":
                r["M3_R_a"], r["M3_R_b"] = f["strains"][0][0], f["strains"][1][0]
                r["M3_main_share"] = share
            curves[(s, name)] = f["pred"].tolist()
        r["M1_final_size"] = final_size(r["M1_R"])
        r["M1_peak_depletion"] = 1 - 1 / r["M1_R"] if r["M1_R"] > 1 else 0
        rows.append(r)
        print(s, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items() if k in
                  ("M1_R", "M2_R", "M3_R_a", "M3_R_b", "M1_rmse", "M3_rmse", "rt_growth_max", "M2_h", "M3_h")}, flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(RES / "season_fits.csv", index=False)
    cur = pd.DataFrame({f"{s}|{m}": v for (s, m), v in curves.items()})
    obs = pd.DataFrame({s: series(nat, s) for s in SEASONS})
    cur.to_csv(RES / "fitted_curves.csv", index=False)
    obs.to_csv(RES / "observed_curves.csv", index=False)
    return res, nat


def run_forecast(nat):
    """山の何週前までのデータで、山の時期と高さをどこまで当てられるか（M1 と M3）。"""
    out = []
    for s in SEASONS:
        y = series(nat, s)
        hol = holiday_mask(int(s[:4]))
        pk = int(np.nanargmax(y))
        for lead in [6, 4, 2, 0]:
            mask = np.zeros(53, bool); mask[:pk - lead + 1] = True
            for name, ns in [("M1", 1), ("M3", 2)]:
                f = fit(y, hol, nstrain=ns, use_h=(ns == 2), mask=mask, starts=8, seed=2)
                fut = f["pred"].copy()
                pw = int(np.argmax(fut))
                out.append(dict(season=s, lead=lead, model=name, peak_week_obs=pk, peak_week_pred=pw,
                                week_err=pw - pk, peak_obs=float(np.nanmax(y)), peak_pred=float(fut.max()),
                                height_ratio=float(fut.max() / np.nanmax(y))))
        print("forecast", s, flush=True)
    fc = pd.DataFrame(out)
    fc.to_csv(RES / "peak_forecast.csv", index=False)
    return fc


def run_robust(nat):
    """設定を変えて M1 と M3 の Reff0、M1 の山の高さの比を出す。"""
    sets = [("基本 D=3日", dict()), ("D=2日", dict(D=2.0)), ("D=4日", dict(D=4.0)),
            ("SEIR 潜伏1.5日", dict(L=1.5)), ("log の足し算 0.1", dict(off=0.1)),
            ("log の足し算 1.0", dict(off=1.0))]
    out = []
    for s in SEASONS:
        y = series(nat, s); hol = holiday_mask(int(s[:4]))
        for lab, kw in sets:
            f1 = fit(y, hol, nstrain=1, use_h=False, starts=6, seed=3, **kw)
            f3 = fit(y, hol, nstrain=2, use_h=True, starts=6, seed=3, **kw)
            R3, _ = main_reff(f3)
            out.append(dict(season=s, setting=lab, M1_R=f1["strains"][0][0], M3_R=R3,
                            M1_peak_ratio=f1["pred"].max() / np.nanmax(y), M3_peak_ratio=f3["pred"].max() / np.nanmax(y),
                            M1_rmse=f1["rmse"], M3_rmse=f3["rmse"]))
        # 増加率から出す R：世代時間の仮定を変える
        for lab, (m, sd) in [("Rt 世代時間 平均2.6日", (2.6, 1.3)), ("Rt 世代時間 平均3.0日", (3.0, 1.5)),
                             ("Rt 世代時間 平均3.5日", (3.5, 1.75))]:
            mx, md = growth_rt(y, m, sd)
            out.append(dict(season=s, setting=lab, rt_max=mx, rt_med=md))
        print("robust", s, flush=True)
    rb = pd.DataFrame(out)
    rb.to_csv(RES / "robustness.csv", index=False)
    return rb


def run_pref():
    """都道府県ごと（コロナ前8シーズン）に M1 を当てはめる。県の名前は図で順位として扱わない。"""
    pf = pd.read_csv(DATA / "flu_pref_weekly.csv")
    out = []
    for s in PRE:
        hol = holiday_mask(int(s[:4]))
        for p, g in pf[pf.season == s].groupby("pref"):
            y = series(g.assign(season=s), s)
            if np.nanmax(y) < 5:
                continue
            f = fit(y, hol, nstrain=1, use_h=False, starts=5, seed=4)
            out.append(dict(season=s, pref=p, R=f["strains"][0][0], rmse=f["rmse"],
                            peak_obs=float(np.nanmax(y)), peak_pred=float(f["pred"].max()),
                            peak_week_obs=int(np.nanargmax(y))))
        print("pref", s, flush=True)
    pr = pd.DataFrame(out)
    pr.to_csv(RES / "pref_fits.csv", index=False)
    return pr


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    nat = pd.read_csv(DATA / "flu_national_weekly.csv")
    if step in ("all", "nat"): run_national()
    if step in ("all", "fc"): run_forecast(nat)
    if step in ("all", "rb"): run_robust(nat)
    if step in ("all", "pref"): run_pref()
