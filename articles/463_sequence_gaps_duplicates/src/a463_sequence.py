"""463 連番のはずの番号の抜けと重複は、どの確かめ方で何件見つかるのか（架空の伝票番号、seed 463）"""
import json
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, BLUE, ORANGE, GRAY, LIGHT, GREEN, save

SRC = "架空の伝票番号（作成者が乱数で作成、seed 463）"
PREFIX = ["A", "B", "C"]; YEARS = [2024, 2025]


def make(seed, n_per=8000, n_gap=30, n_dup=25, n_void=40, tail=True):
    """伝票の表と、取消で欠番にした番号の表を作る。番号は 接頭辞-年-6桁 で、年が変わると1から振り直す"""
    rng = np.random.default_rng(seed)
    rows, truth_gap, truth_dup, void, issued = [], [], [], [], []
    groups = [(p, y) for p in PREFIX for y in YEARS]
    # 抜け・重複・欠番を、6つの組（接頭辞×年）にばらまく
    g_gap = rng.multinomial(n_gap, np.ones(6) / 6); g_dup = rng.multinomial(n_dup, np.ones(6) / 6)
    g_void = rng.multinomial(n_void, np.ones(6) / 6)
    for gi, (p, y) in enumerate(groups):
        n = int(n_per * rng.uniform(0.7, 1.3))
        serial = np.arange(1, n + 1); issued.append((p, y, n))
        inner = serial[1:-4]                                           # 最初と、最後の4件は、途中の抜け・欠番には使わない
        pick = rng.choice(inner, g_gap[gi] + g_void[gi], replace=False)
        gap = set(pick[:g_gap[gi]].tolist()); vd = set(pick[g_gap[gi]:].tolist())
        keep = np.array([s for s in serial if s not in gap and s not in vd])
        dup = rng.choice(keep, g_dup[gi], replace=False)
        allv = np.concatenate([keep, dup])
        rows += [(f"{p}-{y}-{s:06d}", p, y, int(s)) for s in allv]
        truth_gap += [(p, y, int(s)) for s in gap]; truth_dup += [(p, y, int(s)) for s in dup]
        void += [(f"{p}-{y}-{s:06d}", p, y, int(s)) for s in vd]
    df = pd.DataFrame(rows, columns=["slip_no", "prefix", "yr", "serial"]).sample(frac=1, random_state=seed).reset_index(drop=True)
    tail_missing = []
    if tail:                                                           # いちばん後ろの番号が抜ける（C-2025 の最後の3件）
        m = df[(df.prefix == "C") & (df.yr == 2025)].serial.max()
        tail_missing = [("C", 2025, int(m - i)) for i in range(3)]
        df = df[~((df.prefix == "C") & (df.yr == 2025) & (df.serial > m - 3))].reset_index(drop=True)
    return (df, pd.DataFrame(void, columns=["slip_no", "prefix", "yr", "serial"]),
            pd.DataFrame(truth_gap, columns=["prefix", "yr", "serial"]),
            pd.DataFrame(truth_dup, columns=["prefix", "yr", "serial"]),
            pd.DataFrame(tail_missing, columns=["prefix", "yr", "serial"]),
            pd.DataFrame(issued, columns=["prefix", "yr", "last_no"]))


