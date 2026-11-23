"""1025 予約を締め切る時刻で、埋まり具合の見え方は変わるのか？（架空のデータ）

架空の飲食店の昼のコース（定員24人、1人ずつの申し込み）。
申し込みは開始の何時間か前に入り、締め切りより後の申し込みは受けられない。
受けた予約の一部は開始までに取り消され、締め切り前の取り消しの席は後の申し込みで埋まるが、
締め切り後の取り消しの席は埋まらない。同じ申し込みのまま締め切りの時刻だけを変え、
「締め切り時点の埋まり具合」と「当日座った人数」がどう変わるかを数える。
"""
import heapq
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1025
SRC = "架空の飲食店の予約（作成者が乱数で作成、seed 1025）"
CAP = 24
CUTOFFS = (72, 24, 3, 1)                     # 締め切り：開始の何時間前
CUT_NAME = {72: "3日前", 24: "前日（24時間前）", 3: "当日3時間前", 1: "当日1時間前"}
BASE = dict(dem_lo=16, dem_hi=32, late=0.30, cancel=0.15, noshow=0.05, walkin=0.5)
EARLY_MEAN, LEAD_MAX = 96.0, 720.0


def make_sessions(rng, n, dem_lo, dem_hi, late, cancel, noshow, walkin):
    out = []
    dem = rng.uniform(dem_lo, dem_hi, size=n)
    for i in range(n):
        k = rng.poisson(dem[i])
        is_late = rng.random(k) < late
        lead = np.where(is_late, rng.uniform(0, 24, k), np.minimum(24 + rng.exponential(EARLY_MEAN, k), LEAD_MAX))
        cfrac = np.where(rng.random(k) < cancel, rng.random(k), -1.0)   # 予約から開始までのどこで取り消すか
        ns = rng.random(k) < noshow
        wk = rng.random(k) < walkin                                       # 締め切り後なら飛び込みで来る
        out.append((dem[i], lead, cfrac, ns, wk))
    return out


def run_session(lead, cfrac, ns, wk, cut):
    order = np.argsort(-lead)                # 早い申し込みから
    held = 0
    heap = []                                # (取り消す時刻＝開始の何時間前を負にした値, 来ない)
    lost_after, lost_full, walk_want = 0, 0, 0
    for i in order:
        L = lead[i]
        if L <= cut:
            if wk[i]:
                walk_want += 1
            else:
                lost_after += 1
            continue
        while heap and heap[0][0] <= -L:
            heapq.heappop(heap); held -= 1
        if held >= CAP:
            lost_full += 1
            continue
        held += 1
        tc = -(L * (1 - cfrac[i])) if cfrac[i] >= 0 else 1.0   # 取り消す時刻（開始＝0、それより前は負）
        heapq.heappush(heap, (tc, bool(ns[i])))
    while heap and heap[0][0] <= -cut:
        heapq.heappop(heap); held -= 1
    at_cut = held
    seated = sum(1 for tc, n in heap if tc > 0 and not n)
    cancel_after = sum(1 for tc, n in heap if tc <= 0)
    noshow = sum(1 for tc, n in heap if tc > 0 and n)
    walk = min(walk_want, CAP - seated)
    lost_after += walk_want - walk
    return at_cut, seated, walk, cancel_after, noshow, lost_after, lost_full


def simulate(rng, n, dem_lo, dem_hi, late, cancel, noshow, walkin):
    sess = make_sessions(rng, n, dem_lo, dem_hi, late, cancel, noshow, walkin)
    rows = []
    for j, (dem, lead, cfrac, ns, wk) in enumerate(sess):
        for cut in CUTOFFS:
            a, s, w, ca, no, la, lf = run_session(lead, cfrac, ns, wk, cut)
            rows.append({"session": j, "demand_mean": dem, "requests": len(lead), "cutoff_h": cut,
                         "booked_at_cutoff": a, "seated_booked": s, "walkin": w, "seated": s + w,
                         "cancel_after_cutoff": ca, "noshow": no,
                         "lost_after_cutoff": la, "lost_full": lf,
                         "requests_before_cutoff": int((lead > cut).sum())})
    return pd.DataFrame(rows)


def share_before(cut, late):
    """申し込みが締め切りより前に入る割合（式の値）"""
    p_late = (24 - min(cut, 24)) / 24
    p_early = 1.0 if cut <= 24 else float(np.exp(-(cut - 24) / EARLY_MEAN))
    return late * p_late + (1 - late) * p_early


