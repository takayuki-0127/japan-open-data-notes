"""877 予約の時刻どおりに来ない人が1割いると、後の人はどれだけ待つのか？（架空のデータ）

架空の店の予約制カウンター（担当1人、10:00〜18:00、15分ごとに1人の予約＝1日32人）。
1人の手続き時間は平均12分の対数正規分布。時刻どおりの人は予約の少し前に着き、遅れる人は予約より遅れて着く。
同じ日（同じ手続き時間・同じ着く時刻）で、遅れる人がいる場合といない場合、店の回し方（待つ幅）を比べる。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 877
SRC = "架空の店の予約制カウンター（作成者が乱数で作成、seed 877）"
SLOT, N_SLOT, CLOSE = 15.0, 32, 480.0
# 回し方：予約から何分まで遅れた人を待つか。-1 は「来た順＋早く着いた人は予約の前でも始める」
GRACES = {"来た順（遅れた人は着いた時点で並ぶ）": 0.0, "5分まで待つ": 5.0, "10分まで待つ": 10.0,
          "予約順を必ず守る（来るまで待つ）": np.inf, "来た順＋早く着いた人は前倒しで始める": -1.0}
GKEY = {0.0: "g0", 5.0: "g5", 10.0: "g10", np.inf: "ginf", -1.0: "early"}


def make_day(rng, p_late=0.10, late_mean=12.0, svc_mean=12.0, cv=0.4):
    appt = np.arange(N_SLOT) * SLOT
    s2 = np.log(1 + cv ** 2)
    svc = rng.lognormal(np.log(svc_mean) - s2 / 2, np.sqrt(s2), N_SLOT)
    early = rng.normal(-3.0, 2.0, N_SLOT)              # 時刻どおりの人：平均3分前に着く
    late_by = 3.0 + rng.exponential(late_mean - 3.0, N_SLOT)  # 遅れる人：平均 late_mean 分遅れ
    u = rng.random(N_SLOT)
    is_late = u < p_late
    arr_late = appt + np.where(is_late, late_by, early)
    arr_none = appt + early                              # 同じ日に、だれも遅れなかったら
    return appt, svc, arr_late, arr_none, is_late


def serve(appt, svc, arr, grace):
    """予約時刻より前には始めない。予約から grace 分を過ぎて着いた人は、着いた時刻の順に並ぶ"""
    early = grace < 0
    grace = max(grace, 0.0)
    elig = arr if early else np.maximum(arr, appt)
    key = np.where(arr <= appt + grace, appt, arr)
    order = np.lexsort((appt, key))
    start = np.empty(N_SLOT); free = 0.0
    for i in order:
        st = max(free, elig[i]); start[i] = st; free = st + svc[i]
    return start, free


def day_stats(appt, svc, arr, is_late, grace):
    start, end = serve(appt, svc, arr, grace)
    w_from_appt = np.maximum(start - appt, 0.0)         # 予約の時刻から始まるまで（前倒しは0）
    w_from_arr = start - np.maximum(arr, appt)
    return start, end, w_from_appt, w_from_arr


def simulate(seed, days, p_late=0.10, late_mean=12.0, svc_mean=12.0, cv=0.4, keep=False):
    rng = np.random.default_rng(seed)
    acc = {g: {"ontime_w": [], "ontime_w_none": [], "late_w": [], "over": [], "over_none": [], "slot_w": [],
               "slot_w_none": []} for g in GRACES.values()}
    for _ in range(days):
        appt, svc, arr, arr0, il = make_day(rng, p_late, late_mean, svc_mean, cv)
        for g in GRACES.values():
            _, end, w, wa = day_stats(appt, svc, arr, il, g)
            _, end0, w0, _ = day_stats(appt, svc, arr0, np.zeros(N_SLOT, bool), g)
            a = acc[g]
            a["ontime_w"].append(w[~il]); a["ontime_w_none"].append(w0[~il]); a["late_w"].append(wa[il])
            a["over"].append(max(0.0, end - CLOSE)); a["over_none"].append(max(0.0, end0 - CLOSE))
            if keep:
                a["slot_w"].append(np.where(il, np.nan, w)); a["slot_w_none"].append(w0)
    out = {}
    for g, a in acc.items():
        on, on0 = np.concatenate(a["ontime_w"]), np.concatenate(a["ontime_w_none"])
        lw = np.concatenate(a["late_w"]) if sum(len(x) for x in a["late_w"]) else np.array([np.nan])
        ov, ov0 = np.array(a["over"]), np.array(a["over_none"])
        o = {"ontime_mean": float(on.mean()), "ontime_mean_if_none_late": float(on0.mean()),
             "ontime_extra": float(on.mean() - on0.mean()),
             "ontime_p_gt10": float((on > 10).mean()), "ontime_p_gt10_if_none": float((on0 > 10).mean()),
             "late_wait_mean": float(np.nanmean(lw)), "overtime_mean": float(ov.mean()),
             "overtime_mean_if_none": float(ov0.mean()), "p_overtime_gt15": float((ov > 15).mean()),
             "late_count": int(np.isfinite(lw).sum()), "ontime_count": int(len(on))}
        o["extra_total_per_late"] = (float((on.sum() - on0.sum()) / o["late_count"]) if o["late_count"] else 0.0)
        if keep:
            o["slot_w"] = np.nanmean(np.vstack(a["slot_w"]), 0); o["slot_w_none"] = np.vstack(a["slot_w_none"]).mean(0)
        out[g] = o
    return out


def r(d, k=3):
    return {a: (round(b, k) if isinstance(b, float) else b) for a, b in d.items() if not isinstance(b, np.ndarray)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1回分（data）
    appt, svc, arr, arr0, il = make_day(rng)
    cols = {"slot": np.arange(1, N_SLOT + 1), "appt_min": appt, "service_min": svc, "arrival_min": arr,
            "is_late": il.astype(int), "arrival_if_none_late": arr0}
    for g in GRACES.values():
        st, _, w, _ = day_stats(appt, svc, arr, il, g)
        cols[f"start_{GKEY[g]}"] = st
    pd.DataFrame(cols).to_csv(DATA / "one_day.csv", index=False, float_format="%.3f")

    # 2) 基本：遅れる人1割・平均12分遅れ・手続き平均12分（ばらつき0.4）、2,000日
    base = simulate(SEED * 10, 2000, keep=True)
    rows = []
    for name, g in GRACES.items():
        rows.append({"policy": name, **r(base[g])})
    bdf = pd.DataFrame(rows)
    bdf.to_csv(RES / "base_policies.csv", index=False)
    slot_df = pd.DataFrame({"slot": np.arange(1, N_SLOT + 1),
                            **{f"ontime_wait_{GKEY[g]}": np.round(base[g]["slot_w"], 3) for g in GRACES.values()},
                            **{f"if_none_late_{GKEY[g]}": np.round(base[g]["slot_w_none"], 3) for g in GRACES.values()}})
    slot_df.to_csv(RES / "wait_by_slot.csv", index=False)

    # 3) 確かめ：遅れる人の割合（各500日）
    sp = []
    for i, p in enumerate((0.0, 0.05, 0.10, 0.20, 0.30)):
        o = simulate(SEED * 100 + i, 500, p_late=p)
        for name, g in GRACES.items():
            sp.append({"p_late": p, "policy": name, **r(o[g])})
    sp = pd.DataFrame(sp); sp.to_csv(RES / "sensitivity_p_late.csv", index=False)
    # 4) 確かめ：遅れの長さ×手続き時間の平均×ばらつき（遅れる人1割、各300日）
    sq = []
    combos = [(L, m, cv) for L in (5.0, 12.0, 20.0) for m in (10.0, 12.0, 13.5) for cv in (0.2, 0.4, 0.8)]
    for i, (L, m, cv) in enumerate(combos):
        o = simulate(SEED * 1000 + i, 300, 0.10, L, m, cv)
        for name, g in GRACES.items():
            sq.append({"late_mean": L, "svc_mean": m, "cv": cv, "policy": name, **r(o[g])})
    sq = pd.DataFrame(sq); sq.to_csv(RES / "sensitivity_grid.csv", index=False)

    def rng_of(df, g, col):
        v = df[df.policy == [k for k, x in GRACES.items() if x == g][0]][col]
        return [round(float(v.min()), 3), round(float(v.max()), 3)]
    rat = (sq[sq.policy == "予約順を必ず守る（来るまで待つ）"].ontime_extra.values /
           sq[sq.policy == "来た順（遅れた人は着いた時点で並ぶ）"].ontime_extra.values)
    out = {"setting": {"slots": N_SLOT, "slot_min": SLOT, "svc_mean": 12.0, "cv": 0.4, "p_late": 0.10,
                       "late_mean": 12.0, "ontime_arrival": "予約の平均3分前（標準偏差2分）", "days": 2000},
           "base": {GKEY[g]: r(base[g]) for g in GRACES.values()},
           "grid_ontime_extra_range": {GKEY[g]: rng_of(sq, g, "ontime_extra") for g in GRACES.values()},
           "grid_late_wait_range": {GKEY[g]: rng_of(sq, g, "late_wait_mean") for g in GRACES.values()},
           "grid_extra_total_per_late_range": {GKEY[g]: rng_of(sq, g, "extra_total_per_late") for g in GRACES.values()},
           "grid_ontime_extra_by_late_mean": {GKEY[g]: {str(L): [round(float(v.min()), 3), round(float(v.max()), 3)]
                                                        for L, v in sq[sq.policy == n].groupby("late_mean").ontime_extra}
                                              for n, g in GRACES.items() if g in (0.0, np.inf)},
           "late_share_within_5min_calc": round(float(1 - np.exp(-2.0 / 9.0)), 3),
           "late_share_within_10min_calc": round(float(1 - np.exp(-7.0 / 9.0)), 3),
           "grid_ratio_ginf_over_g0_extra": [round(float(rat.min()), 2), round(float(rat.max()), 2)],
           "grid_ginf_ge_g0_all": bool((rat >= 1 - 1e-9).all()),
           "one_day_late_slots": [int(x) for x in np.where(il)[0] + 1]}
    json.dump(out, open(RES / "a877_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：時刻どおりの人の平均の待ち（遅れる人あり／なし）
    names = list(GRACES.keys()); gs = list(GRACES.values())
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    y = np.arange(len(gs))[::-1]
    v0 = [base[g]["ontime_mean_if_none_late"] for g in gs]; v1 = [base[g]["ontime_mean"] for g in gs]
    ax.barh(y + 0.2, v0, 0.38, color=LIGHT, label="だれも遅れなかったら")
    ax.barh(y - 0.2, v1, 0.38, color=BLUE, label="1割が遅れて来る")
    for yi, a, b in zip(y, v0, v1):
        ax.text(a + 0.1, yi + 0.2, f"{a:.1f}分", va="center", fontsize=8.5)
        ax.text(b + 0.1, yi - 0.2, f"{b:.1f}分（+{b - a:.1f}）", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("時刻どおりに来た人の、予約の時刻から始まるまでの平均（分）")
    ax.set_xlim(0, max(v1) * 1.45); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("遅れた人を待つほど、時刻どおりの人の待ちが増える（2,000日）")
    save(fig, "a877_policies.png", SRC)

    # 図2：予約の枠ごとの待ち（時刻どおりの人）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(1, N_SLOT + 1)
    ax.plot(x, base[0.0]["slot_w_none"], color=GRAY, lw=2, ls="--", label="だれも遅れなかったら")
    ax.plot(x, base[0.0]["slot_w"], color=BLUE, lw=2, label="1割遅れ・来た順")
    ax.plot(x, base[np.inf]["slot_w"], color=ORANGE, lw=2, label="1割遅れ・予約順を必ず守る")
    ax.set_xlabel("予約の枠（1＝10:00、32＝17:45）"); ax.set_ylabel("時刻どおりの人の平均の待ち（分）")
    ax.set_xticks([1, 8, 16, 24, 32]); ax.legend(frameon=False, fontsize=9)
    ax.set_title("待ちは朝の数枠でたまり、そのあとは高いまま続く（2,000日）")
    save(fig, "a877_by_slot.png", SRC)

    # 図3：遅れる人の割合を変える
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for name, col, lab in [("来た順（遅れた人は着いた時点で並ぶ）", BLUE, "来た順（5分・10分まで待つも、ほぼ同じ線）"),
                           ("予約順を必ず守る（来るまで待つ）", ORANGE, "予約順を必ず守る（来るまで待つ）"),
                           ("来た順＋早く着いた人は前倒しで始める", GREEN, "来た順＋早く着いた人は前倒しで始める")]:
        d = sp[sp.policy == name]
        ax.plot(d.p_late * 100, d.ontime_mean, "o-", color=col, lw=2, label=lab)
    ax.set_xlabel("遅れて来る人の割合（%）"); ax.set_ylabel("時刻どおりの人の平均の待ち（分）")
    ax.set_xticks([0, 5, 10, 20, 30]); ax.legend(frameon=False, fontsize=8.5)
    ax.set_ylim(0, None)
    ax.set_title("遅れる人が増えたときの、時刻どおりの人の待ち（各500日）")
    save(fig, "a877_p_late.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
