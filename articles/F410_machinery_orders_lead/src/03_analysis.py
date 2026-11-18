"""主な分析：受注と設備投資のずれ（四半期・月）、振れの大きさ、予測の比較（H1〜H4）と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
LAGS = range(0, 7)


def load():
    o = pd.read_csv(D / "orders_quarterly_sa.csv")
    c = pd.read_csv(D / "capex_quarterly_sa.csv")
    df = c.merge(o, on=["year", "q"], how="left")
    df["t"] = df["year"] * 4 + df["q"] - 1
    df = df.set_index("t").sort_index()
    df["label"] = df["year"].astype(str) + "Q" + df["q"].astype(str)
    df["core_real"] = df["core"] / df["capex_deflator"] * 100
    return df


def lg(s, k):
    return np.log(s / s.shift(k)) * 100


def cc(y, x, k, mask=None):
    z = pd.concat([y, x.shift(k)], axis=1).dropna()
    if mask is not None:
        z = z[mask.reindex(z.index).fillna(False)]
    return float(z.iloc[:, 0].corr(z.iloc[:, 1])), len(z)


def lag_table(df, ycol, xcol, kind, mask=None):
    y = lg(df[ycol], 4 if kind == "yoy" else 1)
    x = lg(df[xcol], 4 if kind == "yoy" else 1)
    rows = []
    for k in LAGS:
        c, n = cc(y, x, k, mask)
        rows.append({"lag_q": k, "corr": round(c, 4), "n": n})
    return pd.DataFrame(rows)


def best(t):
    i = t["corr"].idxmax()
    return int(t.loc[i, "lag_q"]), float(t.loc[i, "corr"])


def forecast(df, ycol="capex_nominal", xcol="core", h=2, start=2012 * 4):
    """h 期先の設備投資の前年同期比を、(a) 今の設備投資の前年同期比、(b) それ＋受注の前年同期比 で逐次予測。"""
    y = lg(df[ycol], 4); x = lg(df[xcol], 4)
    z = pd.DataFrame({"target": y.shift(-h), "y": y, "x": x}).dropna()
    err_a, err_b, rec = [], [], []
    for t in z.index:
        if t < start:
            continue
        tr = z[z.index <= t - h]  # 予測する時点 t で答え（t+h）が分かっているデータだけ
        if len(tr) < 12:
            continue
        Xa = np.column_stack([np.ones(len(tr)), tr["y"]])
        Xb = np.column_stack([np.ones(len(tr)), tr["y"], tr["x"]])
        ba = np.linalg.lstsq(Xa, tr["target"].values, rcond=None)[0]
        bb = np.linalg.lstsq(Xb, tr["target"].values, rcond=None)[0]
        pa = ba[0] + ba[1] * z.loc[t, "y"]
        pb = bb[0] + bb[1] * z.loc[t, "y"] + bb[2] * z.loc[t, "x"]
        err_a.append(z.loc[t, "target"] - pa); err_b.append(z.loc[t, "target"] - pb)
        rec.append({"origin_t": int(t), "actual": z.loc[t, "target"], "pred_a": pa, "pred_b": pb})
    ra, rb = float(np.sqrt(np.mean(np.square(err_a)))), float(np.sqrt(np.mean(np.square(err_b))))
    return ra, rb, len(err_a), pd.DataFrame(rec)


def main():
    df = load()
    m = {}
    df[["label", "capex_nominal", "capex_real", "capex_deflator", "core", "core_real", "mfg", "nonmfg_core", "sales_exship", "backlog_exship"]].to_csv(R / "quarterly_panel.csv")
    base = df[df["core"].notna()].copy()
    m["period"] = f"{base['label'].iloc[0]}〜{base['label'].iloc[-1]}"
    m["n_quarters_orders"] = int(len(base))

    # H1：前年同期比のずれ
    t_yoy = lag_table(df, "capex_nominal", "core", "yoy")
    t_qoq = lag_table(df, "capex_nominal", "core", "qoq")
    t_yoy.merge(t_qoq, on="lag_q", suffixes=("_yoy", "_qoq")).to_csv(R / "lag_corr_quarterly.csv", index=False)
    m["H1_best_lag_q"], m["H1_best_corr"] = best(t_yoy)
    m["H1_corr_by_lag"] = {int(k): float(v) for k, v in zip(t_yoy["lag_q"], t_yoy["corr"])}
    m["H1_n_lag0"] = int(t_yoy.loc[0, "n"])
    m["H1"] = "支持" if 1 <= m["H1_best_lag_q"] <= 3 else "外れ"
    # H2：前期比
    m["H2_max_corr_qoq"] = float(t_qoq["corr"].max()); m["H2_max_lag_q"] = int(t_qoq.loc[t_qoq["corr"].idxmax(), "lag_q"])
    m["H2_corr_qoq_by_lag"] = {int(k): float(v) for k, v in zip(t_qoq["lag_q"], t_qoq["corr"])}
    m["H2"] = "支持" if m["H2_max_corr_qoq"] < 0.4 else "外れ"
    # H3：振れの大きさ
    so, sc = float(lg(base["core"], 1).std()), float(lg(base["capex_nominal"], 1).std())
    m["sd_qoq_orders"], m["sd_qoq_capex"], m["sd_ratio"] = round(so, 3), round(sc, 3), round(so / sc, 3)
    m["sd_yoy_orders"], m["sd_yoy_capex"] = round(float(lg(base["core"], 4).std()), 3), round(float(lg(base["capex_nominal"], 4).std()), 3)
    mo = pd.read_csv(D / "orders_monthly_sa.csv")
    m["sd_mom_orders"] = round(float((np.log(mo["core"] / mo["core"].shift(1)) * 100).std()), 3)
    m["share_mom_abs_over5"] = round(float(((np.log(mo["core"] / mo["core"].shift(1)) * 100).abs() > 5).mean() * 100), 1)
    m["min_yoy_orders"] = round(float(lg(base["core"], 4).min()), 2); m["min_yoy_orders_label"] = str(base.loc[lg(base["core"], 4).idxmin(), "label"])
    m["min_yoy_capex"] = round(float(lg(df["capex_nominal"], 4)[df.index >= base.index[0]].min()), 2)
    m["min_yoy_capex_label"] = str(df.loc[lg(df["capex_nominal"], 4)[df.index >= base.index[0]].idxmin(), "label"])
    m["H3"] = "支持" if m["sd_ratio"] >= 2 else "外れ"
    # H4：予測
    ra, rb, n, fc = forecast(df)
    fc.round(4).to_csv(R / "forecast_h2.csv", index=False)
    m["H4_rmse_a"], m["H4_rmse_b"], m["H4_n"] = round(ra, 3), round(rb, 3), n
    m["H4_rmse_cut_pct"] = round((1 - rb / ra) * 100, 1)
    m["H4"] = "支持" if m["H4_rmse_cut_pct"] >= 10 else ("弱く支持" if m["H4_rmse_cut_pct"] > 0 else "外れ")
    for h in [1, 3, 4]:
        a, b, _, _ = forecast(df, h=h)
        m[f"H4_rmse_cut_pct_h{h}"] = round((1 - b / a) * 100, 1)

    # 月のずれ：受注の3か月移動平均の前年同月比 vs 設備投資の前年同期比（四半期の真ん中の月）
    mo["idx"] = mo["year"] * 12 + mo["month"] - 1
    s = mo.set_index("idx")["core"].rolling(3, center=True).mean()  # 中心の月に置く（前後1か月との平均）
    oyoy = np.log(s / s.shift(12)) * 100
    cy = lg(df["capex_nominal"], 4)
    mid = pd.Series(cy.values, index=[int(t // 4) * 12 + (int(t % 4)) * 3 + 1 for t in cy.index])  # 四半期の真ん中の月
    rows = []
    for k in range(0, 13):
        z = pd.concat([mid, oyoy.shift(k)], axis=1).dropna()
        rows.append({"lag_months": k, "corr": round(float(z.iloc[:, 0].corr(z.iloc[:, 1])), 4), "n": len(z)})
    tm = pd.DataFrame(rows); tm.to_csv(R / "lag_corr_monthly.csv", index=False)
    i = tm["corr"].idxmax()
    m["month_best_lag"], m["month_best_corr"] = int(tm.loc[i, "lag_months"]), float(tm.loc[i, "corr"])
    m["month_corr_by_lag"] = {int(k): float(v) for k, v in zip(tm["lag_months"], tm["corr"])}
    # 手持ち月数
    b = base.copy(); b["months_on_hand"] = b["backlog_exship"] / (b["sales_exship"] / 3)
    m["months_on_hand_mean"] = round(float(b["months_on_hand"].mean()), 2)
    m["months_on_hand_first"] = round(float(b["months_on_hand"].iloc[0]), 2)
    m["months_on_hand_last"] = round(float(b["months_on_hand"].iloc[-1]), 2)
    m["months_on_hand_last_label"] = str(b["label"].iloc[-1])
    m["months_on_hand_2019"] = round(float(b.loc[b["year"] == 2019, "months_on_hand"].mean()), 2)
    b[["label", "months_on_hand"]].round(4).to_csv(R / "months_on_hand.csv")

    # 頑健性
    rob = []
    def add(chk, var, k, c, judge):
        rob.append({"check": chk, "variant": var, "best_lag_q": k, "value": round(c, 4), "judge": judge})
    add("H1 最大の相関のずれ", "基本：名目、全期間", m["H1_best_lag_q"], m["H1_best_corr"], m["H1"])
    t = lag_table(df, "capex_real", "core_real", "yoy"); k, c = best(t)
    add("H1 最大の相関のずれ", "実質（受注をデフレーターで割る）", k, c, "支持" if 1 <= k <= 3 else "外れ")
    crisis = pd.Series(True, index=df.index)
    for tt in df.index:
        yq = (df.loc[tt, "year"], df.loc[tt, "q"])
        if (2008, 4) <= yq <= (2009, 4) or yq[0] == 2020:
            crisis[tt] = False
    t = lag_table(df, "capex_nominal", "core", "yoy", mask=crisis); k, c = best(t)
    add("H1 最大の相関のずれ", "リーマン後・コロナの期を除く", k, c, "支持" if 1 <= k <= 3 else "外れ")
    m["rob_excl_crisis_lag"], m["rob_excl_crisis_corr"] = k, round(c, 3)
    for lo, hi, nm in [(2005, 2015, "2005〜2015年"), (2016, 2026, "2016〜2026年")]:
        msk = pd.Series((df["year"] >= lo) & (df["year"] <= hi), index=df.index)
        t = lag_table(df, "capex_nominal", "core", "yoy", mask=msk); k, c = best(t)
        add("H1 最大の相関のずれ", nm, k, c, "支持" if 1 <= k <= 3 else "外れ")
        m[f"rob_{lo}_lag"], m[f"rob_{lo}_corr"] = k, round(c, 3)
        m[f"rob_{lo}_corr_by_lag"] = {int(a): float(v) for a, v in zip(t["lag_q"], t["corr"])}
    for col, nm in [("mfg", "製造業"), ("nonmfg_core", "非製造業（船舶・電力を除く）")]:
        t = lag_table(df, "capex_nominal", col, "yoy"); k, c = best(t)
        add("H1 最大の相関のずれ", nm, k, c, "支持" if 1 <= k <= 3 else "外れ")
        m[f"rob_{col}_lag"], m[f"rob_{col}_corr"] = k, round(c, 3)
    t = lag_table(df, "capex_real", "core_real", "qoq")
    add("H2 前期比の最大の相関", "実質", int(t.loc[t["corr"].idxmax(), "lag_q"]), float(t["corr"].max()), "支持" if t["corr"].max() < 0.4 else "外れ")
    t = lag_table(df, "capex_nominal", "core", "qoq", mask=crisis)
    add("H2 前期比の最大の相関", "リーマン後・コロナの期を除く", int(t.loc[t["corr"].idxmax(), "lag_q"]), float(t["corr"].max()), "支持" if t["corr"].max() < 0.4 else "外れ")
    ra2, rb2, _, _ = forecast(df, ycol="capex_real", xcol="core_real")
    add("H4 RMSE の減り（%）", "実質", None, (1 - rb2 / ra2) * 100, "支持" if (1 - rb2 / ra2) * 100 >= 10 else ("弱く支持" if rb2 < ra2 else "外れ"))
    ra3, rb3, _, _ = forecast(df, start=2016 * 4)
    add("H4 RMSE の減り（%）", "予測の始まりを2016年に", None, (1 - rb3 / ra3) * 100, "支持" if (1 - rb3 / ra3) * 100 >= 10 else ("弱く支持" if rb3 < ra3 else "外れ"))
    rob = pd.DataFrame(rob); rob.to_csv(R / "robustness.csv", index=False)
    m["rob_real_lag"] = int(rob.iloc[1]["best_lag_q"]); m["rob_real_corr"] = float(rob.iloc[1]["value"])
    m["rob_H4_real"] = round(float(rob.iloc[-2]["value"]), 1); m["rob_H4_2016"] = round(float(rob.iloc[-1]["value"]), 1)
    m["rob_H2_real"] = round(float(rob.iloc[-4]["value"]), 3); m["rob_H2_excl"] = round(float(rob.iloc[-3]["value"]), 3)

    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False))
    print(rob.to_string())


if __name__ == "__main__":
    main()
