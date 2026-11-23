"""1039 移動時間の短縮は、全体の時間をどれだけ減らすのか？（架空のデータ）

架空の通勤：家→（歩き8分）→駅→路線1（10分おき、乗って20分）→乗りかえ（歩き2分）→路線2（10分おき、乗って12分）→（歩き6分）→職場。
家を出る時刻はでたらめ。路線1の乗っている時間だけを d 分短くしたとき、家から職場までの時間（全体の時間）が
どれだけ減るかを、時刻表（路線2の発車の位置）を作り直して数える。路線2だけを短くした場合とも比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1039
SRC = "架空の通勤と時刻表（作成者が乱数で作成、seed 1039）"
WALK1, WALK_T, WALK2 = 8.0, 2.0, 6.0
RIDE1, RIDE2 = 20.0, 12.0
H1, H2 = 10.0, 10.0       # 発車の間隔（分）
SD1, SD2 = 1.0, 1.0       # 乗っている時間の振れ（標準偏差、分）
N_TT = 1000               # 作り直す時刻表の数
N_TRIP = 2000             # 時刻表1つあたりの通勤の回数
D_BASE = 3.0              # 短くする分


def next_dep(t, offset, h):
    """時刻 t 以後の最初の発車（発車は offset + h の倍数）"""
    return offset + np.ceil((t - offset) / h - 1e-9) * h


def trips(rng, offset2, n, d1=0.0, d2=0.0, h1=H1, h2=H2, sd1=SD1, sd2=SD2):
    """同じ乱数で、短くする前と後の全体の時間を返す（offset2：路線2の発車の位置、0〜h2）"""
    leave = rng.uniform(0, 600, n)
    e1 = rng.normal(0, sd1, n); e2 = rng.normal(0, sd2, n)
    out = []
    for a, b in [(0.0, 0.0), (d1, d2)]:
        dep1 = next_dep(leave + WALK1, 0.0, h1)
        arr_t = dep1 + np.maximum(RIDE1 - a + e1, 1.0) + WALK_T
        dep2 = next_dep(arr_t, offset2, h2)
        arrive = dep2 + np.maximum(RIDE2 - b + e2, 1.0) + WALK2
        out.append(arrive - leave)
    return out[0], out[1]


def run_set(seed, n_tt=N_TT, n=N_TRIP, **kw):
    rng = np.random.default_rng(seed)
    h2 = kw.get("h2", H2)
    offs = rng.uniform(0, h2, n_tt)
    per_tt, all_cut = [], []
    for o in offs:
        b, a = trips(rng, o, n, **kw)
        cut = b - a
        per_tt.append({"offset2": o, "before_mean": b.mean(), "after_mean": a.mean(), "cut_mean": cut.mean(),
                       "share_cut_lt1": (cut < 1).mean(), "share_cut_ge_h2": (cut >= h2 - 0.5).mean()})
        all_cut.append(cut)
    return pd.DataFrame(per_tt), np.concatenate(all_cut)


def summary(df, cut, d, label, value):
    return {"change": label, "value": value, "d": d,
            "cut_mean_all_min": round(float(cut.mean()), 3),
            "trips_cut_lt1_pct": round(float((cut < 1).mean()) * 100, 2),
            "trips_cut_ge9_5_pct": round(float((cut >= 9.5).mean()) * 100, 2),
            "tt_cut_mean_lt1_pct": round(float((df.cut_mean < 1).mean()) * 100, 2),
            "tt_cut_mean_p10": round(float(df.cut_mean.quantile(.1)), 3),
            "tt_cut_mean_p90": round(float(df.cut_mean.quantile(.9)), 3),
            "total_before_mean_min": round(float(df.before_mean.mean()), 3)}


def main():
    # 基本：路線1を3分短く（振れ1分）
    df, cut = run_set(SEED, d1=D_BASE)
    base = summary(df, cut, D_BASE, "基本（路線1を短く）", 3.0)
    df.round(4).to_csv(DATA / "timetables_base.csv", index=False)
    # 路線2（最後の区間）を短くした場合
    df2, cut2 = run_set(SEED + 1, d2=D_BASE)
    last = summary(df2, cut2, D_BASE, "路線2（最後の区間）を短く", 3.0)
    # 振れなしの1つの時刻表の例（路線2の位置ごと）
    grid = np.round(np.arange(0, 10.0, 0.5), 2)
    ex_rows = []
    for o in grid:
        b, a = trips(np.random.default_rng(SEED + 7), o, 4000, d1=D_BASE, sd1=0.0, sd2=0.0)
        ex_rows.append({"offset2": o, "cut_mean_nonoise": round(float((b - a).mean()), 3),
                        "before_mean_nonoise": round(float(b.mean()), 3)})
    ex = pd.DataFrame(ex_rows)
    ex.to_csv(RES / "offset_example_nonoise.csv", index=False)

    # 確かめ
    rows = [base, last]
    for d in [1.0, 5.0, 8.0]:
        dfx, cx = run_set(SEED * 10 + int(d), n_tt=300, n=1500, d1=d)
        rows.append(summary(dfx, cx, d, "短くする分（分）", d))
    for sd in [0.0, 2.0, 4.0]:
        dfx, cx = run_set(SEED * 20 + int(sd), n_tt=300, n=1500, d1=D_BASE, sd1=sd, sd2=sd)
        rows.append(summary(dfx, cx, D_BASE, "乗っている時間の振れ（分）", sd))
    for h2 in [5.0, 15.0, 20.0]:
        dfx, cx = run_set(SEED * 30 + int(h2), n_tt=300, n=1500, d1=D_BASE, h2=h2)
        s = summary(dfx, cx, D_BASE, "路線2の発車の間隔（分）", h2)
        s["trips_cut_ge9_5_pct"] = None
        s["trips_cut_ge_h2_minus_0_5_pct"] = round(float((cx >= h2 - 0.5).mean()) * 100, 2)
        rows.append(s)
    for h1 in [7.0, 15.0]:
        dfx, cx = run_set(SEED * 40 + int(h1), n_tt=300, n=1500, d1=D_BASE, h1=h1)
        rows.append(summary(dfx, cx, D_BASE, "路線1の発車の間隔（分、路線2は10分）", h1))
    sens = pd.DataFrame(rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    # 全体の時間の中の、路線1に乗っている時間の割合（式）
    mean_total = base["total_before_mean_min"]
    share_ride1 = RIDE1 / mean_total
    res = {
        "setup": {"walk_home_station_min": WALK1, "walk_transfer_min": WALK_T, "walk_station_office_min": WALK2,
                  "ride1_min": RIDE1, "ride2_min": RIDE2, "headway1_min": H1, "headway2_min": H2,
                  "ride_sd_min": SD1, "leave_home_window_min": [0, 600], "timetables": N_TT, "trips_per_timetable": N_TRIP, "cut_min": D_BASE},
        "base": base, "last_leg": last,
        "total_before_mean_min": mean_total,
        "ride1_share_of_total_pct": round(share_ride1 * 100, 2),
        "ride1_cut_pct_of_ride": round(D_BASE / RIDE1 * 100, 2),
        "formula_total_cut_pct": round(D_BASE / mean_total * 100, 2),
        "base_tt_cut_mean_range": [round(float(df.cut_mean.min()), 3), round(float(df.cut_mean.max()), 3)],
        "nonoise_offset_cut_values": sorted(set(ex.cut_mean_nonoise.round(2).tolist())),
        "nonoise_share_offsets_zero_pct": round(float((ex.cut_mean_nonoise < 0.5).mean()) * 100, 2),
        "sensitivity": sens.where(sens.notna(), None).to_dict("records"),
        "sens_range_trips_cut_lt1_pct": [float(sens.trips_cut_lt1_pct.min()), float(sens.trips_cut_lt1_pct.max())],
        "sens_range_cut_mean_all_min_d3": [float(sens[sens.d == 3].cut_mean_all_min.min()),
                                           float(sens[sens.d == 3].cut_mean_all_min.max())],
    }
    json.dump(res, open(RES / "a1039_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：振れなしで、路線2の発車の位置ごとの減り方
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.bar(ex.offset2, ex.cut_mean_nonoise, width=0.42, color=[ORANGE if v > 0.5 else LIGHT for v in ex.cut_mean_nonoise])
    ax.axhline(D_BASE, color=INK, lw=1, ls="--"); ax.text(9.9, D_BASE + 0.25, "短くした3分", ha="right", fontsize=9)
    ax.set_xlabel("路線2の発車の位置（毎時0分から何分ずれた時刻に出るか、0.5分きざみ）")
    ax.set_ylabel("全体の時間の減り（分、平均）"); ax.set_ylim(0, 11)
    ax.set_title("振れがないと、3分短くしても全体は0分か10分しか減らない")
    save(fig, "a1039_offset_nonoise.png", SRC, y=-0.05)

    # 図2：1回ごとの減り（基本、振れ1分）と最後の区間を短くした場合
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    bins = np.arange(-1.5, 12.5, 1.0)
    ax.hist(cut, bins=bins, color=BLUE, alpha=.65, density=True, label="路線1（途中の区間）を3分短く")
    ax.hist(cut2, bins=bins, color=ORANGE, alpha=.65, density=True, label="路線2（最後の区間）を3分短く")
    ax.set_xlabel("1回の通勤で減った時間（分）"); ax.set_ylabel("回数の割合"); ax.set_xlim(-2, 12); ax.set_xticks([0, 3, 6, 10])
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"途中の区間を短くすると、{base['trips_cut_lt1_pct']:.0f}%の回は1分も減らなかった")
    save(fig, "a1039_per_trip.png", SRC, y=-0.05)

    # 図3：振れの大きさと、減りが1分未満の回の割合
    sx = sens[sens.change.isin(["乗っている時間の振れ（分）", "基本（路線1を短く）"])].copy()
    sx["sd"] = np.where(sx.change == "基本（路線1を短く）", SD1, sx.value)
    sx = sx.sort_values("sd")
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.plot(sx.sd, sx.trips_cut_lt1_pct, "o-", color=BLUE, label="減りが1分未満の回")
    ax.plot(sx.sd, sx.tt_cut_mean_lt1_pct, "s-", color=ORANGE, label="平均の減りが1分未満の時刻表")
    for x, y in zip(sx.sd, sx.trips_cut_lt1_pct):
        ax.text(x + 0.08, y + 2, f"{y:.1f}%", fontsize=8.5, color=BLUE)
    for x, y in zip(sx.sd, sx.tt_cut_mean_lt1_pct):
        ax.text(x + 0.12, y - 11, f"{y:.1f}%", fontsize=8.5, color=ORANGE,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    ax.set_xlabel("乗っている時間の振れ（標準偏差、分）"); ax.set_ylabel("%"); ax.set_ylim(-15, 100)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("振れが大きいほど、時刻表ごとの差はならされる（路線1を3分短く）")
    save(fig, "a1039_noise.png", SRC, y=-0.05)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
