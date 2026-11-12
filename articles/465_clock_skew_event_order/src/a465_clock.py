"""465 サーバーごとに時計がずれていると、ログの出来事の順番は何件逆になるのか（架空のアクセスログ、seed 465）"""
import json
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, BLUE, ORANGE, GRAY, LIGHT, GREEN, save

SRC = "架空のアクセスログ（作成者が乱数で作成、seed 465）"
N_USER, N_SRV = 5000, 4


def make(seed, skew_sd=1.0, gap_median=2.0, sticky=False, n_user=N_USER, n_srv=N_SRV):
    """出来事のログを作る。true_t＝本当の時刻（秒）、rec_t＝サーバーの時計で記録された時刻"""
    rng = np.random.default_rng(seed)
    n_ev = rng.integers(4, 13, n_user)                                   # 1人あたり4〜12件
    user = np.repeat(np.arange(n_user), n_ev); n = user.size
    start = rng.uniform(0, 3600, n_user)                                 # 1時間のどこかで始まる
    # 出来事の間隔：短いもの（画面の中の続けての操作・自動の読み込み）と長いもの（ページを読む時間）が混ざる
    short = rng.random(n) < 0.35
    gap = np.where(short, rng.lognormal(np.log(0.3), 0.7, n), rng.lognormal(np.log(gap_median * 4), 0.9, n))
    first = np.r_[True, user[1:] != user[:-1]]
    gap[first] = 0
    cs = np.cumsum(gap); base = np.maximum.accumulate(np.where(first, cs, -np.inf))
    true_t = start[user] + (cs - base)
    seq_in_user = (np.arange(n) - np.maximum.accumulate(np.where(first, np.arange(n), 0)))
    offset = rng.normal(0, skew_sd, n_srv)                               # サーバーごとの時計のずれ（秒）
    srv = (rng.integers(0, n_srv, n_user)[user] if sticky else rng.integers(0, n_srv, n))
    rec_t = np.round(true_t + offset[srv], 3)                            # ミリ秒まで記録
    # 出来事の種類：最初は必ず「入口」、最後の1つ前までに「かごに入れる」、最後が「購入」の人が3割
    kind = np.full(n, "閲覧", dtype=object); kind[first] = "入口"
    last = np.r_[user[1:] != user[:-1], True]
    buyer = rng.random(n_user) < 0.3
    kind[last & buyer[user]] = "購入"
    df = pd.DataFrame({"user_id": user, "seq": seq_in_user, "true_t": true_t, "server": srv, "rec_t": rec_t, "kind": kind})
    # 通し番号：入口の装置（1台）が受け取った順に振る番号＝本当の時刻の順
    df["gw_seq"] = df.true_t.rank(method="first").astype(int)
    return df, offset


def measure(df):
    """記録された時刻で並べたときの、ずれの大きさを測る"""
    d = df.sort_values(["user_id", "seq"])
    same = d.user_id.to_numpy()[1:] == d.user_id.to_numpy()[:-1]
    dt = d.rec_t.to_numpy()[1:] - d.rec_t.to_numpy()[:-1]
    inv_pairs = float((dt[same] < 0).mean() * 100)                       # となりの出来事の順が逆
    neg = int((dt[same] < 0).sum())
    # 記録された時刻で並べ直す
    r = df.sort_values(["user_id", "rec_t", "seq"])
    first_rec = r.groupby("user_id").head(1)
    first_wrong = float((first_rec.kind != "入口").mean() * 100)          # 「最初の出来事」が入口でなくなった人
    # 購入の直前の出来事：本当は seq が1つ前のもの
    r = r.assign(prev_seq=r.groupby("user_id").seq.shift(1))
    buy = r[r.kind == "購入"]
    prev_wrong = float((buy.prev_seq != buy.seq - 1).mean() * 100)
    # 1人の中で、並び順が1か所でも変わった人
    order_changed = float((r.groupby("user_id").seq.apply(lambda s: not s.is_monotonic_increasing)).mean() * 100)
    # 所要時間（入口から最後まで）：記録の時刻の差
    g = df.groupby("user_id")
    dur_true = g.true_t.max() - g.true_t.min()
    lastrow = df.sort_values(["user_id", "seq"]).groupby("user_id").tail(1).set_index("user_id")
    firstrow = df.sort_values(["user_id", "seq"]).groupby("user_id").head(1).set_index("user_id")
    dur_rec = lastrow.rec_t - firstrow.rec_t
    return {"となりの出来事の順が逆%": inv_pairs, "間隔がマイナスになった件数": neg, "最初の出来事が変わった人%": first_wrong,
            "購入の直前の出来事が変わった人%": prev_wrong, "並びが1か所でも変わった人%": order_changed,
            "所要時間のずれの中央値（秒）": float((dur_rec - dur_true).abs().median()),
            "所要時間が1秒以上ずれた人%": float(((dur_rec - dur_true).abs() >= 1).mean() * 100)}