def run_checks(con, df, void, issued):
    con.register("slips", df); con.register("voids", void); con.register("issued", issued)
    out = {}
    # ① 全体で 最大−最小＋1 と件数を比べる（番号の数字の部分だけを見る）
    a = con.execute("SELECT MAX(serial)-MIN(serial)+1 - COUNT(*) FROM slips").fetchone()[0]
    out["c1_diff"] = int(a)
    # ② 接頭辞×年ごとに 最大−最小＋1 と件数を比べる
    out["c2"] = con.execute("""SELECT prefix, yr, MAX(serial)-MIN(serial)+1 AS expected, COUNT(*) AS n,
                               MAX(serial)-MIN(serial)+1-COUNT(*) AS diff FROM slips GROUP BY prefix, yr ORDER BY 1,2""").df()
    # ③ 前の番号との差（LAG）
    lag = con.execute("""SELECT prefix, yr, serial, serial - LAG(serial) OVER (PARTITION BY prefix, yr ORDER BY serial) AS d
                         FROM slips QUALIFY d <> 1""").df()
    out["c3_gap_missing"] = int((lag[lag.d > 1].d - 1).sum()); out["c3_gap_places"] = int((lag.d > 1).sum())
    out["c3_dup"] = int((lag.d == 0).sum())
    out["c3_gap_rows"] = lag[lag.d > 1]
    # ④ 番号の一覧（1〜最大）と突き合わせる＋同じ番号の数
    miss = con.execute("""WITH mx AS (SELECT prefix, yr, MAX(serial) m FROM slips GROUP BY prefix, yr),
                               allno AS (SELECT prefix, yr, UNNEST(range(1, m+1)) AS serial FROM mx)
                          SELECT a.prefix, a.yr, a.serial FROM allno a
                          LEFT JOIN (SELECT DISTINCT prefix, yr, serial FROM slips) s USING (prefix, yr, serial)
                          WHERE s.serial IS NULL""").df()
    dup = con.execute("SELECT prefix, yr, serial, COUNT(*)-1 AS extra FROM slips GROUP BY prefix, yr, serial HAVING COUNT(*) > 1").df()
    out["c4_missing"] = miss; out["c4_dup"] = dup
    # ⑤ ④から、取消で欠番にした番号を除く
    out["c5_missing"] = miss.merge(void[["prefix", "yr", "serial"]], on=["prefix", "yr", "serial"], how="left", indicator=True) \
                            .query("_merge == 'left_only'").drop(columns="_merge")
    # ⑥ 発番の控え（組ごとの最後の番号）まで一覧を作って突き合わせ、欠番を除く
    m6 = con.execute("""WITH allno AS (SELECT prefix, yr, UNNEST(range(1, last_no+1)) AS serial FROM issued)
                         SELECT a.prefix, a.yr, a.serial FROM allno a
                         LEFT JOIN (SELECT DISTINCT prefix, yr, serial FROM slips) s USING (prefix, yr, serial)
                         LEFT JOIN voids v USING (prefix, yr, serial)
                         WHERE s.serial IS NULL AND v.serial IS NULL""").df()
    out["c6_missing"] = m6
    return out


