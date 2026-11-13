"""524 深夜まで営業する店で、売上を暦日で切るか「朝5時締めの営業日」で切るかで、曜日別の売上はどれだけ変わるのか（実務の型）

架空の店（17時〜翌3時に営業、2025年1年分）の1時間ごとの売上を作る。同じ売上を
  - 暦日：0時で切る（日付そのまま）
  - 営業日：朝5時で切る（0〜4時台の売上は前の日の営業日に入れる）
で日ごとに集計し、曜日別・月別の売上を比べる。深夜（0時以降）の売上の割合を変えてもくり返す。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 524
SRC = "架空の店の時間帯別売上（作成者が乱数で作成、seed 524）"
NAMES = ["月", "火", "水", "木", "金", "土", "日"]
# 営業日（夕方の曜日）ごとの売上の大きさと、0時以降の割合
LEVEL = np.array([0.80, 0.85, 0.90, 1.00, 1.35, 1.30, 0.75])
LATE = np.array([0.15, 0.15, 0.18, 0.22, 0.35, 0.40, 0.12])
EVE_W = np.array([.06, .14, .20, .22, .20, .13, .05])      # 17〜23時の配分
LATE_W = np.array([.45, .32, .23])                           # 0〜2時の配分
DAILY = 300_000                                              # 平均的な営業日の売上（円）


def make(late_mult=1.0, seed=SEED):
    rng = np.random.default_rng(seed)
    bdays = pd.date_range("2024-12-31", "2025-12-31", freq="D")    # 12/31夜の分を1/1の0〜2時に入れるため前日から
    rows = []
    for d in bdays:
        w = d.weekday()
        tot = DAILY * LEVEL[w] * rng.lognormal(0, 0.12)
        late = min(LATE[w] * late_mult, 0.9)
        eve = tot * (1 - late) * EVE_W * rng.lognormal(0, 0.05, 7)
        lat = tot * late * LATE_W * rng.lognormal(0, 0.05, 3)
        for h, v in zip(range(17, 24), eve):
            rows.append((d + pd.Timedelta(hours=h), v))
        for h, v in zip(range(0, 3), lat):
            rows.append((d + pd.Timedelta(days=1, hours=h), v))
    df = pd.DataFrame(rows, columns=["hour_start", "sales"])
    df["sales"] = df.sales.round(0)
    return df[(df.hour_start >= "2025-01-01") & (df.hour_start < "2026-01-01 05:00")].reset_index(drop=True)


def daily(df, cut=5):
    cal = df.groupby(df.hour_start.dt.normalize()).sales.sum()
    bus = df.groupby((df.hour_start - pd.Timedelta(hours=cut)).dt.normalize()).sales.sum()
    rng = pd.date_range("2025-01-01", "2025-12-31")
    return cal.reindex(rng, fill_value=0), bus.reindex(rng, fill_value=0)


def by_weekday(s):
    g = s.groupby(s.index.weekday).mean()
    return g.reindex(range(7))


def main():
    df = make()
    df.to_csv(DATA / "fictional_hourly_sales.csv", index=False)
    cal, bus = daily(df)
    wc, wb = by_weekday(cal), by_weekday(bus)
    tw = pd.DataFrame({"曜日": NAMES, "暦日の平均(円)": wc.round(0).astype(int), "営業日の平均(円)": wb.round(0).astype(int)})
    tw["差(%)"] = ((wc / wb - 1) * 100).round(1).to_numpy()
    tw["暦日の順位"] = wc.rank(ascending=False).astype(int).to_numpy(); tw["営業日の順位"] = wb.rank(ascending=False).astype(int).to_numpy()
    tw.to_csv(RES / "by_weekday.csv", index=False)
    mc, mb = cal.groupby(cal.index.month).sum(), bus.groupby(bus.index.month).sum()
    tm = pd.DataFrame({"月": range(1, 13), "暦日(円)": mc.astype(int).to_numpy(), "営業日(円)": mb.astype(int).to_numpy()})
    tm["差(円)"] = tm["暦日(円)"] - tm["営業日(円)"]; tm["差(%)"] = (tm["差(円)"] / tm["営業日(円)"] * 100).round(2)
    tm.to_csv(RES / "by_month.csv", index=False)
    late_share = float(df[df.hour_start.dt.hour < 5].sales.sum() / df.sales.sum())

    # SQL（DuckDB）で営業日の集計をして、Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", df)
    s = con.execute(open(SQL / "02_business_day_duckdb.sql", encoding="utf-8").read()).df().set_index("business_date").sales
    s.index = pd.to_datetime(s.index); s = s[(s.index >= "2025-01-01") & (s.index <= "2025-12-31")]
    sql_ok = bool(np.allclose(s.reindex(bus.index, fill_value=0).to_numpy(), bus.to_numpy()))

    # 深夜の割合を変える
    sw = []
    for m in [0, 0.5, 1.0, 1.5, 2.0]:
        c, b = daily(make(m)); wc2, wb2 = by_weekday(c), by_weekday(b)
        d = make(m); ls = float(d[d.hour_start.dt.hour < 5].sales.sum() / d.sales.sum())
        diff = (wc2 / wb2 - 1) * 100
        sw.append({"深夜の割合の倍率": m, "0時以降の売上の割合(%)": round(ls * 100, 1), "土曜の差(%)": round(diff[5], 1), "日曜の差(%)": round(diff[6], 1),
                   "金曜の差(%)": round(diff[4], 1), "最大の差(%)": round(diff.abs().max(), 1),
                   "暦日で1位の曜日": NAMES[int(wc2.idxmax())], "営業日で1位の曜日": NAMES[int(wb2.idxmax())]})
    sw = pd.DataFrame(sw); sw.to_csv(RES / "sweep_late_share.csv", index=False)
    res = {"sql_matches_python": sql_ok, "late_share_pct": round(late_share * 100, 1), "by_weekday": tw.to_dict("records"),
           "month_diff_pct_range": [float(tm["差(%)"].min()), float(tm["差(%)"].max())], "year_total_cal": int(cal.sum()), "year_total_bus": int(bus.sum())}
    json.dump(res, open(RES / "a524_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：曜日別
    fig, ax = plt.subplots(figsize=(7.4, 4.2)); x = np.arange(7); w = .38
    ax.bar(x - w / 2, wc / 1e4, w, color=GRAY, label="暦日（0時で切る）")
    ax.bar(x + w / 2, wb / 1e4, w, color=BLUE, label="営業日（朝5時で切る）")
    for i in range(7):
        ax.text(i, max(wc[i], wb[i]) / 1e4 + 1, f'{tw["差(%)"][i]:+.0f}%', ha="center", fontsize=9, color=ORANGE if abs(tw["差(%)"][i]) >= 10 else INK)
    ax.set_xticks(x, [f"{n}曜" for n in NAMES]); ax.set_ylabel("1日あたりの売上（万円）")
    ax.set_title("暦日で切ると、金曜の夜の売上が土曜に、土曜の夜の売上が日曜に移る", fontsize=12); ax.legend(frameon=False, loc="upper left")
    ax.set_ylim(0, max(wc.max(), wb.max()) / 1e4 * 1.2)
    save(fig, "a524_by_weekday.png", SRC)
    # 図2：月別の差
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(tm["月"], tm["差(%)"], color=[ORANGE if v > 0 else BLUE for v in tm["差(%)"]])
    for _, r in tm.iterrows():
        ax.text(r["月"], r["差(%)"] + (0.03 if r["差(%)"] >= 0 else -0.03), f'{r["差(%)"]:+.2f}%', ha="center", va="bottom" if r["差(%)"] >= 0 else "top", fontsize=8)
    ax.axhline(0, color=GRAY, lw=.8); ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)])
    ax.set_ylabel("暦日 − 営業日（営業日に対する%）"); ax.set_title("月の売上の差は小さく、月末と月初の曜日で決まる")
    lim = max(abs(tm["差(%)"]).max() * 1.4, 0.5); ax.set_ylim(-lim, lim)
    save(fig, "a524_by_month.png", SRC)
    # 図3：深夜の割合を変える
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.plot(sw["0時以降の売上の割合(%)"], sw["土曜の差(%)"], "o-", color=ORANGE, label="土曜")
    ax.plot(sw["0時以降の売上の割合(%)"], sw["日曜の差(%)"], "s-", color=GREEN, label="日曜")
    ax.plot(sw["0時以降の売上の割合(%)"], sw["金曜の差(%)"], "^-", color=BLUE, label="金曜")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xlabel("0時以降の売上の割合（年間、%）"); ax.set_ylabel("暦日の売上 − 営業日の売上（%）")
    ax.set_title("深夜の売上が多い店ほど、曜日別の売上のずれは大きい"); ax.legend(frameon=False)
    save(fig, "a524_late_share.png", SRC)
    print(tw.to_string()); print(tm.to_string()); print(sw.to_string()); print(res["late_share_pct"], sql_ok)


if __name__ == "__main__":
    main()
