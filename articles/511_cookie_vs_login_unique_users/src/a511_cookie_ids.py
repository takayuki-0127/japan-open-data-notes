"""511 ログの利用者IDがCookieだと、同じ人が別人に数えられ、ユニーク利用者は何%多く出るのか（実務の型）

架空の利用者5,000人の1年分（2026年）のアクセスログを作る。本当の人ID・端末・Cookie を持たせ、
Cookie は端末ごとに一定の確率で消える（消えると新しい Cookie になる）。
同じログを「Cookie」「ログインID（ログインした訪問だけ）」「Cookie とログインIDのつなぎ合わせ」で数え、
本当の人数と比べる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 511
SRC = "架空のアクセスログ（作成者が乱数で作成、seed 511）"
DAYS = pd.date_range("2026-01-01", "2026-12-31", freq="D")


def make_log(n=5000, life=60.0, login_share=0.35, seed=SEED):
    """life：Cookie が消えるまでの平均日数（np.inf なら消えない）。端末は1〜3台"""
    rng = np.random.default_rng(seed)
    rate = rng.lognormal(np.log(0.12), 1.0, n)            # 1日あたりの訪問の多さ（人ごと）
    ndev = rng.choice([1, 2, 3], n, p=[0.45, 0.40, 0.15])
    logs_in = rng.random(n) < 0.6                           # ログインすることがある人（6割）
    rows = []
    cookie_seq = 0
    for i in range(n):
        k = rng.poisson(rate[i] * len(DAYS))
        if k == 0:
            continue
        d = np.sort(rng.integers(0, len(DAYS), k))
        w = np.r_[0.6, np.full(ndev[i] - 1, 0.4 / max(ndev[i] - 1, 1))] if ndev[i] > 1 else np.r_[1.0]
        dev = rng.choice(ndev[i], k, p=w / w.sum())
        # 端末ごとに Cookie を発行し、消えたら新しくする
        cur, born, dead = {}, {}, {}
        ck = np.empty(k, dtype=np.int64)
        for j in range(k):
            dv = dev[j]
            if dv not in cur or d[j] >= dead[dv]:
                cur[dv] = cookie_seq; cookie_seq += 1
                dead[dv] = d[j] + (rng.exponential(life) if np.isfinite(life) else 10 ** 9)
            ck[j] = cur[dv]
        login = logs_in[i] & (rng.random(k) < login_share / 0.6)
        rows.append(pd.DataFrame({"person": i, "day": d, "device": dev, "cookie": ck, "login": login}))
    df = pd.concat(rows, ignore_index=True)
    df["date"] = DAYS[df["day"].to_numpy()]
    df["login_id"] = np.where(df["login"], df["person"], -1)
    # つなぎ合わせ：一度でもログインした Cookie は、その人のIDとして数える
    stitched = df[df["login"]].groupby("cookie")["person"].first()
    df["stitch_id"] = df["cookie"].map(stitched).fillna(-1).astype(np.int64)
    df["stitch_key"] = np.where(df["stitch_id"] >= 0, "p" + df["stitch_id"].astype(str), "c" + df["cookie"].astype(str))
    return df


def uniques(df, freq):
    g = df.assign(per=df["date"].dt.to_period(freq))
    out = g.groupby("per").agg(true=("person", "nunique"), cookie=("cookie", "nunique"),
                               stitch=("stitch_key", "nunique"), visits=("person", "size"))
    lg = g[g["login"]].groupby("per")["person"].nunique()
    out["login"] = lg
    return out


def summarize(df):
    res = {}
    for name, fq in [("日", "D"), ("週", "W-SUN"), ("月", "M"), ("年", "Y")]:
        u = uniques(df, fq)
        res[name] = {"本当の人数": float(u["true"].mean()), "Cookie": float(u["cookie"].mean()),
                     "つなぎ合わせ": float(u["stitch"].mean()), "ログインIDのみ": float(u["login"].mean()),
                     "Cookie倍率": float((u["cookie"] / u["true"]).mean()),
                     "つなぎ合わせ倍率": float((u["stitch"] / u["true"]).mean()),
                     "ログインのみ倍率": float((u["login"] / u["true"]).mean()),
                     "1人あたり訪問_本当": float((u["visits"] / u["true"]).mean()),
                     "1人あたり訪問_Cookie": float((u["visits"] / u["cookie"]).mean())}
    return res


def main():
    df = make_log()
    df[["person", "date", "device", "cookie", "login"]].to_csv(DATA / "fictional_access_log.csv", index=False)
    base = summarize(df)
    # SQL（DuckDB）で月ごとの COUNT(DISTINCT) を出し、pandas と照合
    con = duckdb.connect()
    con.register("logs", df)
    q = open(SQL / "02_monthly_uniques_duckdb.sql").read()
    sm = con.execute(q).df()
    pm = uniques(df, "M")
    assert (sm["cookie_users"].to_numpy() == pm["cookie"].to_numpy()).all()
    assert (sm["true_users"].to_numpy() == pm["true"].to_numpy()).all()
    # Cookie の寿命を変える
    sweep = []
    for life in [np.inf, 365, 180, 90, 60, 30, 7]:
        s = summarize(make_log(life=life))
        sweep.append({"Cookieの平均寿命_日": "消えない" if not np.isfinite(life) else int(life),
                      **{f"{k}_Cookie倍率": round(v["Cookie倍率"], 3) for k, v in s.items()},
                      **{f"{k}_つなぎ合わせ倍率": round(v["つなぎ合わせ倍率"], 3) for k, v in s.items()}})
    sweep = pd.DataFrame(sweep)
    sweep.to_csv(RES / "sweep_cookie_life.csv", index=False)
    # 端末1台だけの人にしぼった場合（端末の違いの分を外す）
    one = df[df.groupby("person")["device"].transform("max") == 0]
    one_s = summarize(one)
    out = {"seed": SEED, "人数": int(df["person"].nunique()), "訪問": int(len(df)),
           "Cookieの数": int(df["cookie"].nunique()), "ログインした訪問の割合": float(df["login"].mean()),
           "基準_寿命60日": base, "端末1台の人だけ": {k: round(v["Cookie倍率"], 3) for k, v in one_s.items()},
           "SQLとpandasの一致": True}
    json.dump(out, open(RES / "a511_main.json", "w"), ensure_ascii=False, indent=1)
    pd.DataFrame(base).T.round(3).to_csv(RES / "uniques_by_period.csv")

    # 図1：期間の長さ別の倍率
    per = ["日", "週", "月", "年"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(4); wd = 0.26
    for j, (k, c, lb) in enumerate([("Cookie倍率", ORANGE, "Cookie で数える"), ("つなぎ合わせ倍率", BLUE, "ログインでつなぎ合わせる"), ("ログインのみ倍率", GRAY, "ログインIDだけで数える")]):
        v = [base[p][k] for p in per]
        ax.bar(x + (j - 1) * wd, v, wd, color=c, label=lb)
        for xi, vi in zip(x, v):
            ax.text(xi + (j - 1) * wd, vi + 0.04, f"{vi:.2f}", ha="center", fontsize=8.5)
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xticks(x, [f"{p}ごと" for p in per]); ax.set_ylabel("本当の人数に対する倍率")
    ax.set_title("期間が長いほど、Cookie のユニーク利用者は膨らむ")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a511_by_period.png", SRC + "。Cookie の平均寿命60日、端末1〜3台、ログインは訪問の35%")
    # 図2：Cookie の寿命を変えたとき（年・月）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    lab = sweep["Cookieの平均寿命_日"].astype(str).tolist()
    for k, c, mk in [("年", ORANGE, "o"), ("月", BLUE, "s"), ("日", GRAY, "^")]:
        ax.plot(lab, sweep[f"{k}_Cookie倍率"], marker=mk, color=c, label=f"{k}ごとのユニーク利用者")
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xlabel("Cookie が消えるまでの平均日数"); ax.set_ylabel("本当の人数に対する倍率")
    ax.set_title("Cookie が早く消えるほど、年の数は大きく膨らむ")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a511_cookie_life.png", SRC + "。端末1〜3台、seed は同じ")
    # 図3：1人あたり訪問回数
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    t = [base[p]["1人あたり訪問_本当"] for p in per]; c = [base[p]["1人あたり訪問_Cookie"] for p in per]
    ax.bar(x - 0.18, t, 0.36, color=BLUE, label="本当の人数で割る")
    ax.bar(x + 0.18, c, 0.36, color=ORANGE, label="Cookie の数で割る")
    for xi, a, b in zip(x, t, c):
        ax.text(xi - 0.18, a * 1.03, f"{a:.2f}", ha="center", fontsize=8.5); ax.text(xi + 0.18, b * 1.03, f"{b:.2f}", ha="center", fontsize=8.5)
    ax.set_yscale("log"); ax.set_xticks(x, [f"{p}ごと" for p in per]); ax.set_ylabel("1人あたりの訪問回数（対数目盛）")
    ax.set_title("Cookie で数えると、1人あたりの訪問は少なく見える")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a511_visits_per_user.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2500])
    print(sweep.to_string())


if __name__ == "__main__":
    main()
