"""1036 移動の記録の抜け（電波が切れた区間）で、距離はどれだけずれるのか？（架空のデータ）

架空の町（6,000m×6,000m、100mごとの碁盤の目の道）を走る配送の車。
車の場所を決まった間隔（基本5秒）で記録する。記録には場所の誤差（基本 標準偏差5m）があり、
電波の届きにくい区域（町の中ほどの円）では多くの点が抜け、ほかの場所でもときどき続けて抜ける。
本当の走った距離（作成者が置いた道のり）と、記録の点から数えた距離を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1036
SRC = "架空の配送の車の移動の記録（作成者が乱数で作成、seed 1036）"
L, B = 6000.0, 100.0
ZONE, R_ZONE = (3000.0, 3000.0), 900.0
BASE = {"dt": 5, "noise": 5.0, "tau": 20.0, "p_zone": 0.8, "p_start": 0.01, "gap_mean": 6, "stop_p": 0.25, "detour_p": 0.03}
METHODS = ["①点をそのまま結ぶ", "②抜けの区間を数えない", "③抜けを道に沿って埋める", "④③＋止まっている間の点を除く"]


def route(rng, detour_p):
    """碁盤の目の上を、出発点から届け先へ1ブロックずつ進む（ときどき1ブロックの寄り道）"""
    while True:
        a = rng.integers(0, 61, 2)
        b = rng.integers(0, 61, 2)
        if np.abs(a - b).sum() >= 25:
            break
    pts = [a.copy()]
    cur = a.copy()
    while (cur != b).any():
        if rng.random() < detour_p:   # 寄り道：横に1ブロック出て戻る
            d = np.array([0, 1]) if rng.random() < .5 else np.array([1, 0])
            d = d * (1 if rng.random() < .5 else -1)
            nxt = np.clip(cur + d, 0, 60)
            if (nxt != cur).any():
                pts.append(nxt.copy()); pts.append(cur.copy())
        need = b - cur
        axis = [i for i in (0, 1) if need[i] != 0]
        i = axis[rng.integers(len(axis))]
        cur = cur.copy(); cur[i] += np.sign(need[i])
        pts.append(cur.copy())
    return np.array(pts, float) * B


def drive(rng, pts, stop_p):
    """交差点ごとの到着・出発の時刻（秒）。速さは便ごとに毎秒6〜10m、交差点で止まる確率 stop_p（10〜60秒）"""
    v = rng.uniform(6, 10)
    t, ts, xs, ys = 0.0, [0.0], [pts[0, 0]], [pts[0, 1]]
    for k in range(1, len(pts)):
        t += np.hypot(*(pts[k] - pts[k - 1])) / v
        ts.append(t); xs.append(pts[k, 0]); ys.append(pts[k, 1])
        if k < len(pts) - 1 and rng.random() < stop_p:
            t += rng.uniform(10, 60)
            ts.append(t); xs.append(pts[k, 0]); ys.append(pts[k, 1])
    return np.array(ts), np.array(xs), np.array(ys)


def ar_noise(rng, tt, noise, tau):
    """場所の誤差：標準偏差 noise（m）、時間とともにゆっくり変わる（相関の時間 tau 秒、0ならその都度でたらめ）"""
    n = len(tt)
    e = rng.normal(0, 1, (n, 2))
    if tau <= 0 or noise == 0:
        return noise * e[:, 0], noise * e[:, 1]
    out = np.empty((n, 2)); out[0] = e[0]
    rho = np.exp(-np.diff(tt) / tau)
    for k in range(1, n):
        out[k] = rho[k - 1] * out[k - 1] + np.sqrt(1 - rho[k - 1] ** 2) * e[k]
    return noise * out[:, 0], noise * out[:, 1]


def record(rng, ts, xs, ys, dt, noise, p_zone, p_start, gap_mean, tau):
    tt = np.arange(0, ts[-1] + 1e-9, dt)
    if tt[-1] < ts[-1]:
        tt = np.append(tt, ts[-1])
    x, y = np.interp(tt, ts, xs), np.interp(tt, ts, ys)
    n = len(tt)
    lost = np.zeros(n, bool)
    inzone = np.hypot(x - ZONE[0], y - ZONE[1]) <= R_ZONE
    lost |= inzone & (rng.random(n) < p_zone)
    k = 0
    while k < n:
        if not inzone[k] and rng.random() < p_start:
            ln = rng.geometric(1 / gap_mean)
            lost[k:k + ln] = True
            k += ln
        else:
            k += 1
    lost[0] = lost[-1] = False   # 出発と到着の点はある
    nx, ny = ar_noise(rng, tt, noise, tau)
    ex, ey = x + nx, y + ny
    return tt, x, y, ex, ey, lost, inzone


def distances(tt, ex, ey, lost, dt):
    keep = ~lost
    t, x, y = tt[keep], ex[keep], ey[keep]
    dx, dy = np.diff(x), np.diff(y)
    gap = np.diff(t) > dt + 1e-9
    eu = np.hypot(dx, dy)
    man = np.abs(dx) + np.abs(dy)
    d1 = eu.sum()
    d2 = eu[~gap].sum()
    d3 = (np.where(gap, man, eu)).sum()
    spd = eu / np.diff(t)
    slow = (~gap) & (spd < 2.0)          # 毎秒2m未満で動いた区間は止まっている間の揺れと見て除く
    d4 = (np.where(gap, man, np.where(slow, 0, eu))).sum()
    return d1, d2, d3, d4, int(gap.sum())


def trips(seed, n, dt=5, noise=5.0, tau=20.0, p_zone=0.8, p_start=0.01, gap_mean=6, stop_p=0.25, detour_p=0.03, keep_one=False):
    rng = np.random.default_rng(seed)
    rows, one = [], None
    for i in range(n):
        pts = route(rng, detour_p)
        ts, xs, ys = drive(rng, pts, stop_p)
        true = np.hypot(np.diff(xs), np.diff(ys)).sum()
        tt, x, y, ex, ey, lost, inzone = record(rng, ts, xs, ys, dt, noise, p_zone, p_start, gap_mean, tau)
        d1, d2, d3, d4, ng = distances(tt, ex, ey, lost, dt)
        rows.append({"trip": i + 1, "true_m": true, "points": len(tt), "lost_share": lost.mean(),
                     "zone_share": inzone.mean(), "through_zone": bool(inzone.any()), "gaps": ng,
                     "m1": d1, "m2": d2, "m3": d3, "m4": d4, "minutes": ts[-1] / 60})
        if keep_one and one is None and inzone.mean() > 0.15 and lost.mean() > 0.12:
            one = {"ts": ts, "xs": xs, "ys": ys, "tt": tt, "ex": ex, "ey": ey, "lost": lost, "trip": i + 1}
    df = pd.DataFrame(rows)
    for k in ["m1", "m2", "m3", "m4"]:
        df["bias_" + k] = df[k] / df.true_m - 1
    return df, one


def r(x, d=4):
    return round(float(x), d)


def summ(df):
    """全体の合計の比のずれ（%）"""
    return {k: r((df[k].sum() / df.true_m.sum() - 1) * 100, 2) for k in ["m1", "m2", "m3", "m4"]}


def main():
    t0 = time.time()
    df, one = trips(SEED, 500, keep_one=True, **BASE)
    df.round(4).to_csv(DATA / "trips.csv", index=False)
    pd.DataFrame({"t_sec": one["tt"], "x_rec": one["ex"].round(1), "y_rec": one["ey"].round(1),
                  "lost": one["lost"].astype(int)}).to_csv(DATA / "points_example_trip.csv", index=False)

    base = summ(df)
    z, nz = df[df.zone_share > 0.15], df[df.zone_share == 0]
    by_zone = {"zone_trips": int(len(z)), "nozone_trips": int(len(nz)),
               "zone_lost_share": r(z.lost_share.mean() * 100, 2), "nozone_lost_share": r(nz.lost_share.mean() * 100, 2),
               "zone": summ(z), "nozone": summ(nz)}
    by_zone["m1_zone_minus_nozone_pt"] = r(by_zone["zone"]["m1"] - by_zone["nozone"]["m1"], 2)
    by_zone["m4_zone_minus_nozone_pt"] = r(by_zone["zone"]["m4"] - by_zone["nozone"]["m4"], 2)
    per_trip = {k: {"p10": r(df["bias_" + k].quantile(.1) * 100, 2), "p90": r(df["bias_" + k].quantile(.9) * 100, 2),
                    "share_abs_gt5": r((df["bias_" + k].abs() > .05).mean() * 100, 1)} for k in ["m1", "m2", "m3", "m4"]}
    # 点の抜けがないときの記録（誤差と間隔だけの効き）
    rng_chk = []
    for nm, kw in [("抜けなし", dict(BASE, p_zone=0.0, p_start=0.0)),
                   ("抜けなし・誤差なし", dict(BASE, p_zone=0.0, p_start=0.0, noise=0.0)),
                   ("抜けなし・誤差なし・寄り道なし", dict(BASE, p_zone=0.0, p_start=0.0, noise=0.0, detour_p=0.0)),
                   ("誤差なし（抜けは基本）", dict(BASE, noise=0.0)),
                   ("誤差なし・寄り道なし（抜けは基本）", dict(BASE, noise=0.0, detour_p=0.0)),
                   ("止まらない（抜けと誤差は基本）", dict(BASE, stop_p=0.0)),
                   ("誤差がその都度でたらめ（相関の時間0秒）", dict(BASE, tau=0.0)),
                   ("誤差がもっとゆっくり変わる（相関の時間60秒）", dict(BASE, tau=60.0))]:
        d, _ = trips(SEED * 10 + len(rng_chk), 300, **kw)
        rng_chk.append({"case": nm, "lost_share": r(d.lost_share.mean() * 100, 2), **summ(d)})
    checks = pd.DataFrame(rng_chk)
    checks.to_csv(RES / "checks.csv", index=False)

    # 確かめ：記録の間隔 × 場所の誤差 × 抜けの多さ（各200便）
    grid = []
    j = 0
    lost_set = {"少ない": (0.4, 0.003), "基本": (0.8, 0.01), "多い": (0.95, 0.03)}
    for dt in [1, 5, 15, 30]:
        for nz_ in [0.0, 5.0, 15.0]:
            for ln, (pz, ps) in lost_set.items():
                d, _ = trips(SEED * 1000 + j, 200, **dict(BASE, dt=dt, noise=nz_, p_zone=pz, p_start=ps))
                j += 1
                grid.append({"dt_sec": dt, "noise_m": nz_, "lost_level": ln, "lost_share": r(d.lost_share.mean() * 100, 2),
                             **summ(d)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    out = {"base_setting": BASE, "n_trips": 500,
           "constants": {"town_m": L, "block_m": B, "zone_center_m": list(ZONE), "zone_radius_m": R_ZONE,
                         "gap_mean_sec_outside_zone": BASE["gap_mean"] * BASE["dt"], "speed_m_per_s": [6, 10],
                         "stop_sec": [10, 60], "slow_cut_m_per_s": 2.0, "zone_trip_cut_share": 0.15,
                         "min_trip_road_m": 25 * B,
                         "grid_lost_levels_p_zone_p_start": {"少ない": [0.4, 0.003], "基本": [0.8, 0.01], "多い": [0.95, 0.03]}},
           "base": {"true_km_mean": r(df.true_m.mean() / 1000, 3), "minutes_mean": r(df.minutes.mean(), 2),
                    "lost_share": r(df.lost_share.mean() * 100, 2), "trips_through_zone": int(df.through_zone.sum()),
                    "bias_pct_total": base, "per_trip": per_trip},
           "by_zone": by_zone, "checks_300trips": checks.to_dict("records"),
           "grid_summary": {"n": int(len(g)),
                            "m1_min": r(g.m1.min(), 2), "m1_max": r(g.m1.max(), 2),
                            "m2_min": r(g.m2.min(), 2), "m2_max": r(g.m2.max(), 2),
                            "m3_min": r(g.m3.min(), 2), "m3_max": r(g.m3.max(), 2),
                            "m4_min": r(g.m4.min(), 2), "m4_max": r(g.m4.max(), 2),
                            "m1_neg": int((g.m1 < 0).sum()), "m1_pos": int((g.m1 > 0).sum()),
                            "abs_m4_le_abs_m1": int((g.m4.abs() <= g.m1.abs()).sum()),
                            "m4_abs_max": r(g.m4.abs().max(), 2)}}
    json.dump(out, open(RES / "a1036_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1便の例
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.add_patch(Circle(ZONE, R_ZONE, color=LIGHT, alpha=.35, lw=0))
    ax.plot(one["xs"], one["ys"], color=GRAY, lw=2.5, label="本当に走った道")
    keep = ~one["lost"]
    ax.plot(one["ex"][keep], one["ey"][keep], color=BLUE, lw=0.9, marker="o", ms=2.2, label="記録の点を結んだ線（①）")
    ax.scatter(one["ex"][one["lost"]], one["ey"][one["lost"]], s=6, color=ORANGE, label="抜けた点（記録に残らなかった場所）", zorder=3)
    ax.text(ZONE[0], ZONE[1] + R_ZONE + 60, "電波の届きにくい区域", ha="center", fontsize=9, color=BLUE)
    xs_all = np.r_[one["xs"], one["ex"]]; ys_all = np.r_[one["ys"], one["ey"]]
    pad = 300
    ax.set_xlim(xs_all.min() - pad, xs_all.max() + pad); ax.set_ylim(ys_all.min() - pad, ys_all.max() + pad + 150)
    ax.set_aspect("equal"); ax.set_xlabel("東西（m）"); ax.set_ylabel("南北（m）")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.11))
    row = df.iloc[one["trip"] - 1]
    ax.set_title(f"1便の例：本当 {row.true_m/1000:.2f}km、点を結ぶと {row.m1/1000:.2f}km", fontsize=12)
    save(fig, "a1036_example.png", SRC, y=-0.15)

    # 図2：数え方ごとのずれ（区域を通る便・通らない便）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    yy = np.arange(4)[::-1]
    zv = [by_zone["zone"][k] for k in ["m1", "m2", "m3", "m4"]]
    nv = [by_zone["nozone"][k] for k in ["m1", "m2", "m3", "m4"]]
    ax.barh(yy + .18, zv, height=.36, color=ORANGE, label=f"区域を多く通る便（{len(z)}便、点の抜け{by_zone['zone_lost_share']:.1f}%）")
    ax.barh(yy - .18, nv, height=.36, color=BLUE, label=f"区域を通らない便（{len(nz)}便、点の抜け{by_zone['nozone_lost_share']:.1f}%）")
    for a_, v in zip(yy + .18, zv):
        ax.text(v + (0.4 if v >= 0 else -0.4), a_, f"{v:+.2f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    for a_, v in zip(yy - .18, nv):
        ax.text(v + (0.4 if v >= 0 else -0.4), a_, f"{v:+.2f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(yy); ax.set_yticklabels(METHODS, fontsize=9)
    lim = max(map(abs, zv + nv)) * 1.45
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("記録から数えた距離の、本当の距離からのずれ（%、便の合計で）")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.2))
    ax.set_title("同じ記録でも、数え方と抜けの多さで距離のずれは向きまで変わる")
    save(fig, "a1036_methods.png", SRC, y=-0.2)

    # 図3：間隔×誤差（抜けは基本）での①と④
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.8), sharey=True)
    cl = {0.0: GRAY, 5.0: BLUE, 15.0: ORANGE}
    for ax, key, ttl in [(axs[0], "m1", "①点をそのまま結ぶ"), (axs[1], "m4", "④道に沿って埋め、止まっている間を除く")]:
        for nz_, gg in g[g.lost_level == "基本"].groupby("noise_m"):
            ax.plot(gg.dt_sec, gg[key], marker="o", color=cl[nz_], label=f"場所の誤差 {nz_:.0f}m")
        ax.axhline(0, color=INK, lw=.8)
        ax.set_xticks([1, 5, 15, 30]); ax.set_xlabel("記録の間隔（秒）"); ax.set_title(ttl, fontsize=11)
    axs[0].set_ylabel("距離のずれ（%）"); axs[0].legend(frameon=False, fontsize=8)
    fig.suptitle("記録の間隔と場所の誤差で、ずれは上にも下にも動く（抜けは基本、各200便）", fontsize=12, y=1.02)
    save(fig, "a1036_grid.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
