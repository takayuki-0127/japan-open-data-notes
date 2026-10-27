"""03c 頑健性（実データ、基本は k=2）
1. 空振りの数え方：転換点から12か月以上離れた月だけ数える
2. 期間：2007年までの転換点 / 2008年以降の転換点
3. 急な転換点（2008年2月の山・2020年5月の谷）を除く
4. 小さな動きは無視する：|値| が、その見方の標準偏差の 0.25 倍より小さい月は「どちらでもない」とする
5. 季節調整をしない前月比（原数値の前月比）を足す
6. 系列を1つずつ外す
7. 「同じ空振りの多さ」で比べる：見方ごとに k=1〜4 を動かし、前年比（k=2）の空振り以下で一番早い設定を探す"""
import numpy as np
import pandas as pd
from common import DATA, RES, IND, SERIES, detect, false_alarms, cycle_table, phase_frame, change

BASE_K = 2


def evaluate(d, ph, tps, cols, k=BASE_K, guard=6, band=0.0):
    rows = []
    for i in cols:
        sig = d[i].copy()
        if band > 0:
            sig = sig.where(sig.abs() >= band * sig.std(), 0.0)
        lags = [detect(sig, tp.date, -1 if tp.type == "peak" else 1, k=k) for _, tp in tps.iterrows()]
        n, yrs = false_alarms(sig, ph, k=k, guard=guard)
        rows.append({"見方": i, "lags": lags, "空振り": n, "年数": yrs})
    return rows


def collect(setting, ind, levels, cols=IND, k=BASE_K, guard=6, band=0.0, tp_filter=None, drop_series=None, add_nsa_mom=False):
    agg = {c: {"lags": [], "n": 0, "yrs": 0.0} for c in cols + (["前月比（季節調整なし）"] if add_nsa_mom else [])}
    for name, (kind, sign) in SERIES.items():
        if drop_series and name == drop_series:
            continue
        d = ind[ind.series == name].set_index("date")
        d = d[d.index >= d["前年比"].first_valid_index()]
        use = list(cols)
        if add_nsa_mom:
            lv = levels[levels.series == name].set_index("date")
            if lv["nsa"].notna().sum() > 24:
                d = d.assign(**{"前月比（季節調整なし）": change(lv["nsa"], 1, kind) * sign})
                use = use + ["前月比（季節調整なし）"]
        c = cycle_table()
        first, last = d["前年比"].first_valid_index(), d.index.max()
        tps = c[(c.date >= first + pd.DateOffset(months=6)) & (c.date + pd.DateOffset(months=12) <= last)]
        if tp_filter is not None:
            tps = tps[tp_filter(tps)]
        ph = phase_frame(d.index)
        for r in evaluate(d, ph, tps, use, k=k, guard=guard, band=band):
            agg[r["見方"]]["lags"] += r["lags"]
            agg[r["見方"]]["n"] += r["空振り"]
            agg[r["見方"]]["yrs"] += r["年数"]
    out = []
    for c, a in agg.items():
        if not a["lags"]:
            continue
        l = np.array(a["lags"], dtype=float)
        out.append({"設定": setting, "見方": c, "k": k, "遅れの中央値": np.nanmedian(l), "遅れの平均": np.nanmean(l),
                    "見逃し": int(np.isnan(l).sum()), "転換点": len(l), "空振り（10年あたり）": a["n"] / a["yrs"] * 10})
    return out


if __name__ == "__main__":
    ind = pd.read_csv(DATA / "indicators.csv", parse_dates=["date"])
    levels = pd.read_csv(DATA / "levels.csv", parse_dates=["date"])
    rows = []
    rows += collect("基本（k=2）", ind, levels)
    rows += collect("空振りは転換点から12か月以上離れた月だけ", ind, levels, guard=12)
    rows += collect("2007年までの転換点", ind, levels, tp_filter=lambda t: t.date < "2008-01-01")
    rows += collect("2008年以降の転換点", ind, levels, tp_filter=lambda t: t.date >= "2008-01-01")
    rows += collect("2008年2月の山・2020年5月の谷を除く", ind, levels,
                    tp_filter=lambda t: ~t.date.isin(pd.to_datetime(["2008-02-01", "2020-05-01"])))
    rows += collect("小さな動き（0.25標準偏差未満）を無視", ind, levels, band=0.25)
    rows += collect("季節調整なしの前月比を足す", ind, levels, add_nsa_mom=True)
    rows += collect("参考：3か月平均の前月比", ind, levels, cols=["3か月前比", "3か月平均の前月比"])
    for s in SERIES:
        rows += collect(f"{s}を除く", ind, levels, drop_series=s)
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    print(rob.pivot_table(index="設定", columns="見方", values="遅れの中央値").round(1))
    print(rob.pivot_table(index="設定", columns="見方", values="空振り（10年あたり）").round(2))

    # 同じ空振りの多さで比べる
    fr = []
    for k in (1, 2, 3, 4):
        fr += collect(f"k={k}", ind, levels, k=k)
    fr = pd.DataFrame(fr)
    fr.to_csv(RES / "frontier_real.csv", index=False)
    ref = fr[(fr["見方"] == "前年比") & (fr.k == 2)]["空振り（10年あたり）"].iloc[0]
    best = (fr[fr["空振り（10年あたり）"] <= ref + 1e-9].sort_values("遅れの平均").groupby("見方").head(1))
    best.to_csv(RES / "equal_false_alarm.csv", index=False)
    print("前年比（k=2）の空振り", round(ref, 2))
    print(best.round(2).to_string())
