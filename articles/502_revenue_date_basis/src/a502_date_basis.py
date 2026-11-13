"""502 売上を受注日・出荷日・検収日のどれで数えるかで、月の売上と前年同月比はどれだけ動くのか（実務の型）

架空の受注データ（小売型・法人向け型）を作り、同じ注文の金額を3つの日付で月に集計して比べる。
会計基準でどれを使うべきかを言うものではない。数字は置いた日数の分布で決まる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 502
SRC = "架空の受注データ（作成者が乱数で作成、seed 502）"
BASES = {"order_date": "受注日", "ship_date": "出荷日", "accept_date": "検収日"}


def make(kind, rng, start="2022-10-01", end="2025-12-31"):
    days = pd.date_range(start, end, freq="D")
    rows = []
    for d in days:
        t = (d - pd.Timestamp("2023-01-01")).days / 365
        level = 1.03 ** t * (0.92 if d >= pd.Timestamp("2025-07-01") else 1.0)   # 2025年7月から需要が8%落ちる
        if kind == "小売型":
            wk = 1.25 if d.dayofweek >= 5 else 0.93
            n = rng.poisson(40 * level * wk)
            amt = rng.lognormal(8.6, 0.6, n)
            lag1 = rng.integers(1, 4, n); lag2 = rng.integers(0, 3, n)
            ship = d + pd.to_timedelta(lag1, "D"); acc = ship + pd.to_timedelta(lag2, "D")
        else:
            if d.dayofweek >= 5:
                continue
            me = d >= (d + pd.offsets.MonthEnd(0)) - pd.Timedelta(days=6)      # 月末の最後の1週は受注が多い
            qe = d.month in (3, 6, 9, 12) and me
            n = rng.poisson(6 * level * (2.2 if qe else 1.6 if me else 1.0))
            amt = rng.lognormal(12.0, 0.9, n)
            lag1 = np.round(rng.lognormal(2.7, 0.55, n)).astype(int)         # 出荷まで 中央値15日
            lag2 = np.round(rng.lognormal(2.6, 0.6, n)).astype(int)          # 検収まで 中央値13日
            ship = d + pd.to_timedelta(lag1, "D"); acc = ship + pd.to_timedelta(lag2, "D")
            to_me = rng.random(n) < 0.5                                       # 半分は月末にまとめて検収
            acc = pd.DatetimeIndex(np.where(to_me, (acc + pd.offsets.MonthEnd(0)).values, acc.values))
        for a, s, c in zip(amt, ship, acc):
            rows.append((d, s, c, a))
    df = pd.DataFrame(rows, columns=["order_date", "ship_date", "accept_date", "amount"])
    df["amount"] = df["amount"].round(-1)
    df["kind"] = kind
    return df


def monthly(df):
    out = {}
    for c in BASES:
        out[c] = df.groupby(df[c].dt.to_period("M"))["amount"].sum()
    m = pd.DataFrame(out).loc["2023-01":"2025-12"]
    return m


def main():
    rng = np.random.default_rng(SEED)
    data = pd.concat([make("小売型", rng), make("法人向け型", rng)], ignore_index=True)
    data.to_csv(DATA / "fictional_orders.csv", index=False, date_format="%Y-%m-%d")
    res = {}
    # DuckDB で同じ月の集計を出し、pandas と一致することを確かめる
    con = duckdb.connect(); con.register("orders", data)
    q = open(SQL / "02_monthly_by_basis_duckdb.sql", encoding="utf-8").read()
    dq = con.sql(q).df()
    for kind in ["小売型", "法人向け型"]:
        d = data[data["kind"] == kind]
        m = monthly(d)
        chk = dq[dq["kind"] == kind].pivot(index="ym", columns="basis", values="amount")
        chk.index = pd.PeriodIndex(chk.index, freq="M")
        assert np.allclose(chk.loc[m.index, list(BASES)].values, m.values)
        m.to_csv(RES / f"monthly_{'retail' if kind == '小売型' else 'b2b'}.csv")
        diff = {}
        for c in ["ship_date", "accept_date"]:
            r = (m[c] / m["order_date"] - 1) * 100
            diff[c] = {"mean_abs_pct": round(float(r.abs().mean()), 2), "max_abs_pct": round(float(r.abs().max()), 2),
                       "max_month": str(r.abs().idxmax())}
        yoy = (m / m.shift(12) - 1).loc["2024-01":"2025-12"] * 100
        sign = np.sign(yoy)
        flips = int((sign.nunique(axis=1) > 1).sum())
        flips_oa = int((sign["order_date"] != sign["accept_date"]).sum())
        ann = m.groupby(m.index.year).sum()
        lags = {"ship_median": float((d["ship_date"] - d["order_date"]).dt.days.median()),
                "accept_median": float((d["accept_date"] - d["order_date"]).dt.days.median())}
        last3 = {}
        for c in BASES:
            x = d[(d[c] >= "2023-01-01") & (d[c] <= "2025-12-31")]
            me = x[c] >= (x[c] + pd.offsets.MonthEnd(0)) - pd.Timedelta(days=2)
            last3[c] = round(float(x.loc[me, "amount"].sum() / x["amount"].sum() * 100), 1)
        # 需要が落ちた月（2025年7月）を、前年同月比がマイナスとして最初に示すのはどの月か
        first_neg = {c: str(yoy[c][yoy[c] < -3].index.min()) if (yoy[c] < -3).any() else None for c in BASES}
        res[kind] = dict(diff=diff, yoy_flip_months=flips, yoy_flip_order_vs_accept=flips_oa, n_months=len(yoy),
                         annual_diff_pct={c: [round(float(v), 2) for v in (ann[c] / ann["order_date"] - 1) * 100] for c in BASES},
                         lags=lags, last3days_share=last3, first_month_yoy_below_minus3=first_neg,
                         yoy={c: {str(k): round(float(v), 2) for k, v in yoy[c].items()} for c in BASES})
        yoy.to_csv(RES / f"yoy_{'retail' if kind == '小売型' else 'b2b'}.csv")
    res["n_orders"] = data.groupby("kind").size().to_dict()
    json.dump(res, open(RES / "a502_main.json", "w"), ensure_ascii=False, indent=1)
    figs(data)
    print(json.dumps({k: {kk: v for kk, v in res[k].items() if kk != "yoy"} for k in ["小売型", "法人向け型"]}, ensure_ascii=False))


def figs(data):
    cols = {"order_date": GRAY, "ship_date": BLUE, "accept_date": ORANGE}
    b = data[data["kind"] == "法人向け型"]; m = monthly(b) / 1e6
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = m.index.to_timestamp()
    for c in BASES:
        ax.plot(x, m[c], color=cols[c], marker="o", ms=3, lw=1.6, label=BASES[c])
    ax.set_ylabel("月の売上（百万円）"); ax.legend(frameon=False, ncol=3)
    ax.set_title("法人向け型：同じ注文でも、数える日付で月の売上が動く")
    save(fig, "a502_monthly_b2b.png", SRC)
    fig, axes = plt.subplots(2, 1, figsize=(9, 3.8), sharex=True)
    for ax, kind in zip(axes, ["小売型", "法人向け型"]):
        mm = monthly(data[data["kind"] == kind])
        yoy = (mm / mm.shift(12) - 1).loc["2024-01":"2025-12"] * 100
        for i, c in enumerate(BASES):
            v = yoy[c].values
            ax.scatter(np.arange(len(v)), [2 - i] * len(v), c=[BLUE if t >= 0 else ORANGE for t in v], s=60, marker="s")
        ax.set_yticks([2, 1, 0], list(BASES.values())); ax.set_title(kind, fontsize=11, loc="left")
        ax.spines["left"].set_visible(False)
    axes[1].set_xticks(range(0, 24, 3), [f"{y}年{mo}月" for y in (2024, 2025) for mo in (1, 4, 7, 10)], fontsize=8.5)
    fig.suptitle("前年同月比の向き（青＝プラス、橙＝マイナス）", y=1.0)
    save(fig, "a502_yoy_sign.png", SRC)
    fig, ax = plt.subplots(figsize=(7.6, 4))
    lag1 = (b["ship_date"] - b["order_date"]).dt.days; lag2 = (b["accept_date"] - b["order_date"]).dt.days
    bins = np.arange(0, 121, 3)
    ax.hist(lag1.clip(upper=120), bins=bins, color=BLUE, alpha=0.7, label="受注→出荷")
    ax.hist(lag2.clip(upper=120), bins=bins, color=ORANGE, alpha=0.6, label="受注→検収")
    ax.set_xlabel("受注からの日数"); ax.set_ylabel("注文の数"); ax.legend(frameon=False)
    ax.set_title("法人向け型：受注から出荷・検収までの日数")
    save(fig, "a502_lags.png", SRC)


if __name__ == "__main__":
    main()
