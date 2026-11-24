"""1265 期の終わりに受注が集まって見えるのは、決まる日が寄るからか、記録を付ける日が寄るからか？（架空のデータ）

作成者が置いた架空の会社の法人向けの商談。1期＝91日（13週）。9期つづけて作り、前後の期にまたがる分を入れるため、
2〜8期目の7期で数える。各期の受注は平均300件（数え上げの乱数）。
  決まる日：受注のうち割合 c は期の最後の14日に、残りは期の91日に均等に決まる（c が「決まる日が本当に寄る」分）
  記録を付ける日：決まってから平均 L 日おくれて付ける（おくれの日数は0日から始まる、だんだん減る形の乱数）
  期をまたぐとき：記録の日が期の最後の日を過ぎるなら、割合 q で期の最後の3日のうちに付け直す（ただし決まった日より前にはしない）。
                  残りは次の期に付く
  記録の「決まった日」の欄：割合 w は本当の決まった日を書き、残りは記録を付けた日をそのまま書く
数えるもの：期の受注のうち、期の最後の14日に入る割合を
  ⓪本当の決まった日　①記録を付けた日　②記録の「決まった日」の欄
で数える。均等なら 14÷91＝15.38%。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1265
SRC = "架空の法人向けの商談の受注（作成者が置いた決まる日・記録のおくれ・付け直しの割合からの乱数、seed 1265）"
D, NQ, END = 91, 9, 14
BASE = dict(c=0.15, L=7, q=0.8, w=0.5, n=300)
UNIF = END / D


def one_set(rng, c=0.15, L=7, q=0.8, w=0.5, n=300):
    cnt = rng.poisson(n, NQ)
    qi = np.repeat(np.arange(NQ), cnt)
    late = rng.random(len(qi)) < c
    day_in = np.where(late, rng.integers(D - END, D, len(qi)), rng.integers(0, D, len(qi)))
    dec = qi * D + day_in
    lag = rng.geometric(1 / (L + 1), len(qi)) - 1 if L > 0 else np.zeros(len(qi), int)
    rec = dec + lag
    qend = (qi + 1) * D - 1
    over = rec > qend
    fix = over & (rng.random(len(qi)) < q)
    rec = np.where(fix, np.maximum(dec, qend - rng.integers(0, 3, len(qi))), rec)
    field = np.where(rng.random(len(qi)) < w, dec, rec)
    return dict(qi=qi, dec=dec, rec=rec, field=field, fixed=fix, spill=over & ~fix)


def shares(o, quarters=range(1, NQ - 1)):
    res = {}
    for name in ["dec", "rec", "field"]:
        d = o[name]
        qq = d // D
        m = np.isin(qq, list(quarters))
        dd = d[m] % D
        res[name] = float(np.mean(dd >= D - END))
        res[name + "_last3"] = float(np.mean(dd >= D - 3))
        res[name + "_first14"] = float(np.mean(dd < 14))
    res["spill_share"] = float(np.mean(o["spill"][np.isin(o["qi"], list(quarters))]))
    res["fixed_share"] = float(np.mean(o["fixed"][np.isin(o["qi"], list(quarters))]))
    return res


def weekly(o, name, quarters=range(1, NQ - 1)):
    d = o[name]
    m = np.isin(d // D, list(quarters))
    wk = np.minimum((d[m] % D) // 7, 12)
    return np.bincount(wk, minlength=13) / m.sum()


def main():
    t0 = time.time()
    o = one_set(np.random.default_rng([SEED, 0]), **BASE)
    df = pd.DataFrame({"quarter_of_decision": o["qi"] + 1, "decided_day": o["dec"], "recorded_day": o["rec"],
                       "field_decided_day": o["field"], "moved_to_quarter_end": o["fixed"].astype(int),
                       "recorded_next_quarter": o["spill"].astype(int)})
    df.to_csv(DATA / "wins_one_set.csv", index=False)
    one = shares(o)

    # 基本の置き方で500回
    rows = []
    for r in range(500):
        s = shares(one_set(np.random.default_rng([SEED, 1, r]), **BASE))
        s["rep"] = r
        rows.append(s)
    reps = pd.DataFrame(rows)
    reps.round(5).to_csv(RES / "reps_base.csv", index=False)

    # 2つの対照の場面：A 決まる日は寄らず記録がおくれる／B 決まる日が寄り記録はその日に付ける
    scen = {"A_record_only": dict(c=0.0, L=14, q=0.8, w=0.5, n=300),
            "B_decision_only": dict(c=0.15, L=0, q=0.8, w=0.5, n=300),
            "base": BASE}
    sc_rows, wk_rows = [], []
    for k, (nm, pr) in enumerate(scen.items()):
        acc, wk = [], {x: np.zeros(13) for x in ["dec", "rec"]}
        for r in range(200):
            o = one_set(np.random.default_rng([SEED, 2, k, r]), **pr)
            acc.append(shares(o))
            for x in wk:
                wk[x] += weekly(o, x) / 200
        a = pd.DataFrame(acc).mean()
        sc_rows.append({"scenario": nm, **pr, **a.to_dict()})
        for x in wk:
            for i, v in enumerate(wk[x]):
                wk_rows.append({"scenario": nm, "date": x, "week": i + 1, "share": v})
    sc = pd.DataFrame(sc_rows)
    sc.round(4).to_csv(RES / "scenarios.csv", index=False)
    wkdf = pd.DataFrame(wk_rows)
    wkdf.round(4).to_csv(RES / "weekly.csv", index=False)

    # 27通り
    grid = []
    for c in [0.0, 0.15, 0.3]:
        for L in [0, 7, 14]:
            for q in [0.5, 0.8, 1.0]:
                acc = [shares(one_set(np.random.default_rng([SEED, 3, int(c * 100), L, int(q * 10), r]), c=c, L=L, q=q, w=0.5, n=300)) for r in range(40)]
                a = pd.DataFrame(acc).mean()
                grid.append({"c": c, "L": L, "q": q, **a.to_dict()})
    gr = pd.DataFrame(grid)
    gr["decision_part"] = gr["dec"] - UNIF
    gr["record_part"] = gr["rec"] - gr["dec"]
    gr.round(4).to_csv(RES / "grid.csv", index=False)

    q_ = lambda x, p: round(float(np.quantile(x, p)), 4)
    m = lambda x: round(float(np.mean(x)), 4)
    A = sc.set_index("scenario").loc["A_record_only"]
    B = sc.set_index("scenario").loc["B_decision_only"]
    head = {"uniform_share": round(UNIF, 4), "uniform_last3": round(3 / D, 4),
            "share_decided": m(reps.dec), "share_recorded": m(reps.rec), "share_field": m(reps.field),
            "share_recorded_p10_p90": [q_(reps.rec, .1), q_(reps.rec, .9)],
            "excess_recorded": round(m(reps.rec) - UNIF, 4), "decision_part": round(m(reps.dec) - UNIF, 4),
            "record_part": round(m(reps.rec) - m(reps.dec), 4),
            "record_part_share_of_excess": round((m(reps.rec) - m(reps.dec)) / (m(reps.rec) - UNIF), 4),
            "last3_decided": m(reps.dec_last3), "last3_recorded": m(reps.rec_last3),
            "first14_decided": m(reps.dec_first14), "first14_recorded": m(reps.rec_first14),
            "last3_field": m(reps.field_last3), "first14_field": m(reps.field_first14),
            "moved_to_quarter_end_share": m(reps.fixed_share), "recorded_next_quarter_share": m(reps.spill_share)}
    scen_out = {nm: {k: round(float(v), 4) for k, v in sc.set_index("scenario").loc[nm].items() if k in
                     ["dec", "rec", "field", "dec_last3", "rec_last3", "dec_first14", "rec_first14", "fixed_share", "spill_share"]}
                for nm in scen}
    rng_ = lambda s: [round(float(s.min()), 4), round(float(s.max()), 4)]
    robust = {"settings": int(len(gr)), "share_recorded_range": rng_(gr.rec), "share_decided_range": rng_(gr.dec),
              "record_part_range": rng_(gr.record_part),
              "record_part_range_L0": rng_(gr[gr.L == 0].record_part),
              "record_part_range_L14": rng_(gr[gr.L == 14].record_part),
              "settings_record_part_larger": int(np.sum(gr.record_part > gr.decision_part)),
              "rec_last3_range_by_L": {str(L): rng_(gr[gr.L == L].rec_last3) for L in [0, 7, 14]},
              "dec_last3_range": rng_(gr.dec_last3),
              "rec_first14_range_by_L": {str(L): rng_(gr[gr.L == L].rec_first14) for L in [0, 7, 14]}}
    out = {"headline": head, "scenarios": scen_out, "one_set": {k: round(v, 4) for k, v in one.items()}, "robust": robust,
           "settings": {"days_per_quarter": D, "quarters_made": NQ, "quarters_counted": "2〜8期目の7期", "end_window_days": END,
                        "base": BASE, "scenarios": scen, "reps_base": 500, "reps_scenarios": 200, "reps_grid": 40}}
    json.dump(out, open(RES / "a1265_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1 分け方
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    labs = ["⓪本当の決まった日", "①記録を付けた日", "②記録の「決まった日」欄"]
    v = [head["share_decided"] * 100, head["share_recorded"] * 100, head["share_field"] * 100]
    ax.bar(labs, v, color=[GREEN, ORANGE, BLUE], width=0.55)
    for i, vv in enumerate(v):
        ax.text(i, vv + 0.8, f"{vv:.2f}%", ha="center", fontsize=10)
    ax.axhline(UNIF * 100, color=INK, lw=0.8, ls="--")
    ax.text(1.5, UNIF * 100 + 0.8, "均等なら15.38%", ha="center", fontsize=8.5)
    ax.set_ylim(0, max(v) + 8)
    ax.set_ylabel("期の最後の14日に入る受注の割合（%）")
    ax.set_title("どの日付で数えるか（基本の置き方、500回の平均）")
    save(fig, "a1265_three_dates.png", SRC)

    # 図2 週ごとの形 A と B
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    for ax, nm, ttl in [(axes[0], "A_record_only", "A：決まる日は寄らない・記録が平均14日おくれる"),
                        (axes[1], "B_decision_only", "B：決まる日が寄る・記録はその日に付ける（2本の線は重なる）")]:
        for x, c, lab in [("dec", GREEN, "本当の決まった日"), ("rec", ORANGE, "記録を付けた日")]:
            d = wkdf[(wkdf.scenario == nm) & (wkdf.date == x)]
            ax.plot(d.week, d.share * 100, color=c, marker="o", ms=4, label=lab)
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("期の中の週（13週目は最後の7日）")
        ax.set_xticks(range(1, 14))
    axes[0].set_ylabel("期の受注のうちその週の割合（%）")
    axes[0].set_ylim(0, wkdf.share.max() * 100 + 3)
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1265_weekly_A_B.png", SRC)

    # 図3 27通りの分け方
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    g = gr.reset_index(drop=True)
    x = np.arange(len(g)) + np.repeat([0, 1, 2], 9)
    ax.bar(x - 0.2, g.decision_part * 100, 0.4, color=GREEN, label="決まる日が寄る分（⓪−15.38%）")
    ax.bar(x + 0.2, g.record_part * 100, 0.4, color=ORANGE, label="記録の付け方の分（①−⓪）")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x, [f"{int(r.L)}日\n{r.q:.1f}" for r in g.itertuples()], fontsize=6.5)
    top_ = max(g.decision_part.max(), g.record_part.max()) * 100
    for i, c in enumerate([0.0, 0.15, 0.3]):
        ax.text(i * 10 + 4, top_ + 2, f"期の終わりに決まる割合 {round(c*100)}%", ha="center", fontsize=9)
    ax.set_ylim(min(0, g.record_part.min() * 100) - 1, top_ + 9)
    ax.set_ylabel("均等（15.38%）からの上ずれ（ポイント）")
    ax.set_xlabel("下の段：記録のおくれの平均（日）／期の最後に付け直す割合")
    ax.set_title("①記録を付けた日で数えた上ずれの内訳（27通り、各40回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    save(fig, "a1265_grid.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