def main():
    res = {}
    con = duckdb.connect()
    df, void, tg, td, tail, issued = make(463)
    DATA.mkdir(exist_ok=True)
    df.to_csv(DATA / "slips.csv", index=False); void.to_csv(DATA / "void_numbers.csv", index=False)
    tg.to_csv(DATA / "truth_missing.csv", index=False); td.to_csv(DATA / "truth_duplicates.csv", index=False)
    issued.to_csv(DATA / "issued_last_numbers.csv", index=False)
    o = run_checks(con, df, void, issued)
    n_gap, n_dup, n_void, n_tail = len(tg), len(td), len(void), len(tail)
    res["setup"] = {"伝票の行": len(df), "組（接頭辞×年）": 6, "入れた抜け": n_gap, "入れた重複": n_dup,
                    "取消の欠番": n_void, "最後の番号の抜け": n_tail}
    key = lambda d: set(map(tuple, d[["prefix", "yr", "serial"]].to_numpy().tolist()))
    T_gap, T_void, T_dup, T_tail = key(tg), key(void), key(td), key(tail)

    c2 = o["c2"]; c2.to_csv(RES / "check2_by_group.csv", index=False)
    # ②の「差」：抜け＋欠番−重複 が出るだけ
    true_by = (pd.concat([tg.assign(k="gap"), void[["prefix", "yr", "serial"]].assign(k="void"), td.assign(k="dup"), tail.assign(k="tail")])
               .groupby(["prefix", "yr", "k"]).size().unstack(fill_value=0).reset_index())
    for col in ["gap", "void", "dup", "tail"]:
        if col not in true_by: true_by[col] = 0
    c2m = c2.merge(true_by, on=["prefix", "yr"], how="left").fillna(0)
    assert ((c2m["diff"] == c2m.gap + c2m.void - c2m.dup).all())
    c2m.to_csv(RES / "check2_vs_truth.csv", index=False)

    found4 = key(o["c4_missing"]); found5 = key(o["c5_missing"]); found6 = key(o["c6_missing"]); dup4 = key(o["c4_dup"])
    # ③ LAG：抜けた番号を1つずつ言えるか（差の行から範囲を戻す）
    lagrows = o["c3_gap_rows"]
    lag_missing = set()
    for _, r in lagrows.iterrows():
        for s in range(int(r.serial - r.d) + 1, int(r.serial)):
            lag_missing.add((r.prefix, int(r.yr), s))
    table = [
        {"確かめ方": "① 全体で 最大−最小＋1 と件数", "言えること": f"差 {o['c1_diff']:,}（件数が多い）", "見つけた抜け": 0, "見つけた重複": 0,
         "欠番への空振り": 0, "最後の抜け": 0},
        {"確かめ方": "② 組ごとに 最大−最小＋1 と件数", "言えること": "差の合計 " + str(int(c2['diff'].sum())) + "（抜け＋欠番−重複）", "見つけた抜け": 0, "見つけた重複": 0,
         "欠番への空振り": 0, "最後の抜け": 0},
        {"確かめ方": "③ 前の番号との差（LAG）", "言えること": "抜けの場所と重複", "見つけた抜け": len(lag_missing & T_gap),
         "見つけた重複": o["c3_dup"], "欠番への空振り": len(lag_missing & T_void), "最後の抜け": len(lag_missing & T_tail)},
        {"確かめ方": "④ 番号の一覧と突き合わせ", "言えること": "抜けた番号と重複", "見つけた抜け": len(found4 & T_gap),
         "見つけた重複": int(o["c4_dup"].extra.sum()), "欠番への空振り": len(found4 & T_void), "最後の抜け": len(found4 & T_tail)},
        {"確かめ方": "⑤ ④から取消の欠番を除く", "言えること": "抜けた番号と重複", "見つけた抜け": len(found5 & T_gap),
         "見つけた重複": int(o["c4_dup"].extra.sum()), "欠番への空振り": len(found5 & T_void), "最後の抜け": len(found5 & T_tail)},
        {"確かめ方": "⑥ 発番の控えまで突き合わせ", "言えること": "抜けた番号と重複、最後の抜け", "見つけた抜け": len(found6 & T_gap),
         "見つけた重複": int(o["c4_dup"].extra.sum()), "欠番への空振り": len(found6 & T_void), "最後の抜け": len(found6 & T_tail)},
    ]
    tab = pd.DataFrame(table); tab.to_csv(RES / "found_by_check.csv", index=False)
    res["found"] = {r["確かめ方"]: {k: (int(v) if not isinstance(v, str) else v) for k, v in r.items() if k != "確かめ方"} for r in table}
    res["check1"] = {"差": o["c1_diff"], "件数": len(df), "番号の最大": int(df.serial.max())}
    res["check2_groups"] = c2m[["prefix", "yr", "diff", "gap", "void", "dup", "tail"]].astype({"gap": int, "void": int, "dup": int, "tail": int}).to_dict("records")
    assert dup4 == T_dup and (lag_missing - T_gap - T_void) == set()

    # ---- 抜けと重複が打ち消し合う場面：②が「差0」と言う割合 ----
    rng = np.random.default_rng(463)
    # 組ごとに抜け・重複が Poisson(λ) で起きるとき、差が0になる割合（問題があるのに）
    rows2 = []
    for lam in [0.5, 1, 2, 5, 10]:
        g = rng.poisson(lam, 200000); d = rng.poisson(lam, 200000)
        has = (g + d) > 0
        rows2.append({"組あたりの抜け・重複の平均（それぞれ）": lam, "問題のある組のうち②が差0と言う割合%": float(((g == d) & has).sum() / has.sum() * 100),
                      "問題のある組のうち②の差が±1以内%": float(((np.abs(g - d) <= 1) & has).sum() / has.sum() * 100)})
    canc = pd.DataFrame(rows2); canc.to_csv(RES / "cancellation.csv", index=False)
    res["cancellation"] = {str(r["組あたりの抜け・重複の平均（それぞれ）"]): round(r["問題のある組のうち②が差0と言う割合%"], 1) for _, r in canc.iterrows()}

    # ---- 200回くり返し：確かめ方ごとの見つけた割合 ----
    rec = []
    for rep in range(200):
        d2, v2, g2, dd2, t2, i2 = make(10000 + rep, n_per=2000)
        o2 = run_checks(con, d2, v2, i2)
        Tg, Tv, Tt = key(g2), key(v2), key(t2)
        f4, f5, f6 = key(o2["c4_missing"]), key(o2["c5_missing"]), key(o2["c6_missing"])
        c2z = int((o2["c2"]["diff"] == 0).sum())
        rec.append({"②で差0の組": c2z, "④抜け": len(f4 & Tg) / len(Tg), "④空振り": len(f4 & Tv), "⑤抜け": len(f5 & Tg) / len(Tg),
                    "⑤空振り": len(f5 & Tv), "最後の抜けを見つけた": len((f4 | f5) & Tt), "⑥最後の抜け": len(f6 & Tt), "⑥抜け": len(f6 & Tg) / len(Tg), "⑥空振り": len(f6 & Tv), "重複": int(o2["c4_dup"].extra.sum()) / len(dd2),
                    "①差": o2["c1_diff"]})
    rec = pd.DataFrame(rec); rec.to_csv(RES / "repeat_200.csv", index=False)
    res["repeat_200"] = {"④が見つけた抜け%": round(rec["④抜け"].mean() * 100, 1), "④の欠番への空振り（平均の件数）": round(rec["④空振り"].mean(), 1),
                         "⑤の空振り": round(rec["⑤空振り"].mean(), 1), "最後の抜けを見つけた回（①〜⑤）": int((rec["最後の抜けを見つけた"] > 0).sum()), "⑥が最後の抜け3件を全部見つけた回": int((rec["⑥最後の抜け"] == 3).sum()), "⑥が見つけた抜け%": round(rec["⑥抜け"].mean() * 100, 1), "⑥の空振り": round(rec["⑥空振り"].mean(), 1),
                         "重複を見つけた%": round(rec["重複"].mean() * 100, 1), "②で差0の組が1つ以上あった回%": round((rec["②で差0の組"] > 0).mean() * 100, 1),
                         "①の差が正だった回": int((rec["①差"] > 0).sum())}

    # ---- 文字として並べたときの落とし穴：接頭辞つきの番号を文字のまま MAX/MIN する ----
    con.register("slips", df)
    r = con.execute("SELECT MIN(slip_no), MAX(slip_no), COUNT(*), COUNT(DISTINCT slip_no) FROM slips").fetchone()
    res["as_text"] = {"最小": r[0], "最大": r[1], "行": r[2], "違う番号の数": r[3]}
    json.dump(res, open(RES / "a463_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    lab = ["①全体で\n最大−最小＋1と件数", "②組ごとに\n最大−最小＋1と件数", "③前の番号との差\n（LAG）", "④番号の一覧と\n突き合わせ", "⑤④から取消の\n欠番を除く", "⑥発番の控えまで\n突き合わせ"]
    x = np.arange(6); w = 0.26
    ax.bar(x - w, tab["見つけた抜け"], w, color=BLUE, label=f"見つけた抜け（入れたのは{n_gap}件）")
    ax.bar(x, tab["見つけた重複"], w, color=GREEN, label=f"見つけた重複（入れたのは{n_dup}件）")
    ax.bar(x + w, tab["欠番への空振り"], w, color=ORANGE, label=f"取消の欠番を「抜け」と言った数（欠番は{n_void}件）")
    for i in range(6):
        for dx, col in [(-w, "見つけた抜け"), (0, "見つけた重複"), (w, "欠番への空振り")]:
            ax.text(i + dx, tab[col][i] + 0.6, str(int(tab[col][i])), ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylabel("件数"); ax.set_ylim(0, max(n_void, n_gap) * 1.35)
    ax.set_title("確かめ方ごとの、見つけた抜け・重複と空振り"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a463_found_by_check.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    g = [f"{r.prefix}-{int(r.yr)}" for r in c2m.itertuples()]
    xx = np.arange(len(g))
    ax.bar(xx - 0.3, c2m.gap, 0.2, color=BLUE, label="抜け"); ax.bar(xx - 0.1, c2m.void, 0.2, color=LIGHT, label="取消の欠番")
    ax.bar(xx + 0.1, -c2m.dup, 0.2, color=GREEN, label="重複（マイナスに効く）"); ax.bar(xx + 0.3, c2m["diff"], 0.2, color=ORANGE, label="②が出す差")
    ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(xx); ax.set_xticklabels(g)
    ax.set_title("②の差は、抜け＋欠番−重複"); ax.set_ylabel("件数"); ax.set_ylim(-9, 19); ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center")
    ax = axes[1]
    ax.plot(canc.iloc[:, 0], canc.iloc[:, 1], "o-", color=ORANGE, label="差がちょうど0")
    ax.plot(canc.iloc[:, 0], canc.iloc[:, 2], "s-", color=BLUE, label="差が±1以内")
    for a, b in zip(canc.iloc[:, 0], canc.iloc[:, 1]):
        ax.annotate(f"{b:.0f}%", (a, b), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(canc.iloc[:, 0]); ax.set_xticklabels([f"{v:g}" for v in canc.iloc[:, 0]])
    ax.set_xlabel("1つの組に起きる抜け・重複の平均（それぞれ、件）"); ax.set_ylabel("問題のある組のうちの割合（%）")
    ax.set_title("抜けと重複が打ち消し合う割合"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, 100)
    save(fig, "a463_cancellation.png", SRC)

    fig, ax = plt.subplots(figsize=(9.5, 3.8)); ax.axis("off")
    cell = [[r["確かめ方"], r["言えること"], f"{r['見つけた抜け']}／{n_gap}", f"{r['見つけた重複']}／{n_dup}", f"{r['欠番への空振り']}／{n_void}",
             f"{r['最後の抜け']}／{n_tail}"] for r in table]
    t = ax.table(cellText=cell, colLabels=["確かめ方", "分かること", "抜け", "重複", "欠番への\n空振り", "最後の\n抜け"],
                 loc="center", cellLoc="left", colWidths=[0.33, 0.31, 0.08, 0.08, 0.10, 0.10])
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.9)
    for (i, j), c in t.get_celld().items():
        c.set_edgecolor("#dddddd")
        if i == 0: c.set_facecolor("#f0f0f0"); c.set_text_props(weight="bold")
    ax.set_title("確かめ方ごとに分かること（基本の場面）", fontsize=12)
    save(fig, "a463_table.png", SRC, y=0.02)


if __name__ == "__main__":
    main()