def summarize(df, late):
    rows = []
    for cut, g in df.groupby("cutoff_h", sort=False):
        rows.append({"cutoff_h": cut, "cutoff": CUT_NAME[cut],
                     "fill_at_cutoff": round(float(g.booked_at_cutoff.mean() / CAP) * 100, 2),
                     "seated_rate": round(float(g.seated.mean() / CAP) * 100, 2),
                     "seated_booked_rate": round(float(g.seated_booked.mean() / CAP) * 100, 2),
                     "walkin_rate": round(float(g.walkin.mean() / CAP) * 100, 2),
                     "gap_pt": round(float((g.booked_at_cutoff - g.seated_booked).mean() / CAP) * 100, 2),
                     "cancel_after_cutoff_per_cap": round(float(g.cancel_after_cutoff.mean() / CAP) * 100, 2),
                     "noshow_per_cap": round(float(g.noshow.mean() / CAP) * 100, 2),
                     "share_full_at_cutoff": round(float((g.booked_at_cutoff >= CAP).mean()) * 100, 2),
                     "lost_after_cutoff_share": round(float(g.lost_after_cutoff.sum() / g.requests.sum()) * 100, 2),
                     "lost_full_share": round(float(g.lost_full.sum() / g.requests.sum()) * 100, 2),
                     "before_cutoff_share": round(float(g.requests_before_cutoff.sum() / g.requests.sum()) * 100, 2),
                     "before_cutoff_share_formula": round(share_before(cut, late) * 100, 2)})
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df = simulate(rng, 12000, **BASE)
    df[df.session < 1000].to_csv(DATA / "sessions.csv", index=False, float_format="%.3f")
    tab = summarize(df, BASE["late"])
    tab.to_csv(RES / "by_cutoff.csv", index=False)
    t = tab.set_index("cutoff_h")
    res = {"sessions": int(df.session.nunique()), "capacity": CAP, "setting": dict(BASE, early_mean_h=EARLY_MEAN, lead_max_h=LEAD_MAX, cutoffs_h=list(CUTOFFS)),
           "fill_jump_72_to_1_pt": round(float(t.loc[1, "fill_at_cutoff"] - t.loc[72, "fill_at_cutoff"]), 2),
           "seated_jump_72_to_1_pt": round(float(t.loc[1, "seated_rate"] - t.loc[72, "seated_rate"]), 2),
           "fill_jump_24_to_1_pt": round(float(t.loc[1, "fill_at_cutoff"] - t.loc[24, "fill_at_cutoff"]), 2),
           "seated_jump_24_to_1_pt": round(float(t.loc[1, "seated_rate"] - t.loc[24, "seated_rate"]), 2),
           "max_abs_before_share_vs_formula_pt": round(float((tab.before_cutoff_share - tab.before_cutoff_share_formula).abs().max()), 2)}

    # 2つの店：A は申し込みが多く3日前締め切り、B は少なく1時間前締め切り。30回（1か月）ごとの平均で比べる
    rngc = np.random.default_rng([SEED, 7])
    cmp_rows = []
    for gapname, (a_lo, a_hi, b_lo, b_hi) in {"Aが2割多い": (19.2, 38.4, 16, 32), "Aが1割多い": (17.6, 35.2, 16, 32), "同じ": (16, 32, 16, 32)}.items():
        kw = {k: v for k, v in BASE.items() if k not in ("dem_lo", "dem_hi")}
        da = simulate(rngc, 3000, a_lo, a_hi, **kw)
        db = simulate(rngc, 3000, b_lo, b_hi, **kw)
        A = da[da.cutoff_h == 72].reset_index(drop=True); B = db[db.cutoff_h == 1].reset_index(drop=True)
        A["month"] = A.session // 30; B["month"] = B.session // 30
        ma = A.groupby("month")[["booked_at_cutoff", "seated", "requests"]].mean()
        mb = B.groupby("month")[["booked_at_cutoff", "seated", "requests"]].mean()
        cmp_rows.append({"case": gapname, "months": int(len(ma)),
                         "A_requests_mean": round(float(A.requests.mean()), 2), "B_requests_mean": round(float(B.requests.mean()), 2),
                         "A_fill_at_cutoff": round(float(A.booked_at_cutoff.mean() / CAP) * 100, 2),
                         "B_fill_at_cutoff": round(float(B.booked_at_cutoff.mean() / CAP) * 100, 2),
                         "A_seated_rate": round(float(A.seated.mean() / CAP) * 100, 2),
                         "B_seated_rate": round(float(B.seated.mean() / CAP) * 100, 2),
                         "share_months_B_fill_higher": round(float((mb.booked_at_cutoff.values > ma.booked_at_cutoff.values).mean()) * 100, 2),
                         "share_months_B_seated_higher": round(float((mb.seated.values > ma.seated.values).mean()) * 100, 2),
                         "share_months_B_requests_higher": round(float((mb.requests.values > ma.requests.values).mean()) * 100, 2)})
    cmpdf = pd.DataFrame(cmp_rows)
    cmpdf.to_csv(RES / "two_shops.csv", index=False)

    # 確かめ：27通り
    rows = []
    for wkr in (0.0, 0.5, 0.9):
        for late in (0.10, 0.30, 0.50):
            for cc in (0.05, 0.15, 0.30):
                d = simulate(rng, 800, BASE["dem_lo"], BASE["dem_hi"], late, cc, BASE["noshow"], wkr)
                tb = summarize(d, late).set_index("cutoff_h")
                rows.append({"walkin": wkr, "late": late, "cancel": cc,
                             "fill_72": tb.loc[72, "fill_at_cutoff"], "fill_24": tb.loc[24, "fill_at_cutoff"], "fill_1": tb.loc[1, "fill_at_cutoff"],
                             "seated_72": tb.loc[72, "seated_rate"], "seated_1": tb.loc[1, "seated_rate"],
                             "fill_jump_72_to_1_pt": round(tb.loc[1, "fill_at_cutoff"] - tb.loc[72, "fill_at_cutoff"], 2),
                             "seated_jump_72_to_1_pt": round(tb.loc[1, "seated_rate"] - tb.loc[72, "seated_rate"], 2),
                             "gap_72_pt": tb.loc[72, "gap_pt"], "gap_1_pt": tb.loc[1, "gap_pt"],
                             "max_abs_before_share_vs_formula_pt": round(float((tb.before_cutoff_share - tb.before_cutoff_share_formula).abs().max()), 2)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    # 確かめ：申し込みの多さ（基本の置き方のまま）
    drows = []
    for dl, dh, dn in [(8, 24, "少ない"), (16, 32, "基本"), (24, 40, "多い")]:
        kw = {k: v for k, v in BASE.items() if k not in ("dem_lo", "dem_hi")}
        tb = summarize(simulate(rng, 2000, dl, dh, **kw), BASE["late"]).set_index("cutoff_h")
        drows.append({"demand": dn, "dem_lo": dl, "dem_hi": dh, "fill_72": tb.loc[72, "fill_at_cutoff"], "fill_1": tb.loc[1, "fill_at_cutoff"],
                      "seated_72": tb.loc[72, "seated_rate"], "seated_1": tb.loc[1, "seated_rate"],
                      "fill_jump_72_to_1_pt": round(tb.loc[1, "fill_at_cutoff"] - tb.loc[72, "fill_at_cutoff"], 2),
                      "seated_jump_72_to_1_pt": round(tb.loc[1, "seated_rate"] - tb.loc[72, "seated_rate"], 2)})
    pd.DataFrame(drows).to_csv(RES / "sensitivity_demand.csv", index=False)
    res["grid"] = {}
    for c in ["fill_jump_72_to_1_pt", "seated_jump_72_to_1_pt", "gap_72_pt", "gap_1_pt", "max_abs_before_share_vs_formula_pt"]:
        res["grid"][c + "_min"] = float(grid[c].min()); res["grid"][c + "_max"] = float(grid[c].max())
    res["grid"]["n_fill_jump_bigger_than_seated_jump"] = int((grid.fill_jump_72_to_1_pt > grid.seated_jump_72_to_1_pt).sum())
    res["grid"]["n_gap72_bigger_than_gap1"] = int((grid.gap_72_pt > grid.gap_1_pt).sum())
    for wv in (0.0, 0.5, 0.9):
        gw = grid[grid.walkin == wv]
        res["grid"][f"walkin{int(wv * 100)}_fill_jump_min"] = float(gw.fill_jump_72_to_1_pt.min())
        res["grid"][f"walkin{int(wv * 100)}_fill_jump_max"] = float(gw.fill_jump_72_to_1_pt.max())
        res["grid"][f"walkin{int(wv * 100)}_seated_jump_min"] = float(gw.seated_jump_72_to_1_pt.min())
        res["grid"][f"walkin{int(wv * 100)}_seated_jump_max"] = float(gw.seated_jump_72_to_1_pt.max())
    res["grid"]["n"] = int(len(grid)); res["grid"]["sessions_each"] = 800
    with open(RES / "a1025_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：締め切りごとの、締め切り時点の埋まり具合と当日座った人数
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    x = np.arange(len(tab))
    ax.bar(x - 0.2, tab.fill_at_cutoff, 0.4, color=ORANGE, label="締め切り時点の埋まり具合")
    ax.bar(x + 0.2, tab.seated_booked_rate, 0.4, color=BLUE, label="当日座った人数（予約）")
    ax.bar(x + 0.2, tab.walkin_rate, 0.4, bottom=tab.seated_booked_rate, color=LIGHT, label="当日座った人数（飛び込み）")
    for i, r in tab.iterrows():
        ax.text(i - 0.2, r.fill_at_cutoff + 1.5, f"{r.fill_at_cutoff:.1f}", ha="center", fontsize=8.5, color=ORANGE)
        ax.text(i + 0.2, r.seated_rate + 1.5, f"{r.seated_rate:.1f}", ha="center", fontsize=8.5, color=BLUE)
    ax.set_xticks(x); ax.set_xticklabels([f"{c}\n締め切り" for c in tab.cutoff])
    ax.set_ylim(0, 100); ax.set_ylabel("24席に対する割合（%、平均）")
    ax.set_title("同じ申し込みで、締め切りの時刻だけを変えると")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    save(fig, "a1025_by_cutoff.png", SRC)

    # 図2：2つの店
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    x = np.arange(len(cmpdf))
    ax.bar(x - 0.2, cmpdf.A_fill_at_cutoff, 0.4, color=GRAY, label="A店（3日前締め切り）")
    ax.bar(x + 0.2, cmpdf.B_fill_at_cutoff, 0.4, color=BLUE, label="B店（1時間前締め切り）")
    for i, r in cmpdf.iterrows():
        ax.text(i - 0.2, r.A_fill_at_cutoff + 1.5, f"{r.A_fill_at_cutoff:.1f}", ha="center", fontsize=8.5)
        ax.text(i + 0.2, r.B_fill_at_cutoff + 1.5, f"{r.B_fill_at_cutoff:.1f}", ha="center", fontsize=8.5, color=BLUE)
        ax.text(i, 92, f"Bが埋まって見えた月 {r.share_months_B_fill_higher:.1f}%", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([f"申し込み：{c}" for c in cmpdf.case])
    ax.set_ylim(0, 115); ax.set_ylabel("締め切り時点の埋まり具合（%、平均）")
    ax.set_title("申し込みの多い店と、締め切りの遅い店")
    ax.legend(fontsize=8.5, frameon=False, loc="upper center", ncol=2)
    save(fig, "a1025_two_shops.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    mk = {0.10: "o", 0.30: "s", 0.50: "^"}
    cl = {0.0: LIGHT, 0.5: BLUE, 0.9: INK}
    for _, r in grid.iterrows():
        ax.scatter(r.seated_jump_72_to_1_pt, r.fill_jump_72_to_1_pt, marker=mk[r.late], color=cl[r.walkin], s=40)
    lim = [min(grid.seated_jump_72_to_1_pt.min(), 0) - 1, max(grid.fill_jump_72_to_1_pt.max(), grid.seated_jump_72_to_1_pt.max()) + 3]
    ax.plot(lim, lim, color=GRAY, lw=0.8, ls=":")
    for k2, m in mk.items():
        ax.scatter([], [], marker=m, color=GRAY, label=f"直前の申し込み {int(k2 * 100)}%")
    for c2, c in cl.items():
        ax.scatter([], [], marker="o", color=c, label=f"締め切り後に飛び込みで来る {int(c2 * 100)}%")
    ax.set_xlabel("当日座った人数（予約＋飛び込み）の上がり幅（ポイント）")
    ax.set_ylabel("締め切り時点の埋まり具合の上がり幅（ポイント）")
    ax.set_title("3日前→1時間前締め切りにしたときの上がり幅（27通り）")
    ax.text(12, 4, "点線：2つの上がり幅が同じ", fontsize=8, color=GRAY, ha="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right", ncol=2)
    save(fig, "a1025_grid.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(tab.to_string()); print(cmpdf.to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
