"""514 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか（実務の型）

架空の倉庫（200品目×180日）で、出荷（出庫）と入荷（入庫）の「起きた時刻」と「システムに記録された時刻」を作る。
本当の在庫はマイナスにならない（物がなければ出荷できない）。入庫の記録が検品などで遅れると、
記録だけで積み上げた在庫は一時的にマイナスになる。締め（日次の集計を走らせる時刻）を遅らせると、どこまで戻るかも見る。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 514
SRC = "架空の倉庫の入出庫記録（作成者が乱数で作成、seed 514）"
N_ITEM, DAYS = 200, 180
LAGS = {"当日24時": 0, "翌2時": 2, "翌9時": 9, "翌日24時": 24, "3日後": 72}
DELAYS = [0, 1, 3, 6, 12, 24, 48]           # 入庫記録の遅れ（中央値、時間）


def simulate(seed=SEED):
    """起きた時刻（時間、0＝1日目0時）と数量の並びを品目ごとに作る"""
    rng = np.random.default_rng(seed)
    items = []
    for i in range(N_ITEM):
        lam = float(np.exp(rng.uniform(np.log(4), np.log(60))))   # 1日の出荷件数の平均
        s, Q, lead = int(lam * 3), int(lam * 7), 2
        on_hand = s + Q; init = on_hand; pending = []              # (到着時刻, 数量)
        ev_t, ev_q, kind = [], [], []
        for d in range(DAYS):
            for a in sorted(pending):                               # 朝の入荷（7〜8時半、出荷が始まる前）
                if a[0] < (d + 1) * 24 and a[0] >= d * 24:
                    on_hand += a[1]; ev_t.append(a[0]); ev_q.append(a[1]); kind.append("入庫")
            pending = [a for a in pending if a[0] >= (d + 1) * 24]
            ts = np.sort(d * 24 + rng.uniform(9, 18, rng.poisson(lam)))
            for t in ts:                                           # 出荷は 9〜18時、物がなければ出せない
                if on_hand >= 1:
                    on_hand -= 1; ev_t.append(t); ev_q.append(-1); kind.append("出庫")
                if on_hand + sum(a[1] for a in pending) <= s:      # 発注点を下回ったら発注
                    pending.append(((d + lead) * 24 + rng.uniform(7, 8.5), Q))
        items.append({"item": i, "init": init, "t": np.array(ev_t), "q": np.array(ev_q), "kind": np.array(kind)})
    return items


def add_record_time(items, recv_median, seed=SEED + 1):
    rng = np.random.default_rng(seed)
    for it in items:
        n = len(it["t"]); isr = it["kind"] == "入庫"
        dl = np.where(isr, recv_median * rng.lognormal(0, 1.0, n) if recv_median > 0 else 0.0,
                      rng.exponential(0.2, n))                     # 出庫の記録はほぼすぐ（平均12分）
        it["r"] = it["t"] + dl
    return items


def daily_stock(it, lag):
    """日dの締め（d日目24時＋lag 時間に集計）で、d日目までに起きて集計時刻までに記録されたものを積む"""
    first = np.ceil(it["t"] / 24).astype(int)
    if lag is not None:
        first = np.maximum(first, np.ceil((it["r"] - lag) / 24).astype(int))
    first = np.maximum(first, 1)
    add = np.bincount(np.minimum(first, DAYS + 1), weights=it["q"], minlength=DAYS + 2)[1:DAYS + 1]
    return it["init"] + np.cumsum(add)


def intraday_min_by_record(it):
    """記録の順に在庫を動かしたとき、その日のうちに一度でもマイナスになったか（画面で見る在庫）"""
    o = np.argsort(it["r"]); r = it["r"][o]; st = it["init"] + np.cumsum(it["q"][o])
    day = np.minimum(np.floor(r / 24).astype(int), DAYS + 1); mn = np.full(DAYS + 2, np.inf)
    np.minimum.at(mn, day, st)
    return mn[:DAYS]


def measure(items):
    rows = []
    true = np.array([daily_stock(it, None) for it in items])
    for name, lag in LAGS.items():
        rec = np.array([daily_stock(it, lag) for it in items])
        rows.append({"締め": name, "マイナスの日の割合": float((rec < 0).mean()),
                     "マイナスになった品目": int((rec < 0).any(axis=1).sum()),
                     "欠品と誤判定（記録≦0・本当>0）の割合": float(((rec <= 0) & (true > 0)).mean()),
                     "月末在庫の合計のずれ": float(sum(rec[:, d].sum() - true[:, d].sum() for d in range(29, DAYS, 30)) /
                                          sum(true[:, d].sum() for d in range(29, DAYS, 30))),
                     "月末在庫が1個でも違う品目の割合": float(np.mean([(rec[:, d] != true[:, d]).mean() for d in range(29, DAYS, 30)]))})
    intr = np.array([intraday_min_by_record(it) for it in items])
    return pd.DataFrame(rows), true, float((intr < 0).mean()), int((intr < 0).any(axis=1).sum())


def main():
    base = simulate()
    out = {"seed": SEED, "品目": N_ITEM, "日数": DAYS}
    out["記録の件数"] = int(sum(len(it["t"]) for it in base))
    out["入庫の件数"] = int(sum((it["kind"] == "入庫").sum() for it in base))
    tr = np.array([daily_stock(it, None) for it in base])
    out["本当の在庫がマイナスの日"] = int((tr < 0).sum()); out["本当の在庫が0の日の割合"] = float((tr == 0).mean())
    sweep = []
    for m in DELAYS:
        items = add_record_time(base, m)
        tab, _, intr_share, intr_items = measure(items)
        tab.insert(0, "入庫記録の遅れ_中央値_時間", m); tab["日中に一度でもマイナス（画面）の日の割合"] = intr_share
        tab["日中にマイナスになった品目"] = intr_items
        sweep.append(tab)
    sw = pd.concat(sweep, ignore_index=True); sw.to_csv(RES / "sweep.csv", index=False)
    b = sw[sw["入庫記録の遅れ_中央値_時間"] == 6]
    out["遅れ6時間の表"] = b.to_dict("records")
    # DuckDB で1品目分の日次在庫（記録時刻・締め当日24時）を計算して一致を確認
    items6 = add_record_time(base, 6)
    rec = pd.concat([pd.DataFrame({"item": it["item"], "event_h": it["t"], "record_h": it["r"], "qty": it["q"]}) for it in items6])
    init = pd.DataFrame({"item": [it["item"] for it in items6], "init": [it["init"] for it in items6]})
    con = duckdb.connect(); con.register("rec", rec); con.register("init_stock", init)
    sql = open(SQL / "02_stock_duckdb.sql").read()
    for lag in [0, 9]:
        q = con.execute(sql.replace("{LAG}", str(lag)).replace("{DAYS}", str(DAYS))).df()
        py = np.array([daily_stock(it, lag) for it in items6])
        dq = q.pivot(index="item", columns="d", values="stock").sort_index().to_numpy()
        assert np.array_equal(dq, py), "DuckDB と pandas の日次在庫が一致しない"
        out[f"DuckDB_一致_lag{lag}"] = True
    json.dump(out, open(RES / "a514_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：入庫の記録の遅れ × マイナスの日の割合（締め別）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for name, col, mk in [("当日24時", ORANGE, "o"), ("翌9時", BLUE, "s"), ("翌日24時", GREEN, "^"), ("3日後", GRAY, "d")]:
        t = sw[sw["締め"] == name]
        ax.plot(range(len(DELAYS)), t["マイナスの日の割合"] * 100, marker=mk, color=col, label=f"締め：{name}")
    t = sw[sw["締め"] == "当日24時"]
    ax.plot(range(len(DELAYS)), t["日中に一度でもマイナス（画面）の日の割合"] * 100, ls="--", color=INK, lw=1, label="日中に一度でも（画面の在庫）")
    for xi, v in enumerate(t["マイナスの日の割合"] * 100):
        if v >= 1: ax.text(xi - 0.12, v + 0.6, f"{v:.1f}", ha="center", fontsize=8, color=ORANGE)
    ax.set_xticks(range(len(DELAYS)), [f"{m}時間" for m in DELAYS]); ax.set_xlabel("入庫の記録の遅れ（中央値）")
    ax.set_ylabel("在庫がマイナスの品目・日の割合（%）")
    ax.set_title("入庫の記録が遅れるほどマイナスの日が増え、締めを遅らせると減る", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a514_negative_by_delay.png", SRC + "。200品目×180日。出庫の記録の遅れは平均12分")
    # 図2：1品目の例（本当の在庫と記録の在庫、時間単位）
    it = items6[int(np.argmax([(intraday_min_by_record(i) < 0).sum() for i in items6]))]
    o = np.argsort(it["t"]); o2 = np.argsort(it["r"])
    lo, hi = 24 * 60, 24 * 74
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    tt = it["t"][o]; ts = np.cumsum(it["q"][o]) + it["init"]
    rr = it["r"][o2]; rs = np.cumsum(it["q"][o2]) + it["init"]
    m1 = (tt >= lo) & (tt <= hi); m2 = (rr >= lo) & (rr <= hi)
    s0 = ts[tt < lo][-1] if (tt < lo).any() else it["init"]; r0 = rs[rr < lo][-1] if (rr < lo).any() else it["init"]
    ax.step(np.r_[lo, tt[m1]] / 24, np.r_[s0, ts[m1]], where="post", color=BLUE, label="本当の在庫（起きた時刻で）")
    ax.step(np.r_[lo, rr[m2]] / 24, np.r_[r0, rs[m2]], where="post", color=ORANGE, label="記録の在庫（記録された時刻で）")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("日"); ax.set_ylabel("在庫（個）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"入荷の記録が届くまで、出荷だけが先に引かれてマイナスになる（品目{it['item']}の例）", fontsize=11.5)
    save(fig, "a514_one_item.png", SRC + "。入庫記録の遅れ中央値6時間の場合の14日分")
    # 図3：締め × 指標（遅れ6時間）
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.0))
    names = list(LAGS)
    v1 = b["欠品と誤判定（記録≦0・本当>0）の割合"].to_numpy() * 100
    axs[0].bar(range(5), v1, color=[ORANGE, ORANGE, BLUE, GREEN, GRAY])
    for a, v in enumerate(v1): axs[0].text(a, v + 0.02, f"{v:.2f}", ha="center", fontsize=8.5)
    axs[0].set_xticks(range(5), names, fontsize=8.5); axs[0].set_title("欠品と誤って見える品目・日（%）", fontsize=11)
    v2 = b["月末在庫の合計のずれ"].to_numpy() * 100
    axs[1].bar(range(5), v2, color=[ORANGE, ORANGE, BLUE, GREEN, GRAY])
    for a, v in enumerate(v2): axs[1].text(a, v - 0.08, f"{v:+.1f}", ha="center", va="top", fontsize=8.5)
    axs[1].axhline(0, color=INK, lw=0.8); axs[1].set_ylim(v2.min() * 1.15, 0.2)
    axs[1].set_xticks(range(5), names, fontsize=8.5); axs[1].set_title("月末在庫の合計のずれ（%）", fontsize=11)
    fig.suptitle("締めを遅らせるほど、欠品に見える日と月末在庫のずれは小さくなる（入庫記録の遅れ6時間）", fontsize=12, y=1.03)
    save(fig, "a514_by_cutoff.png", SRC + "。月末在庫は6か月の各月末の合計")
    print(sw.to_string()); print({k: v for k, v in out.items() if k != "遅れ6時間の表"})


if __name__ == "__main__":
    main()
