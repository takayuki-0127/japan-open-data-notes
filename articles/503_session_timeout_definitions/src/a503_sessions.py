"""503 ログの「セッション」を何分空いたら切るかで、セッション数と1回あたりの滞在はどれだけ変わるのか（実務の型）

架空のアクセスログを作り（本当の「訪問」が分かっている）、切る時間を5〜120分に変えてセッションを作り直す。
日付が変わったところで切るかどうかも比べる。数字は置いた閲覧の間隔の分布で決まる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 503
SRC = "架空のアクセスログ（作成者が乱数で作成、seed 503）"
TIMEOUTS = [5, 10, 15, 20, 30, 45, 60, 90, 120]


def make(n_users=3000, seed=SEED):
    rng = np.random.default_rng(seed)
    rows = []; vid = 0
    t0 = pd.Timestamp("2026-03-01")
    for u in range(n_users):
        nv = 1 + rng.poisson(2.5)
        starts = np.sort(rng.uniform(0, 28 * 24 * 3600, nv))
        for s in starts:
            npages = rng.geometric(0.28)                          # 1ページだけの訪問は28%
            t = s; times = [t]
            for k in range(npages - 1):
                z = rng.random()
                if z < 0.80:
                    g = rng.lognormal(np.log(45), 0.9)            # ふつうの閲覧：中央値45秒
                elif z < 0.95:
                    g = rng.uniform(180, 900)                     # 読み込む：3〜15分
                else:
                    g = rng.uniform(900, 2700)                    # 席を外して戻る：15〜45分
                t += g; times.append(t)
            for tt in times:
                rows.append((u, vid, tt))
            vid += 1
            if rng.random() < 0.12:                               # すぐ戻ってくる別の訪問（10〜60分後）
                t2 = times[-1] + rng.uniform(600, 3600)
                for k in range(rng.geometric(0.4)):
                    rows.append((u, vid, t2 + 40 * k))
                vid += 1
    df = pd.DataFrame(rows, columns=["user", "visit", "sec"]).sort_values(["user", "sec"]).reset_index(drop=True)
    df["ts"] = t0 + pd.to_timedelta(df["sec"], unit="s")
    return df[["user", "visit", "ts"]]


def sessionize(df, minutes, cut_midnight=False):
    g = df.groupby("user")["ts"]
    gap = g.diff()
    new = gap.isna() | (gap > pd.Timedelta(minutes=minutes))
    if cut_midnight:
        new |= df["ts"].dt.date != df.groupby("user")["ts"].shift().dt.date
    return new.groupby(df["user"]).cumsum().astype(int)


def evaluate(df, sid):
    key = df["user"].astype(str) + "_" + sid.astype(str)
    sess = df.groupby(key)
    n_s = sess.ngroups
    pages = df.groupby(key).size()
    # 本当の訪問との一致：その訪問の全ページがちょうど1つのセッションで、そのセッションにほかの訪問がない
    nsess_per_visit = pd.Series(key.values, index=df.index).groupby(df["visit"]).nunique()
    nvisit_per_sess = df["visit"].groupby(key).nunique()
    sess_of_visit = pd.Series(key.values).groupby(df["visit"].values).first()
    exact = (nsess_per_visit == 1) & (sess_of_visit.map(nvisit_per_sess) == 1)
    return dict(sessions=int(n_s), pages_per_session=float(pages.mean()), bounce=float((pages == 1).mean()),
                exact_visit_share=float(exact.mean()), split_visit_share=float((nsess_per_visit > 1).mean()),
                merged_session_share=float((nvisit_per_sess > 1).mean()))


def main():
    df = make()
    df.to_csv(DATA / "fictional_pageviews.csv", index=False)
    truth = df.groupby("visit").size()
    out = {"pageviews": len(df), "users": int(df["user"].nunique()), "true_visits": int(df["visit"].nunique()),
           "true_pages_per_visit": float(truth.mean()), "true_bounce": float((truth == 1).mean())}
    rows = []
    for m in TIMEOUTS:
        for cut in (False, True):
            e = evaluate(df, sessionize(df, m, cut))
            rows.append({"timeout_min": m, "cut_midnight": cut, **e})
    tab = pd.DataFrame(rows); tab.to_csv(RES / "timeouts.csv", index=False)
    out["table"] = tab.round(4).to_dict(orient="records")
    # DuckDB のウィンドウ関数で30分のセッションを作り、pandas と同じ数になるか
    con = duckdb.connect(); con.register("pv", df)
    q = open(SQL / "02_sessionize_duckdb.sql", encoding="utf-8").read()
    n_sql = con.sql(q).fetchone()[0]
    n_pd = int(tab.query("timeout_min==30 and not cut_midnight")["sessions"].iloc[0])
    assert n_sql == n_pd, (n_sql, n_pd)
    out["sql_check_30min"] = int(n_sql)
    # 日をまたぐ訪問の数
    span = df.groupby("visit")["ts"].agg(["min", "max"])
    out["visits_crossing_midnight"] = int((span["min"].dt.date != span["max"].dt.date).sum())
    gaps = df.groupby("user")["ts"].diff().dt.total_seconds().dropna() / 60
    same = (df["visit"] == df.groupby("user")["visit"].shift())[df.groupby("user")["ts"].diff().notna()]
    out["within_gap_over30_share"] = float((gaps[same.values] > 30).mean())
    out["between_gap_under30_share"] = float((gaps[~same.values] <= 30).mean())
    json.dump(out, open(RES / "a503_main.json", "w"), ensure_ascii=False, indent=1)
    figs(df, tab, out, gaps, same)
    print(json.dumps({k: v for k, v in out.items() if k != "table"}, ensure_ascii=False))
    print(tab.round(3).to_string())


def figs(df, tab, out, gaps, same):
    t = tab[~tab["cut_midnight"]].set_index("timeout_min")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(t.index, t["sessions"] / out["true_visits"] * 100, marker="o", color=BLUE, label="セッション数（本当の訪問＝100）")
    ax.plot(t.index, t["exact_visit_share"] * 100, marker="s", color=ORANGE, label="本当の訪問とちょうど一致した割合（%）")
    ax.axhline(100, color=GRAY, lw=0.8, ls="--")
    ax.set_xscale("log"); ax.set_xticks(t.index, [str(m) for m in t.index]); ax.set_xlabel("この分より空いたら切る")
    ax.legend(frameon=False, fontsize=9.5); ax.set_title("切る時間を変えると、セッション数と一致の割合が動く")
    save(fig, "a503_timeouts.png", SRC)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(t.index, t["pages_per_session"], marker="o", color=BLUE, label="1回あたりのページ数")
    ax2 = ax.twinx()
    ax2.plot(t.index, t["bounce"] * 100, marker="s", color=ORANGE, label="1ページだけのセッション（%）")
    ax.axhline(out["true_pages_per_visit"], color=BLUE, lw=0.8, ls="--"); ax2.axhline(out["true_bounce"] * 100, color=ORANGE, lw=0.8, ls="--")
    ax.set_xscale("log"); ax.set_xticks(t.index, [str(m) for m in t.index]); ax.set_xlabel("この分より空いたら切る")
    ax.set_ylabel("ページ数", color=BLUE); ax2.set_ylabel("%", color=ORANGE); ax2.spines["right"].set_visible(True)
    ax.set_title("1回あたりのページ数と、1ページだけの割合（破線は本当の訪問）")
    save(fig, "a503_pages_bounce.png", SRC)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.logspace(-1.5, 3.5, 60)
    ax.hist(gaps[same.values].clip(lower=0.03), bins=bins, color=BLUE, alpha=0.7, label="同じ訪問の中の間隔")
    ax.hist(gaps[~same.values].clip(lower=0.03), bins=bins, color=ORANGE, alpha=0.6, label="訪問と訪問の間")
    ax.axvline(30, color=INK, lw=1); ax.text(32, ax.get_ylim()[1] * 0.9, "30分", fontsize=9)
    ax.set_xscale("log"); ax.set_xlabel("前のページからの時間（分）"); ax.set_ylabel("ページの数"); ax.legend(frameon=False)
    ax.set_title("2つの間隔の分布は重なっていて、どこで切っても混ざる")
    save(fig, "a503_gaps.png", SRC)


if __name__ == "__main__":
    main()
