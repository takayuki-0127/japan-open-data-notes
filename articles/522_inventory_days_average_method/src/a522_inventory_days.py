"""522 在庫回転日数を「期首と期末の平均在庫」で出すと、毎日の在庫から出した値と何日ずれるのか（実務の型）

架空の商品1つの在庫を、2025年1月1日〜12月31日の毎日で作る。入荷のしかた（毎日・月初・月中・月末に月1回）と
売れ方の季節（山なし・12月に山）を変えて、在庫回転日数（平均在庫 ÷ 1日あたりの払出し）を3通りの平均在庫で出す。
  - 期首と期末の平均：(期首の在庫 + 期末の在庫) / 2
  - 月末の平均：期首と12か月の月末、13点の平均
  - 毎日の平均：365日の日末在庫の平均（この記事ではこれを基準にする）
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 522
SRC = "架空の在庫データ（作成者が乱数で作成、seed 522）"
DAYS = pd.date_range("2024-12-01", "2025-12-31", freq="D")     # 12月分は助走（期首の在庫を作るため）
Y0, Y1 = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
BASE = 100.0              # 1日の平均の払出し（個）
SAFETY_DAYS = 7           # 入荷の直後に「次の入荷まで＋7日分」を持つ


def demand_curve(peak_month=None, amp=0.0):
    """1日あたりの見込みの払出し。peak_month の月の中ごろに山、振れ幅 amp"""
    doy = DAYS.dayofyear.to_numpy()
    if peak_month is None or amp == 0:
        return np.full(len(DAYS), BASE)
    mid = pd.Timestamp(2025, peak_month, 15).dayofyear
    return BASE * (1 + amp * np.cos(2 * np.pi * (doy - mid) / 365))


def simulate(inbound, peak_month=None, amp=0.0, seed=SEED):
    """inbound: 'daily'、または月1回の入荷日（1〜28、'end' は月末）"""
    rng = np.random.default_rng(seed)
    exp = demand_curve(peak_month, amp)
    sales_draw = rng.normal(exp, exp * 0.15).clip(0)
    if inbound == "daily":
        deliv = np.ones(len(DAYS), bool)
    elif inbound == "end":
        deliv = DAYS.is_month_end
    else:
        deliv = DAYS.day == inbound
    deliv = np.asarray(deliv)
    nxt = np.zeros(len(DAYS), int)                       # 次の入荷までの日数
    k = len(DAYS)
    for i in range(len(DAYS) - 1, -1, -1):
        nxt[i] = (k - i) if k < len(DAYS) else 31
        if deliv[i]:
            k = i
    inv, I = np.zeros(len(DAYS)), 30 * BASE
    inb = np.zeros(len(DAYS)); sold = np.zeros(len(DAYS))
    for i in range(len(DAYS)):
        if deliv[i]:                                     # 朝に入荷：次の入荷まで＋安全在庫の分まで補う
            target = exp[i:i + nxt[i]].sum() + exp[i] * SAFETY_DAYS
            inb[i] = max(target - I, 0); I += inb[i]
        sold[i] = min(sales_draw[i], I); I -= sold[i]
        inv[i] = I                                       # 日末の在庫
    return pd.DataFrame({"date": DAYS, "inbound": inb.round(1), "shipped": sold.round(1), "inv_end": inv.round(1)})


def turnover(df):
    y = df[(df.date >= Y0) & (df.date <= Y1)]
    per_day = y.shipped.sum() / len(y)
    opening = df.loc[df.date == Y0 - pd.Timedelta(days=1), "inv_end"].iloc[0]
    closing = y.inv_end.iloc[-1]
    me = [opening] + list(y[y.date.dt.is_month_end].inv_end)
    avg = {"期首と期末の平均": (opening + closing) / 2, "月末の平均（13点）": float(np.mean(me)), "毎日の平均": y.inv_end.mean()}
    return {k: v / per_day for k, v in avg.items()}, per_day


def main():
    scen = [("毎日入荷", "daily"), ("月1回・月初（1日）", 1), ("月1回・月中（15日）", 15), ("月1回・月末", "end")]
    seasons = [("季節の山なし", None, 0.0), ("12月に山（振れ幅±50%）", 12, 0.5)]
    rows, keep = [], {}
    for sn, pm, amp in seasons:
        for name, ib in scen:
            df = simulate(ib, pm, amp)
            keep[(sn, name)] = df
            t, pdy = turnover(df)
            base = t["毎日の平均"]
            r = {"季節": sn, "入荷": name, "1日の払出し": round(pdy, 1)}
            for k, v in t.items():
                r[k + "(日)"] = round(v, 2)
            for k in ["期首と期末の平均", "月末の平均（13点）"]:
                r[k + "のずれ(日)"] = round(t[k] - base, 2)
                r[k + "のずれ(%)"] = round((t[k] / base - 1) * 100, 1)
            rows.append(r)
    tb = pd.DataFrame(rows); tb.to_csv(RES / "turnover_by_scenario.csv", index=False)

    # SQL（DuckDB）で同じ3通りを出し、Python と一致するか（12月に山・月末入荷）
    d = keep[("12月に山（振れ幅±50%）", "月1回・月末")]
    d.to_csv(DATA / "fictional_daily_inventory_peak12_monthend.csv", index=False)
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("inv", d)
    s = con.execute(open(SQL / "02_turnover_days_duckdb.sql", encoding="utf-8").read()).df().iloc[0]
    t, _ = turnover(d)
    sql_ok = bool(np.allclose([s.days_open_close, s.days_month_end, s.days_daily], [t["期首と期末の平均"], t["月末の平均（13点）"], t["毎日の平均"]], atol=1e-6))

    # 入荷日を1〜28日と月末に動かしたときの、月末の平均のずれ（山なし）
    sw = []
    for ib in list(range(1, 29)) + ["end"]:
        t, _ = turnover(simulate(ib))
        sw.append({"入荷日": "月末" if ib == "end" else ib, "月末の平均(日)": round(t["月末の平均（13点）"], 2), "毎日の平均(日)": round(t["毎日の平均"], 2),
                   "ずれ(日)": round(t["月末の平均（13点）"] - t["毎日の平均"], 2)})
    sw = pd.DataFrame(sw); sw.to_csv(RES / "sweep_delivery_day.csv", index=False)
    # 季節の山の月を動かしたときの、期首と期末の平均のずれ（毎日入荷・月末入荷）
    sp = []
    for pm in range(1, 13):
        r = {"山の月": pm}
        for name, ib in [("毎日入荷", "daily"), ("月1回・月末", "end")]:
            t, _ = turnover(simulate(ib, pm, 0.5))
            r[name + "：期首と期末のずれ(日)"] = round(t["期首と期末の平均"] - t["毎日の平均"], 2)
            r[name + "：毎日の平均(日)"] = round(t["毎日の平均"], 2)
        sp.append(r)
    sp = pd.DataFrame(sp); sp.to_csv(RES / "sweep_peak_month.csv", index=False)

    res = {"sql_matches_python": sql_ok, "by_scenario": rows,
           "sweep_delivery_day_range": [float(sw["ずれ(日)"].min()), float(sw["ずれ(日)"].max())],
           "sweep_peak_month_daily_range": [float(sp["毎日入荷：期首と期末のずれ(日)"].min()), float(sp["毎日入荷：期首と期末のずれ(日)"].max())],
           "sweep_peak_month_end_range": [float(sp["月1回・月末：期首と期末のずれ(日)"].min()), float(sp["月1回・月末：期首と期末のずれ(日)"].max())]}
    json.dump(res, open(RES / "a522_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：月初入荷と月末入荷の毎日の在庫と、月末の点
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 5.4), sharex=True)
    for ax, name, c in zip(axes, ["月1回・月初（1日）", "月1回・月末"], [BLUE, ORANGE]):
        d = keep[("季節の山なし", name)]; y = d[(d.date >= Y0 - pd.Timedelta(days=1))]
        ax.plot(y.date, y.inv_end, color=c, lw=1.2, label="日末の在庫")
        me = y[y.date.dt.is_month_end]
        ax.plot(me.date, me.inv_end, "o", color=INK, ms=4, label="月末の在庫（13点）")
        ax.axhline(y[y.date >= Y0].inv_end.mean(), color=GRAY, ls="--", lw=1, label="毎日の平均")
        ax.axhline(me.inv_end.mean(), color=INK, ls=":", lw=1.2, label="月末の平均")
        ax.set_title(f"{name}に入荷（季節の山なし）", fontsize=11, loc="left"); ax.set_ylabel("在庫（個）")
    axes[0].legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.32))
    fig.suptitle("月末の在庫だけを拾うと、入荷日によって平均が上にも下にもずれる", y=1.06)
    save(fig, "a522_daily_inventory.png", SRC)
    # 図2：シナリオ別の回転日数
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    SH = {"毎日入荷": "毎日", "月1回・月初（1日）": "月初", "月1回・月中（15日）": "月中", "月1回・月末": "月末"}
    lab = [f"{SH[r['入荷']]}\n{'山なし' if r['季節'] == '季節の山なし' else '12月に山'}" for r in rows]
    x = np.arange(len(rows)); w = .26
    for j, (k, c) in enumerate([("期首と期末の平均(日)", ORANGE), ("月末の平均（13点）(日)", LIGHT), ("毎日の平均(日)", BLUE)]):
        ax.bar(x + (j - 1) * w, tb[k], w, color=c, label=k.replace("(日)", ""))
    for i, r in tb.iterrows():
        ax.text(i - w, r["期首と期末の平均(日)"] + .3, f'{r["期首と期末の平均(日)"]:.1f}', ha="center", fontsize=7)
        ax.text(i + w, r["毎日の平均(日)"] + .3, f'{r["毎日の平均(日)"]:.1f}', ha="center", fontsize=7)
    ax.set_xticks(x, lab, fontsize=9); ax.set_ylabel("在庫回転日数（日）"); ax.set_xlabel("入荷のしかた（毎日、または月1回の入荷日）と売れ方の季節")
    ax.set_title("平均在庫の取り方で、在庫回転日数が変わる"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    ax.set_ylim(0, tb[["期首と期末の平均(日)", "月末の平均（13点）(日)", "毎日の平均(日)"]].to_numpy().max() * 1.25)
    save(fig, "a522_by_scenario.png", SRC)
    # 図3：季節の山の月を動かしたとき
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.axhline(0, color=GRAY, lw=.8)
    ax.plot(sp["山の月"], sp["毎日入荷：期首と期末のずれ(日)"], "o-", color=BLUE, label="毎日入荷")
    ax.plot(sp["山の月"], sp["月1回・月末：期首と期末のずれ(日)"], "s-", color=ORANGE, label="月1回・月末に入荷")
    ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)]); ax.set_xlabel("売れる山の月（振れ幅±50%、期は1〜12月）")
    ax.set_ylabel("期首と期末の平均 − 毎日の平均（日）")
    ax.set_title("期首・期末が売れ方の山や谷に当たると、2点の平均は大きくずれる"); ax.legend(frameon=False)
    save(fig, "a522_peak_month.png", SRC)
    print(tb.to_string()); print(sw.to_string()); print(sp.to_string()); print(res["sql_matches_python"])


if __name__ == "__main__":
    main()
