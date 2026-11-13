"""521 問い合わせの対応時間を「営業時間」で数えるか「暦の時間」で数えるかで、期限内に返せた割合は何ポイント変わるのか（実務の型）

架空の問い合わせ（2025年の1年分）を作る。窓口は平日9〜18時だけ動き（土日・祝日・12/29〜1/3は休み）、
初回の返信は「営業時間で数えた経過時間」に従って出す。同じ記録を、暦の時間と営業時間の2通りで数え、
期限内（4・8・24時間）に返せた割合を比べる。営業時間の経過は Python と SQL（DuckDB）の両方で数え、一致を確かめる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 521
SRC = "架空の問い合わせ記録（作成者が乱数で作成、seed 521）。祝日は内閣府「国民の祝日」"
OPEN, CLOSE = 9, 18                      # 営業時間 9:00〜18:00（1日540分）
DAYS = pd.date_range("2024-12-01", "2026-02-28", freq="D")


def calendar():
    hol = set(pd.to_datetime(pd.read_csv(DATA / "holidays_2025.csv").iloc[:, 0]).dt.date)
    cal = pd.DataFrame({"d": DAYS})
    md = cal.d.dt.strftime("%m-%d")
    cal["biz"] = (cal.d.dt.weekday < 5) & ~cal.d.dt.date.isin(hol) & ~md.isin(["12-29", "12-30", "12-31", "01-01", "01-02", "01-03"])
    cal["mins"] = np.where(cal.biz, (CLOSE - OPEN) * 60, 0)
    cal["cum_before"] = cal.mins.cumsum() - cal.mins          # その日の0時までに過ぎた営業分
    return cal


CAL = calendar()
D0 = DAYS[0]


def biz_index(ts):
    """時刻 → それまでに過ぎた営業分（累積）。差を取れば営業時間の経過になる"""
    ts = pd.to_datetime(pd.Series(ts))
    di = (ts.dt.normalize() - D0).dt.days.to_numpy()
    m = (ts.dt.hour * 60 + ts.dt.minute + ts.dt.second / 60).to_numpy()
    within = np.clip(m - OPEN * 60, 0, (CLOSE - OPEN) * 60)
    return CAL.cum_before.to_numpy()[di] + np.where(CAL.biz.to_numpy()[di], within, 0)


def from_biz_index(x):
    """累積の営業分 → 時刻（返信の時刻を作るのに使う）"""
    cb, mins = CAL.cum_before.to_numpy(), CAL.mins.to_numpy()
    di = np.searchsorted(cb + mins, x, side="left")
    di = np.minimum(di, len(CAL) - 1)
    # x がちょうど営業日の終わりなら、その日の18時
    off = x - cb[di]
    return DAYS[di] + pd.to_timedelta(OPEN * 60 + off, unit="m")


def make(n=30000, seed=SEED):
    rng = np.random.default_rng(seed)
    days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    # 受付の日：平日に多め。受付の時刻：日中に多く、夜や朝にも来る
    wdw = np.where(days.weekday < 5, 1.0, 0.45)
    d = rng.choice(len(days), n, p=wdw / wdw.sum())
    hour_w = np.array([1, .6, .4, .3, .3, .4, .8, 1.5, 2.5, 4, 4.5, 4.3, 3, 4, 4.3, 4.2, 4, 3.6, 3, 2.6, 2.4, 2.2, 1.9, 1.4])
    hr = rng.choice(24, n, p=hour_w / hour_w.sum())
    t = days[d] + pd.to_timedelta(hr * 60 + rng.integers(0, 60, n), unit="m")
    # 担当者は営業時間だけ動く：返信までの「営業分」は対数正規（中央値150分）
    need = rng.lognormal(np.log(150), 0.9, n)
    bi = biz_index(t)
    reply = from_biz_index(bi + need)
    df = pd.DataFrame({"id": np.arange(1, n + 1), "received": t, "replied": pd.to_datetime(reply).floor("s")}).sort_values("received", ignore_index=True)
    df["id"] = np.arange(1, n + 1)
    return df


def slot(r):
    """受付の時間帯の区分"""
    hol = set(pd.to_datetime(pd.read_csv(DATA / "holidays_2025.csv").iloc[:, 0]).dt.date)
    nextbiz = []
    out = []
    for ts in r:
        dd = ts.normalize()
        biz = bool(CAL.biz.iloc[(dd - D0).days])
        h = ts.hour + ts.minute / 60
        if biz and OPEN <= h < CLOSE:
            out.append("平日の営業時間内")
            continue
        # 次の営業日の朝までの暦の時間
        k = (dd - D0).days + (1 if (not biz or h >= CLOSE) else 0)
        while not CAL.biz.iloc[k]:
            k += 1
        wait = (DAYS[k] + pd.Timedelta(hours=OPEN) - ts) / pd.Timedelta(hours=1)
        if wait <= 16:
            out.append("平日の夜・朝")
        elif wait <= 64:
            out.append("週末（金曜夜〜日曜）")
        else:
            out.append("3連休以上の前・最中")
    return pd.Series(out)


def main():
    df = make()
    df.to_csv(DATA / "fictional_inquiries.csv", index=False)
    df["cal_h"] = (df.replied - df.received) / pd.Timedelta(hours=1)
    df["biz_h"] = (biz_index(df.replied) - biz_index(df.received)) / 60
    df["slot"] = slot(df.received)
    df["wd"] = df.received.dt.weekday
    # SQL（DuckDB）で営業時間の経過を数え、Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1")
    cal = CAL.assign(d=CAL.d.dt.date)
    con.register("cal", cal); con.register("inq", df[["id", "received", "replied"]])
    q = open(SQL / "02_business_minutes_duckdb.sql", encoding="utf-8").read()
    s = con.execute(q).df().sort_values("id")
    sql_ok = bool(np.allclose(s.biz_min.to_numpy() / 60, df.sort_values("id").biz_h.to_numpy(), atol=1e-6))

    TH = [4, 8, 24]
    res = {"n": len(df), "sql_matches_python": sql_ok, "median_cal_h": round(df.cal_h.median(), 2), "median_biz_h": round(df.biz_h.median(), 2)}
    rows = []
    for th in TH:
        c, b = (df.cal_h <= th).mean() * 100, (df.biz_h <= th).mean() * 100
        rows.append({"期限（時間）": th, "暦の時間で期限内(%)": round(c, 1), "営業時間で期限内(%)": round(b, 1), "差(pt)": round(b - c, 1)})
    tb = pd.DataFrame(rows); tb.to_csv(RES / "within_by_threshold.csv", index=False); res["by_threshold"] = rows
    order = ["平日の営業時間内", "平日の夜・朝", "週末（金曜夜〜日曜）", "3連休以上の前・最中"]
    rs = []
    for k in order:
        g = df[df.slot == k]
        c, b = (g.cal_h <= 8).mean() * 100, (g.biz_h <= 8).mean() * 100
        rs.append({"受付": k, "件数": len(g), "暦8時間以内(%)": round(c, 1), "営業8時間以内(%)": round(b, 1), "差(pt)": round(b - c, 1),
                   "暦の時間の中央値(h)": round(g.cal_h.median(), 1), "営業時間の中央値(h)": round(g.biz_h.median(), 1)})
    ts = pd.DataFrame(rs); ts.to_csv(RES / "within8_by_slot.csv", index=False); res["by_slot_8h"] = rs
    names = ["月", "火", "水", "木", "金", "土", "日"]
    rw = []
    for w in range(7):
        g = df[df.wd == w]
        rw.append({"曜日": names[w], "件数": len(g), "暦24時間以内(%)": round((g.cal_h <= 24).mean() * 100, 1), "営業8時間以内(%)": round((g.biz_h <= 8).mean() * 100, 1),
                   "暦8時間以内(%)": round((g.cal_h <= 8).mean() * 100, 1)})
    tw = pd.DataFrame(rw); tw.to_csv(RES / "within_by_weekday.csv", index=False); res["by_weekday"] = rw
    # 同じ「24時間」でも暦と営業で、合否が入れ替わる件数
    res["flip_24h_cal_fail_biz_ok"] = int(((df.cal_h > 24) & (df.biz_h <= 24)).sum())
    res["flip_8h_cal_fail_biz_ok"] = int(((df.cal_h > 8) & (df.biz_h <= 8)).sum())
    res["max_cal_h"] = round(df.cal_h.max(), 1)
    json.dump(res, open(RES / "a521_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：期限ごとの期限内の割合
    fig, ax = plt.subplots(figsize=(7.2, 4))
    x = np.arange(len(TH)); w = .36
    ax.bar(x - w / 2, tb["暦の時間で期限内(%)"], w, color=GRAY, label="暦の時間で数える")
    ax.bar(x + w / 2, tb["営業時間で期限内(%)"], w, color=BLUE, label="営業時間で数える")
    for i, r in tb.iterrows():
        ax.text(i - w / 2, r["暦の時間で期限内(%)"] + 1, f'{r["暦の時間で期限内(%)"]:.1f}', ha="center", fontsize=9)
        ax.text(i + w / 2, r["営業時間で期限内(%)"] + 1, f'{r["営業時間で期限内(%)"]:.1f}', ha="center", fontsize=9)
    ax.set_xticks(x, [f"{t}時間以内" for t in TH]); ax.set_ylim(0, 108); ax.set_ylabel("期限内に初回返信できた割合（%）")
    ax.set_title("同じ記録でも、数え方で期限内の割合が変わる"); ax.legend(frameon=False, loc="lower right")
    save(fig, "a521_by_threshold.png", SRC)
    # 図2：受付の時間帯ごと（8時間）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    y = np.arange(len(order))[::-1]
    ax.barh(y + .2, ts["暦8時間以内(%)"], .38, color=GRAY, label="暦の8時間以内")
    ax.barh(y - .2, ts["営業8時間以内(%)"], .38, color=BLUE, label="営業時間の8時間以内")
    for yy, (_, r) in zip(y, ts.iterrows()):
        ax.text(r["暦8時間以内(%)"] + 1, yy + .2, f'{r["暦8時間以内(%)"]:.1f}', va="center", fontsize=9)
        ax.text(r["営業8時間以内(%)"] + 1, yy - .2, f'{r["営業8時間以内(%)"]:.1f}（{int(r["件数"]):,}件）', va="center", fontsize=9)
    ax.set_yticks(y, order); ax.set_xlim(0, 118); ax.set_xlabel("8時間以内に初回返信できた割合（%）")
    ax.set_title("営業時間の外に来た問い合わせほど、暦の時間では遅れて見える"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    save(fig, "a521_by_slot.png", SRC, y=-0.11)
    # 図3：曜日別
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.plot(names, tw["営業8時間以内(%)"], "o-", color=BLUE, label="営業時間の8時間以内")
    ax.plot(names, tw["暦24時間以内(%)"], "s-", color=ORANGE, label="暦の24時間以内")
    ax.plot(names, tw["暦8時間以内(%)"], "^-", color=GRAY, label="暦の8時間以内")
    for i, r in tw.iterrows():
        ax.text(i, r["暦24時間以内(%)"] + (-8 if i < 4 else 3), f'{r["暦24時間以内(%)"]:.0f}', ha="center", fontsize=8, color=ORANGE)
    ax.set_ylim(0, 105); ax.set_ylabel("期限内の割合（%）"); ax.set_xlabel("受付の曜日")
    ax.set_title("受付の曜日で、暦の時間の期限内の割合は大きく変わる"); ax.legend(frameon=False, loc="lower left", fontsize=9)
    save(fig, "a521_by_weekday.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
