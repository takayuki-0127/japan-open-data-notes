"""F283 03 分析：値上げの前後の駆け込み・反動・定着と、仮説の判定。

PLAN.md の式どおり：品目ごとに log(実質の支出) を
月ダミー＋トレンド＋2018年1月・2025年1月の段差＋2020年3〜6月の各月ダミー
＋出来事ごとのパルス（k=-2..+2）と段差（k>=0）で回帰する。
"""
import json
import pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / "results"
OUT.mkdir(exist_ok=True)
panel = pd.read_csv(BASE / "data" / "panel.csv")

EV = {  # 品目ごとの出来事（年月, 名前, 種類）
    "tobacco": [(201810, "T1", "up"), (202010, "T2", "up"), (202110, "T3", "up")],
    "happo": [(202010, "A1", "up"), (202310, "A2", "up")],
    "wine": [(202010, "W1", "up"), (202310, "W2", "up")],
    "beer": [(202010, "B1", "down"), (202310, "B2", "down")],
    "sake": [(202010, "S1", "down"), (202310, "S2", "down")],
}
CTAX = (201910, "CT", "ctax")
ITEMS = list(EV)
JP = {"tobacco": "たばこ", "happo": "発泡酒・ビール風", "wine": "ワイン", "beer": "ビール", "sake": "清酒"}


