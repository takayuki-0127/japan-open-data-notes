"""1311 データを日付の範囲で台に分けると、新しい日付を受け持つ1台に、書き込みはどれだけ集まるのか？（架空のデータ）

作成者が置いた架空のアプリの記録。台は10台。運用前の360日分（-360〜-1日目）の記録があり、
日付の範囲で36日ずつ10台に分けてある。運用を始めてから360日（0〜359日目）、毎日10万回の書き込みを乱数で作る。
1回の書き込みは、確率0.8で「その日の日付の新しい記録」、残り0.2で「前からある記録の書き直し」。
書き直す記録の日付は、その日から右に長い乱数の日数（平均20日）だけ前（-360日目より前にはしない）。
振り分け方：
  ① 日付の範囲（新しい日付は、いちばん新しい範囲の台がそのまま受け持つ）
  ② 日付の範囲（先の日付も36日ずつの範囲にして、台に順に割り当てておく）
  ③ 日付の番号を台数で割った余り（1日ごとに台が替わる）
  ④ 記録の番号を台数で割った余り（日付を見ない）
  ⑤ 日付の範囲を5つにし、1つの範囲を2台で受け持つ（範囲の中は記録の番号を2で割った余り）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1311
SRC = "架空のアプリの記録（作成者が置いた書き込みの作りと振り分けの決まりからの乱数、seed 1311）"
METHODS = ["m1_range_open", "m2_range_rotate", "m3_day_mod", "m4_id_mod", "m5_range_k2"]
LABELS = ["①日付の範囲（新しい日付は最後の台）", "②日付の範囲（先の日付も順に割り当て）", "③日付の番号の余り（1日ごとに替わる）",
          "④記録の番号の余り（日付を見ない）", "⑤日付の範囲を2台ずつで受け持つ"]
COLS = [ORANGE, "#c08a2a", BLUE, GRAY, GREEN]


def assign(date, rid, M, H, k=2):
    """書き込み（記録の日付 date、記録の番号 rid）ごとの台。H は運用前の日数"""
    L = H // M                                   # 1台の範囲の日数
    out = {}
    hist_m = np.clip((date + H) // L, 0, M - 1)  # 運用前の範囲。新しい日付は最後の台
    out["m1_range_open"] = hist_m
    rot = np.where(date >= 0, (date // L) % M, hist_m)
    out["m2_range_rotate"] = rot
    out["m3_day_mod"] = date % M
    out["m4_id_mod"] = rid % M
    G = M // k
    Lg = H // G
    grp = np.clip((date + H) // Lg, 0, G - 1)
    out["m5_range_k2"] = grp * k + (rid // M) % k
    return out


def simulate(rng, days, W, p_new, age_mean, M, H, k=2, keep_daily=False):
    busiest = {m: np.zeros(days) for m in METHODS}
    total = {m: np.zeros(M) for m in METHODS}
    daily_counts = []
    for d in range(days):
        new = rng.random(W) < p_new
        age = np.floor(rng.exponential(age_mean, W)).astype(np.int64)
        date = np.where(new, d, np.maximum(d - age, -H))
        rid = rng.integers(0, 2 ** 40, W)
        a = assign(date, rid, M, H, k)
        for m in METHODS:
            c = np.bincount(a[m], minlength=M)
            busiest[m][d] = c.max() / W
            total[m] += c
            if keep_daily:
                daily_counts.append({"day": d, "method": m, **{f"machine_{i}": int(c[i]) for i in range(M)}})
    return busiest, total, daily_counts


def main():
    t0 = time.time()
    M, H, DAYS, W, PNEW, AGE = 10, 360, 360, 100_000, 0.8, 20.0
    rng = np.random.default_rng([SEED, 1])
    busiest, total, daily = simulate(rng, DAYS, W, PNEW, AGE, M, H, keep_daily=True)
    pd.DataFrame(daily).to_csv(DATA / "daily_writes_by_machine.csv", index=False)

    base = {}
    rows = []
    for i, m in enumerate(METHODS):
        b = busiest[m]
        tot = total[m] / total[m].sum()
        base[m] = {"label": LABELS[i],
                   "daily_busiest_share_mean_pct": round(float(b.mean()) * 100, 2),
                   "daily_busiest_share_min_pct": round(float(b.min()) * 100, 2),
                   "daily_busiest_share_max_pct": round(float(b.max()) * 100, 2),
                   "daily_busiest_vs_average_mean": round(float(b.mean()) * M, 3),
                   "year_total_busiest_share_pct": round(float(tot.max()) * 100, 2),
                   "year_total_smallest_share_pct": round(float(tot.min()) * 100, 2),
                   "year_total_busiest_vs_average": round(float(tot.max()) * M, 3)}
        rows.append({"method": LABELS[i], **{kk: v for kk, v in base[m].items() if kk != "label"}})
    pd.DataFrame(rows).to_csv(RES / "base_by_method.csv", index=False)
    pd.DataFrame({"day": np.arange(DAYS), **{m: (busiest[m] * 100).round(3) for m in METHODS}}).to_csv(RES / "daily_busiest_share_pct.csv", index=False)

    # ②の範囲の中の日（範囲に入って何日目か）ごとの、いちばん多い1台の割合
    pos = np.arange(DAYS) % (H // M)
    m2pos = pd.DataFrame({"day_in_range": pos, "share": busiest["m2_range_rotate"]}).groupby("day_in_range").share.mean()
    m2_pos = {"first_day_pct": round(float(m2pos.iloc[0]) * 100, 2), "last_day_pct": round(float(m2pos.iloc[-1]) * 100, 2)}

    # 式の目安：①は新しい記録＋書き直しのうち最後の台の範囲（36日＋運用の日数）に入る分。初日の目安
    L = H // M
    m1_day0_formula = PNEW + (1 - PNEW) * (1 - np.exp(-L / AGE))
    # ③は新しい記録＋書き直しのうち、日付の差が台数の倍数になる分（差0を含む）
    q = np.exp(-1 / AGE)       # 1日ごとに残る割合（切り捨てた日数の分布）
    m3_formula = PNEW + (1 - PNEW) * (1 - q) / (1 - q ** M)
    # ⑤は①の分を2台で分ける
    formulas = {"m1_day0_formula_pct": round(float(m1_day0_formula) * 100, 2),
                "m3_formula_pct": round(float(m3_formula) * 100, 2),
                "m4_formula_pct": round(100 / M, 2)}

    # 保存されている記録（新しい記録の数）の割合：運用前も1日8万件の新しい記録があったと置く
    stored = {}
    for m in ["m1_range_open", "m2_range_rotate", "m3_day_mod", "m4_id_mod", "m5_range_k2"]:
        dates = np.arange(-H, DAYS)
        rid_share = np.full(M, 1 / M)
        if m == "m4_id_mod":
            sh = rid_share
        elif m == "m5_range_k2":
            G = M // 2; Lg = H // G
            grp = np.clip((dates + H) // Lg, 0, G - 1)
            c = np.bincount(grp, minlength=G) / len(dates)
            sh = np.repeat(c / 2, 2)
        else:
            a = assign(dates, np.zeros(len(dates), dtype=np.int64), M, H)[m]
            sh = np.bincount(a, minlength=M) / len(dates)
        stored[m] = round(float(sh.max()) * 100, 2)

    # k（1つの範囲を何台で受け持つか）を変える。基本の置き方、60日、1日2万回
    krows = []
    for k in [1, 2, 5, 10]:
        rg = np.random.default_rng([SEED, 2, k])
        b, _, _ = simulate(rg, 60, 20_000, PNEW, AGE, M, H, k=k)
        krows.append({"machines_per_range": k, "daily_busiest_share_mean_pct": round(float(b["m5_range_k2"].mean()) * 100, 2),
                      "busiest_vs_average": round(float(b["m5_range_k2"].mean()) * M, 3)})
    pd.DataFrame(krows).to_csv(RES / "by_machines_per_range.csv", index=False)

    # 確かめ：新しい記録の割合×書き直す記録の日数の平均×台数の27通り（60日、1日2万回）
    grid = []
    for pn in [0.5, 0.8, 0.95]:
        for am in [5, 20, 60]:
            for mm in [10, 20, 40]:
                rg = np.random.default_rng([SEED, 3, int(pn * 100), am, mm])
                b, _, _ = simulate(rg, 60, 20_000, pn, float(am), mm, H)
                grid.append({"p_new": pn, "update_age_mean_days": am, "machines": mm,
                             "m1_busiest_pct": round(float(b["m1_range_open"].mean()) * 100, 2),
                             "m3_busiest_pct": round(float(b["m3_day_mod"].mean()) * 100, 2),
                             "m4_busiest_pct": round(float(b["m4_id_mod"].mean()) * 100, 2),
                             "m5_busiest_pct": round(float(b["m5_range_k2"].mean()) * 100, 2),
                             "average_pct": round(100 / mm, 2),
                             "m1_vs_average": round(float(b["m1_range_open"].mean()) * mm, 3),
                             "m3_vs_average": round(float(b["m3_day_mod"].mean()) * mm, 3)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr)),
              "m1_busiest_range_pct": [float(gr.m1_busiest_pct.min()), float(gr.m1_busiest_pct.max())],
              "m3_busiest_range_pct": [float(gr.m3_busiest_pct.min()), float(gr.m3_busiest_pct.max())],
              "m5_busiest_range_pct": [float(gr.m5_busiest_pct.min()), float(gr.m5_busiest_pct.max())],
              "m4_busiest_range_pct": [float(gr.m4_busiest_pct.min()), float(gr.m4_busiest_pct.max())],
              "m1_vs_average_range": [float(gr.m1_vs_average.min()), float(gr.m1_vs_average.max())],
              "m3_vs_average_range": [float(gr.m3_vs_average.min()), float(gr.m3_vs_average.max())],
              "m1_at_least_p_new_count": int((gr.m1_busiest_pct >= gr.p_new * 100).sum()),
              "m3_at_least_p_new_count": int((gr.m3_busiest_pct >= gr.p_new * 100).sum())}

    out_json = {"base": base, "m2_by_day_in_range": m2_pos, "formula": formulas, "stored_busiest_share_pct_day359": stored,
                "by_machines_per_range": krows, "robust": robust,
                "setup": {"machines": M, "history_days": H, "days": DAYS, "writes_per_day": W, "p_new": PNEW,
                          "update_age_mean_days": AGE, "range_days": L, "grid_days": 60, "grid_writes_per_day": 20_000}}
    json.dump(out_json, open(RES / "a1311_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：日ごとのいちばん多い1台の割合
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    for i, m in enumerate(METHODS):
        ax.plot(np.arange(DAYS), busiest[m] * 100, color=COLS[i], lw=1.1, label=LABELS[i])
    ax.axhline(100 / M, color=GRAY, lw=0.8, ls="--")
    ax.text(DAYS - 2, 100 / M + 2, "平均（10%）", ha="right", fontsize=8.5, color=INK)
    ax.set_ylim(0, 105); ax.set_xlim(0, DAYS - 1)
    ax.set_xlabel("運用を始めてからの日（0〜359日目）"); ax.set_ylabel("その日の書き込みのうち、いちばん多い1台の割合（%）", fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    ax.set_title("日付だけで台を決める①②③は、その日の書き込みの8割以上が1台に集まった（10台）", fontsize=12)
    save(fig, "a1311_daily_busiest.png", SRC, y=-0.2)

    # 図2：1日ごとの平均と、360日の合計で見たいちばん多い1台
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    x = np.arange(len(METHODS))
    dd = [base[m]["daily_busiest_share_mean_pct"] for m in METHODS]
    yy = [base[m]["year_total_busiest_share_pct"] for m in METHODS]
    ax.bar(x - 0.2, dd, 0.4, color=BLUE, label="1日ごとに見たとき（360日の平均）")
    ax.bar(x + 0.2, yy, 0.4, color=LIGHT, label="360日の合計で見たとき")
    for xi, v in zip(x - 0.2, dd):
        ax.text(xi, v + 1.5, f"{v:.2f}", ha="center", fontsize=7.5)
    for xi, v in zip(x + 0.2, yy):
        ax.text(xi, v + 1.5, f"{v:.2f}", ha="center", fontsize=7.5)
    ax.axhline(100 / M, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels(["①範囲\n（最後の台）", "②範囲\n（順に割り当て）", "③日付の\n番号の余り", "④記録の\n番号の余り", "⑤範囲を\n2台ずつ"], fontsize=8.5)
    ax.set_ylim(0, 110); ax.set_ylabel("書き込みのうち、いちばん多い1台の割合（%）", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("②③は360日の合計では均等に近いが、1日ごとには1台に集まる", fontsize=12)
    save(fig, "a1311_day_vs_year.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    gx = np.arange(len(gr))
    for kk in range(3):  # 新しい記録の割合の組ごとに線を切る（組をまたいで線を結ばない）
        sl = slice(kk * 9, kk * 9 + 9)
        ax.plot(gx[sl], gr.m1_busiest_pct.values[sl], "o-", color=ORANGE, ms=4, lw=0.9, label="①日付の範囲（最後の台）" if kk == 0 else None)
        ax.plot(gx[sl], gr.m3_busiest_pct.values[sl], "o-", color=BLUE, ms=4, lw=0.9, label="③日付の番号の余り" if kk == 0 else None)
        ax.plot(gx[sl], gr.m5_busiest_pct.values[sl], "o-", color=GREEN, ms=4, lw=0.9, label="⑤範囲を2台ずつ" if kk == 0 else None)
        ax.plot(gx[sl], gr.m4_busiest_pct.values[sl], "o-", color=GRAY, ms=4, lw=0.9, label="④記録の番号の余り" if kk == 0 else None)
    for kk in [9, 18]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    for kk, pn in enumerate([0.5, 0.8, 0.95]):
        ax.text(kk * 9 + 4, 106, f"新しい記録の割合{pn}", ha="center", fontsize=8.5)
    ax.set_ylim(0, 112)
    ax.set_xticks(gx); ax.set_xticklabels([f"{a}日・{m}台" for a, m in zip(gr.update_age_mean_days, gr.machines)], fontsize=6, rotation=90)
    ax.set_xlabel("27通り（下は「書き直す記録の日数の平均・台数」）", fontsize=8.5)
    ax.set_ylabel("いちばん多い1台の割合（%、60日の平均）", fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.24))
    ax.set_title("日付で決める①③は、どの置き方でも新しい記録の割合より上に残る", fontsize=11.5)
    save(fig, "a1311_grid.png", SRC, y=-0.27)

    print(json.dumps(out_json, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