def main():
    res = {}
    con = duckdb.connect()
    df, off = make(465)
    DATA.mkdir(exist_ok=True); df.head(3000).round(3).to_csv(DATA / "access_log_sample.csv", index=False)
    res["setup"] = {"人": N_USER, "出来事": len(df), "サーバー": N_SRV, "時計のずれ（秒）": [round(float(x), 2) for x in off],
                    "間隔の中央値（秒）": round(float(df.sort_values(["user_id", "seq"]).groupby("user_id").true_t.diff().median()), 2),
                    "間隔が1秒未満の割合%": round(float((df.sort_values(["user_id", "seq"]).groupby("user_id").true_t.diff().dropna() < 1).mean() * 100), 1)}
    base = measure(df); res["base"] = {k: round(v, 1) for k, v in base.items()}

    # SQL でも同じ数を出す（LAG で前の出来事との間隔を見る）
    con.register("log", df)
    q = con.execute("""SELECT SUM(CASE WHEN d < 0 THEN 1 ELSE 0 END), COUNT(d) FROM
                       (SELECT rec_t - LAG(rec_t) OVER (PARTITION BY user_id ORDER BY seq) AS d FROM log)""").fetchone()
    assert int(q[0]) == base["間隔がマイナスになった件数"]
    q2 = con.execute("""SELECT AVG(CASE WHEN kind <> '入口' THEN 1.0 ELSE 0 END) * 100 FROM
                        (SELECT kind, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY rec_t, seq) rn FROM log) WHERE rn = 1""").fetchone()[0]
    assert abs(q2 - base["最初の出来事が変わった人%"]) < 1e-9

    # ---- A. 時計のずれの大きさ × 間隔の長さ（各30回） ----
    rows = []
    for sd in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]:
        for gm in [0.5, 2.0, 10.0]:
            ms = [measure(make(1000 + rep, skew_sd=sd, gap_median=gm)[0]) for rep in range(30 if gm == 2.0 else 10)]
            m = pd.DataFrame(ms).mean().to_dict(); m.update({"時計のずれの標準偏差（秒）": sd, "ページを読む間隔の中央値（秒）": gm * 4})
            rows.append(m)
    sw = pd.DataFrame(rows); sw.to_csv(RES / "by_skew_and_gap.csv", index=False)
    mid = sw[sw["ページを読む間隔の中央値（秒）"] == 8.0]
    res["by_skew"] = {str(r["時計のずれの標準偏差（秒）"]): {"順が逆%": round(r["となりの出来事の順が逆%"], 1), "最初%": round(r["最初の出来事が変わった人%"], 1),
                                                    "購入の直前%": round(r["購入の直前の出来事が変わった人%"], 1), "並びが変わった人%": round(r["並びが1か所でも変わった人%"], 1),
                                                    "所要時間1秒以上%": round(r["所要時間が1秒以上ずれた人%"], 1)} for _, r in mid.iterrows()}

    # ---- B. 並べ方3つ（ずれ1秒・30回） ----
    rows = []
    for rep in range(30):
        d, _ = make(2000 + rep, skew_sd=1.0)
        a = measure(d)                                                    # ①記録された時刻で並べる
        # ②通し番号で並べる：順番は必ず正しい。ただし所要時間は時刻から出すので、ずれは残る
        b = {"となりの出来事の順が逆%": 0.0, "最初の出来事が変わった人%": 0.0, "購入の直前の出来事が変わった人%": 0.0, "並びが1か所でも変わった人%": 0.0,
             "所要時間が1秒以上ずれた人%": a["所要時間が1秒以上ずれた人%"], "間隔がマイナスになった件数": a["間隔がマイナスになった件数"]}
        s, _ = make(2000 + rep, skew_sd=1.0, sticky=True)                # ③同じ人は1台で記録する
        c = measure(s)
        # 人をまたいだ順番（全体で時刻順に並べたとき、となりの2件の順が本当と逆の割合）
        def cross(x):
            o = x.sort_values("rec_t"); t = o.true_t.to_numpy()
            return float((np.diff(t) < 0).mean() * 100)
        rows.append({"rep": rep, **{f"①{k}": v for k, v in a.items()}, **{f"②{k}": v for k, v in b.items()}, **{f"③{k}": v for k, v in c.items()},
                     "①全体の順が逆%": cross(d), "③全体の順が逆%": cross(s)})
    mt = pd.DataFrame(rows).mean(numeric_only=True)
    keys = ["となりの出来事の順が逆%", "最初の出来事が変わった人%", "購入の直前の出来事が変わった人%", "並びが1か所でも変わった人%", "所要時間が1秒以上ずれた人%"]
    meth = pd.DataFrame({"指標": keys, "①記録された時刻で並べる": [mt[f"①{k}"] for k in keys],
                         "②受け取った順の通し番号で並べる": [mt[f"②{k}"] for k in keys], "③同じ人は1台で記録する": [mt[f"③{k}"] for k in keys]})
    meth.loc[len(meth)] = ["人をまたいだ全体の順が逆%", mt["①全体の順が逆%"], 0.0, mt["③全体の順が逆%"]]
    meth.to_csv(RES / "by_method.csv", index=False)
    res["by_method"] = {r["指標"]: [round(r.iloc[1], 1), round(r.iloc[2], 1), round(r.iloc[3], 1)] for _, r in meth.iterrows()}

    # ---- C. サーバーの台数（ずれ1秒） ----
    rows = []
    for ns in [2, 3, 5, 10]:
        ms = [measure(make(3000 + rep, skew_sd=1.0, n_srv=ns)[0]) for rep in range(20)]
        rows.append({"サーバーの台数": ns, **pd.DataFrame(ms).mean().to_dict()})
    bs = pd.DataFrame(rows); bs.to_csv(RES / "by_servers.csv", index=False)
    res["by_servers"] = {str(int(r["サーバーの台数"])): round(r["となりの出来事の順が逆%"], 1) for _, r in bs.iterrows()}

    # ---- D. 集計への影響：「入口のページ別の人数」のような集計の代わりに、最初の出来事の種類の内訳 ----
    r = df.sort_values(["user_id", "rec_t", "seq"]).groupby("user_id").head(1).kind.value_counts()
    res["first_event_kind"] = {k: int(v) for k, v in r.items()}
    json.dump(res, open(RES / "a465_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

    # ---- 図 ----
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    for gm, col in [(2.0, LIGHT), (8.0, BLUE), (40.0, "#1b4f91")]:
        d = sw[sw["ページを読む間隔の中央値（秒）"] == gm]
        ax.plot(d["時計のずれの標準偏差（秒）"], d["となりの出来事の順が逆%"], "o-", color=col, label=f"ページを読む間隔の中央値 {gm:g}秒")
    ax.set_xlabel("サーバーの時計のずれ（標準偏差、秒）"); ax.set_ylabel("となりの出来事の順が逆になった割合（%）")
    ax.set_title("時計のずれと、順番の入れ替わり"); ax.legend(frameon=False, fontsize=8.5)
    ax = axes[1]
    ax.plot(mid["時計のずれの標準偏差（秒）"], mid["並びが1か所でも変わった人%"], "o-", color=ORANGE, label="並びが1か所でも変わった人")
    ax.plot(mid["時計のずれの標準偏差（秒）"], mid["購入の直前の出来事が変わった人%"], "s-", color=BLUE, label="購入の直前の出来事が変わった人")
    ax.plot(mid["時計のずれの標準偏差（秒）"], mid["最初の出来事が変わった人%"], "^-", color=GREEN, label="最初の出来事が変わった人")
    ax.set_xlabel("サーバーの時計のずれ（標準偏差、秒）"); ax.set_ylabel("人の割合（%）"); ax.set_title("人ごとの見え方がどれだけ変わるか")
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a465_by_skew.png", SRC)

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    x = np.arange(len(meth)); w = 0.27
    for i, (col, c) in enumerate(zip(meth.columns[1:], [ORANGE, GREEN, BLUE])):
        ax.bar(x + (i - 1) * w, meth[col], w, color=c, label=col)
        for xx, v in zip(x, meth[col]):
            ax.text(xx + (i - 1) * w, v + 1, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(["となりの出来事の\n順が逆", "最初の出来事が\n変わった人", "購入の直前が\n変わった人", "並びが1か所でも\n変わった人", "所要時間が1秒\n以上ずれた人", "人をまたいだ\n全体の順が逆"], fontsize=8.5)
    ax.set_ylabel("割合（%）"); ax.set_title("並べ方・記録のしかたごとの比べ（時計のずれ1秒）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_ylim(0, meth.iloc[:, 1:].to_numpy().max() * 1.2)
    save(fig, "a465_by_method.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    ax.plot(mid["時計のずれの標準偏差（秒）"], mid["間隔がマイナスになった件数"], "o-", color=ORANGE)
    for a, b in zip(mid["時計のずれの標準偏差（秒）"], mid["間隔がマイナスになった件数"]):
        ax.annotate(f"{b:,.0f}", (a, b), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)
    ax.set_xlabel("サーバーの時計のずれ（標準偏差、秒）"); ax.set_ylabel(f"件数（出来事 約{len(df)//1000}千件のうち）")
    ax.set_title("前の出来事との間隔がマイナスになった件数")
    ax = axes[1]
    ax.plot(bs["サーバーの台数"], bs["となりの出来事の順が逆%"], "o-", color=BLUE)
    for a, b in zip(bs["サーバーの台数"], bs["となりの出来事の順が逆%"]):
        ax.annotate(f"{b:.1f}%", (a, b), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)
    ax.set_xlabel("サーバーの台数"); ax.set_ylabel("となりの出来事の順が逆になった割合（%）"); ax.set_title("台数を変えたとき（ずれ1秒）")
    ax.set_ylim(0, bs["となりの出来事の順が逆%"].max() * 1.3)
    save(fig, "a465_negative_and_servers.png", SRC)


if __name__ == "__main__":
    main()