def idx(ym):
    return (ym // 100) * 12 + ym % 100 - 1


def design(ym, events, trend="lin", win=(-2, 2), covid=True, steps_only=False, start=201501):
    t = np.array([idx(v) for v in ym])
    X = pd.DataFrame(index=range(len(ym)))
    X["const"] = 1.0
    tt = (t - t.mean()) / 12
    X["trend"] = tt
    if trend == "quad":
        X["trend2"] = tt ** 2
    if trend == "none":  # レビュー後に追加：トレンドなし
        X = X.drop(columns=["trend"])
    mon = np.array([v % 100 for v in ym])
    for m in range(2, 13):
        X[f"m{m}"] = (mon == m).astype(float)
    if start <= 201712:
        X["kakeibo2018"] = (np.array(ym) >= 201801).astype(float)
    X["rev2025"] = (np.array(ym) >= 202501).astype(float)
    if covid:
        for v in (202003, 202004, 202005, 202006):
            X[f"cv{v}"] = (np.array(ym) == v).astype(float)
    for e_ym, name, _ in events:
        te = idx(e_ym)
        k = t - te
        X[f"step_{name}"] = (k >= 0).astype(float)
        if not steps_only:
            for kk in range(win[0], win[1] + 1):
                X[f"p_{name}_{kk}"] = (k == kk).astype(float)
    X = X.loc[:, (X.std() > 0) | (X.columns == "const")]
    return X


def fit(item, var="real", trend="lin", win=(-2, 2), covid=True, extra=None, drop=None,
        start=201501, steps_only=False):
    d = panel[(panel.item == item) & (panel.ym >= start)].reset_index(drop=True)
    evs = EV[item] + [CTAX] + (extra or [])
    if drop is not None:
        d = d[~d.ym.isin(drop)].reset_index(drop=True)
    y = np.log(d[var].values)
    X = design(d.ym.values, evs, trend, win, covid, steps_only, start)
    m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return m, evs


def metrics(m, name, win=(-2, 2)):
    p = m.params
    pre = [k for k in range(win[0], 0)]
    post = [k for k in range(0, win[1] + 1)]
    F = sum(p.get(f"p_{name}_{k}", 0.0) for k in pre)
    R = sum(p.get(f"p_{name}_{k}", 0.0) for k in post)
    S = p.get(f"step_{name}", np.nan)
    cov = m.cov_params()
    def se(cols):
        cols = [c for c in cols if c in cov.index]
        v = np.ones(len(cols))
        return float(np.sqrt(v @ cov.loc[cols, cols].values @ v)) if cols else np.nan
    return dict(F=F, R=R, S=S,
                F_se=se([f"p_{name}_{k}" for k in pre]),
                R_se=se([f"p_{name}_{k}" for k in post]),
                S_se=se([f"step_{name}"]),
                pulses={k: float(p.get(f"p_{name}_{k}", np.nan)) for k in range(win[0], win[1] + 1)})


def price_step(item, name, start=201501):
    m, _ = fit(item, var="cpi", steps_only=True, start=start)
    return float(m.params[f"step_{name}"])


# ---------- 本体 ----------
rows = []
for item in ITEMS:
    m, evs = fit(item)
    for e_ym, name, kind in EV[item]:
        r = metrics(m, name)
        P = price_step(item, name)
        rows.append(dict(item=item, item_jp=JP[item], event=name, ym=e_ym, kind=kind,
                         F=r["F"], F_se=r["F_se"], R=r["R"], R_se=r["R_se"], S=r["S"], S_se=r["S_se"],
                         P=P, eps=r["S"] / P if abs(P) > 1e-9 else np.nan,
                         **{f"p{k}": v for k, v in r["pulses"].items()}))
res = pd.DataFrame(rows)

# ---------- 偽の出来事（偶然の幅） ----------
plac = []
for item in ITEMS:
    # 2017年10月・2024年10月は、2018年1月・2025年1月の段差と見分けられない（式の上で同じになる）ので使わない
    real_years = {e // 100 for e, _, _ in EV[item]} | {2019, 2017, 2024}
    for y in range(2016, 2026):
        if y in real_years:
            continue
        fake = (y * 100 + 10, f"FK{y}", "fake")
        m, _ = fit(item, extra=[fake])
        r = metrics(m, fake[1])
        plac.append(dict(item=item, ym=fake[0], F=r["F"], R=r["R"], S=r["S"]))
plac = pd.DataFrame(plac)
band = {c: [float(plac[c].quantile(0.05)), float(plac[c].quantile(0.95))] for c in ("F", "R", "S")}

# ---------- 前年比（H5） ----------
def yoy_stats(item, e_ym):
    d = panel[panel.item == item].set_index("ym")["real"]
    t0 = idx(e_ym)
    def ymk(k):
        tt = t0 + k
        return (tt // 12) * 100 + tt % 12 + 1
    def yoy(k):
        a, b = ymk(k), ymk(k - 12)
        return float(np.log(d[a]) - np.log(d[b])) if a in d.index and b in d.index else np.nan
    return dict(yoy_m1=yoy(-1), yoy_0=yoy(0), yoy_p1=yoy(1),
                yoy_3_8=float(np.nanmean([yoy(k) for k in range(3, 9)])))

yy = pd.DataFrame([dict(event=r.event, **yoy_stats(r.item, r.ym)) for r in res.itertuples()])
res = res.merge(yy, on="event")
res.to_csv(OUT / "A_events.csv", index=False, float_format="%.5f")
plac.to_csv(OUT / "B_placebo.csv", index=False, float_format="%.5f")

# ---------- 仮説 ----------
up = res[res.kind == "up"]
H1_n = int((up.F > 0).sum())
fpos = up[up.F > 0]
H2_n = int((fpos.R <= -0.5 * fpos.F).sum())
tob = res[res.item == "tobacco"]
H3_ok = bool(((tob.S < 0) & (tob.eps.abs() < 1)).all())
def s(ev):
    return float(res.loc[res.event == ev, "S"].iloc[0])
H4_ok = bool(s("B1") > 0 and s("A1") < 0 and s("B2") > 0 and s("A2") < 0)
H5_n = int((up.yoy_0.abs() >= 2 * up.yoy_3_8.abs()).sum())
hyp = {
    "H1": dict(count=H1_n, of=len(up), rule=">=5", verdict="支持" if H1_n >= 5 else "外れ"),
    "H2": dict(count=H2_n, of=len(fpos), rule=">=half", verdict="支持" if H2_n * 2 >= len(fpos) and len(fpos) > 0 else "外れ"),
    "H3": dict(ok=H3_ok, verdict="支持" if H3_ok else "外れ"),
    "H4": dict(ok=H4_ok, verdict="支持" if H4_ok else "外れ"),
    "H5": dict(count=H5_n, of=len(up), rule=">=4", verdict="支持" if H5_n >= 4 else "外れ"),
}

# ---------- 頑健性 ----------
def run_variant(**kw):
    out = []
    for item in ITEMS:
        win = kw.get("win", (-2, 2))
        m, _ = fit(item, **kw)
        for e_ym, name, kind in EV[item]:
            r = metrics(m, name, win)
            out.append(dict(event=name, kind=kind, F=r["F"], R=r["R"], S=r["S"]))
    return pd.DataFrame(out)

covid_drop = [y * 100 + m for y in (2020, 2021) for m in range(1, 13)
              if 202003 <= y * 100 + m <= 202109 and not (202008 <= y * 100 + m <= 202012)
              and not (202106 <= y * 100 + m <= 202112)]
# 出来事の窓（2020年10月・2021年10月の前後2か月）は残す。
# レビュー後：2021年6〜7月も残す（2020年10月の窓と2021年10月の窓の間に月が1つもないと、
# たばこの2つの段差とパルスが式の上で区別できなくなるため）
variants = {
    "R1_2次トレンド": dict(trend="quad"),
    "R2_コロナ期を除く": dict(drop=covid_drop, covid=False),
    "R3_名目の支出": dict(var="spend"),
    "R4_窓±3": dict(win=(-3, 3)),
    "R5_2018年以降": dict(start=201801),
}
rob = {}
for k, kw in variants.items():
    v = run_variant(**kw)
    u = v[v.kind == "up"]
    fp = u[u.F > 0]
    rob[k] = dict(
        H1=int((u.F > 0).sum()),
        H2=f"{int((fp.R <= -0.5 * fp.F).sum())}/{len(fp)}",
        tobacco_S=[round(float(x), 4) for x in v[v.event.isin(["T1", "T2", "T3"])].S],
        H4=bool(v.set_index("event").S["B1"] > 0 and v.set_index("event").S["A1"] < 0
                and v.set_index("event").S["B2"] > 0 and v.set_index("event").S["A2"] < 0),
        events={r.event: dict(F=round(r.F, 4), R=round(r.R, 4), S=round(r.S, 4)) for r in v.itertuples()},
    )

# ---------- レビュー後の確かめ（独立レビューの指摘を受けて追加） ----------
rv = {"rank": {}, "items": {}, "events": {}}
for k, kw in [("main", {})] + list(variants.items()):
    for item in ITEMS:
        d = panel[(panel.item == item) & (panel.ym >= kw.get("start", 201501))].reset_index(drop=True)
        if kw.get("drop") is not None:
            d = d[~d.ym.isin(kw["drop"])].reset_index(drop=True)
        X = design(d.ym.values, EV[item] + [CTAX], kw.get("trend", "lin"), kw.get("win", (-2, 2)),
                   kw.get("covid", True), False, kw.get("start", 201501))
        rv["rank"][f"{k}|{item}"] = [int(np.linalg.matrix_rank(X.values)), int(X.shape[1])]
for item in ITEMS:
    m, _ = fit(item)
    mt, _ = fit(item, trend="none")
    rv["items"][item] = dict(trend_per_year=float(m.params["trend"]), step_CT=float(m.params["step_CT"]),
                             rev2025=float(m.params.get("rev2025", np.nan)),
                             kakeibo2018=float(m.params.get("kakeibo2018", np.nan)))
    for e_ym, name, kind in EV[item]:
        p = m.params
        S = float(p[f"step_{name}"])
        R = sum(float(p[f"p_{name}_{k}"]) for k in range(0, 3))
        F = sum(float(p[f"p_{name}_{k}"]) for k in (-2, -1))
        rv["events"][name] = dict(
            S_notrend=float(mt.params[f"step_{name}"]),
            pre_based_pct={k: float((np.exp(p[f"p_{name}_{k}"] + S) - 1) * 100) for k in range(0, 3)},
            R_plus_3S=R + 3 * S, F=F)
upx = [n for n, v in rv["events"].items() if res.set_index("event").kind[n] == "up" and v["F"] > 0]
rv["H2_alt_R3S"] = dict(count=int(sum(rv["events"][n]["R_plus_3S"] <= -0.5 * rv["events"][n]["F"] for n in upx)),
                        of=len(upx))
def yoy_base(e_ym):
    t = idx(e_ym) - 12
    return (t // 12) * 100 + t % 12 + 1
rv["yoy_base_month"] = {r.event: int(yoy_base(r.ym)) for r in res.itertuples()}
(OUT / "review_checks.json").write_text(json.dumps(rv, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- 問い直し（結果を見た後に追加） ----------
# 偽の出来事のうち、2022年10月のビール・発泡酒で大きな駆け込みと反動が出た。
# この月はビール類の値段が税と関係なく上がった月（物価指数で確かめる）。税以外の値上げでも同じ形かを見る。
reask = {}
for item in ("beer", "happo"):
    ev = (202210, "X1", "up")
    m, _ = fit(item, extra=[ev])
    r = metrics(m, "X1")
    mp, _ = fit(item, var="cpi", steps_only=True, extra=[ev])
    P = float(mp.params["step_X1"])
    reask[item] = dict(F=r["F"], F_se=r["F_se"], R=r["R"], R_se=r["R_se"], S=r["S"], S_se=r["S_se"], P=P,
                       eps=r["S"] / P, pulses=r["pulses"])
    # 2022年10月を入れたとき、本来の出来事（2020・2023年）の値がどれだけ動くか
    for e_ym, name, kind in EV[item]:
        rr = metrics(m, name)
        reask[item][f"{name}_with_X1"] = dict(F=rr["F"], R=rr["R"], S=rr["S"])
# 物価指数の月ごとの動き（2022年9→10月）
cpi_jump = {}
for item in ("beer", "happo", "sake", "wine", "tobacco"):
    d = panel[panel.item == item].set_index("ym")["cpi"]
    cpi_jump[item] = {str(k): float(np.log(d[k] / d[kp])) for k, kp in
                      [(202210, 202209), (202010, 202009), (202310, 202309), (201810, 201809), (202110, 202109)]}
# 偽の出来事を、2022年10月を除いた分布でも出す
plac2 = plac[plac.ym != 202210]
band_ex2022 = {c: [float(plac2[c].quantile(0.05)), float(plac2[c].quantile(0.95))] for c in ("F", "R", "S")}
per_item_F = {it: [float(g.F.min()), float(g.F.max())] for it, g in plac.groupby("item")}

main = dict(
    hypotheses=hyp,
    reask=reask, cpi_monthly_jump=cpi_jump, placebo_band_90_ex2022=band_ex2022,
    placebo_F_range_by_item=per_item_F, placebo_n_ex2022=len(plac2),
    placebo_band_90=band, placebo_n=len(plac),
    events={r.event: {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r._asdict().items() if k != "Index"}
            for r in res.itertuples()},
    robustness=rob,
)
(OUT / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
pd.set_option("display.width", 200)
print(res[["event", "item_jp", "kind", "F", "R", "S", "S_se", "P", "eps", "yoy_0", "yoy_3_8"]].round(3))
print("band", band, "n", len(plac))
print(json.dumps(hyp, ensure_ascii=False))
for k, v in rob.items():
    print(k, v["H1"], v["H2"], v["tobacco_S"], v["H4"])
print("reask", json.dumps(reask, ensure_ascii=False, default=float)[:1500])
print("cpi", json.dumps(cpi_jump))
print("band_ex2022", band_ex2022, len(plac2), per_item_F)
