"""1294 車の台数を重さの上限だけ、または大きさの上限だけで見込むと、両方を守って積んだ台数よりどれだけ少なく出るのか？（架空のデータ）

架空の通販の配送。1台の車には重さの上限1,000kgと荷台の大きさの上限10立方メートルがある。
荷物は2種類：「重くて小さい」（体積の平均0.02立方メートル、重さの平均8kg）と
「軽くて大きい」（体積の平均0.08立方メートル、重さの平均2kg）。
体積と、1立方メートルあたりの重さは、それぞれ対数で正規の分布で散らばる（作成者が置いた）。
その日の荷物は2,000個、来た順はでたらめ。重くて小さい荷物の割合 p を0〜100%で変える。
見込み：重さだけ＝重さの合計÷1,000の切り上げ、大きさだけ＝体積の合計÷10の切り上げ、両方の大きいほう。
本当の台数：来た順に、重さと大きさの両方が収まる車のうち、いちばん先に使い始めた車に積む（車は閉じない）。
形は気にせず、体積の合計だけで荷台に入るかを決める。すべてシミュレーション。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1294
SRC = "架空の通販の配送の積み込みのシミュレーション（作成者が乱数で作成、seed 1294）"
W_CAP, V_CAP = 1000.0, 10.0
N = 2000
TYPES = {"heavy": {"v": 0.02, "w": 8.0}, "light": {"v": 0.08, "w": 2.0}}
SIG_V, SIG_D = 0.5, 0.3
PS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0]
DAYS_BASE = 150
SCALES = [0.5, 1.0, 2.0, 4.0]     # 荷物1つの大きさと重さを何倍にするか（個数は2,000÷倍率）
PS_GRID = [0.3, 0.5, 0.7]
DAYS_GRID = 100


def draw(rng, n, p, scale, sig_v=SIG_V, sig_d=SIG_D):
    heavy = rng.random(n) < p
    vm = np.where(heavy, TYPES["heavy"]["v"], TYPES["light"]["v"]) * scale
    dm = np.where(heavy, TYPES["heavy"]["w"] / TYPES["heavy"]["v"], TYPES["light"]["w"] / TYPES["light"]["v"])
    v = vm * rng.lognormal(-sig_v ** 2 / 2, sig_v, n)
    d = dm * rng.lognormal(-sig_d ** 2 / 2, sig_d, n)
    w = v * d
    # 1台に収まらない荷物は入れない（引き直す）
    bad = (v > V_CAP) | (w > W_CAP)
    if bad.any():
        raise ValueError("too big")
    return v, w, heavy


def pack(v, w):
    """両方の上限を守り、来た順に、収まる車のうちいちばん先に使い始めた車へ"""
    rv = np.full(len(v), V_CAP); rw = np.full(len(v), W_CAP)
    nb = 0
    for a, b in zip(v, w):
        if nb:
            ok = np.nonzero((rv[:nb] >= a - 1e-9) & (rw[:nb] >= b - 1e-9))[0]
            if len(ok):
                k = ok[0]; rv[k] -= a; rw[k] -= b; continue
        rv[nb] -= a; rw[nb] -= b; nb += 1
    return nb, V_CAP - rv[:nb], W_CAP - rw[:nb]


def one_day(rng, p, scale, keep=False):
    n = int(round(N / scale))      # 荷物を大きくしたぶん個数を減らし、車の台数の目安をそろえる
    v, w, h = draw(rng, n, p, scale)
    ew = int(np.ceil(w.sum() / W_CAP - 1e-9)); ev = int(np.ceil(v.sum() / V_CAP - 1e-9))
    nb, lv, lw = pack(v, w)
    r = {"p_heavy": p, "scale": scale, "items": n, "weight_sum": float(w.sum()), "volume_sum": float(v.sum()),
         "est_weight_only": ew, "est_volume_only": ev, "est_both": max(ew, ev), "trucks": nb}
    return (r, lv, lw) if keep else r


def summarize(df):
    t = df.trucks
    return {"trucks_mean": t.mean(),
            "est_weight_only_mean": df.est_weight_only.mean(), "est_volume_only_mean": df.est_volume_only.mean(),
            "est_both_mean": df.est_both.mean(),
            "short_weight_only_pct": (1 - (df.est_weight_only / t).mean()) * 100,
            "short_volume_only_pct": (1 - (df.est_volume_only / t).mean()) * 100,
            "short_both_pct": (1 - (df.est_both / t).mean()) * 100,
            "short_weight_only_trucks": (t - df.est_weight_only).mean(),
            "short_volume_only_trucks": (t - df.est_volume_only).mean(),
            "short_both_trucks": (t - df.est_both).mean(),
            "weight_fill_pct": (df.weight_sum / (t * W_CAP)).mean() * 100,
            "volume_fill_pct": (df.volume_sum / (t * V_CAP)).mean() * 100}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    for p in PS:
        for d in range(DAYS_BASE):
            r = one_day(rng, p, 1.0); r["day"] = d; rows.append(r)
    base = pd.DataFrame(rows)
    bd = base.copy()
    bd["weight_sum"] = bd.weight_sum.round(2); bd["volume_sum"] = bd.volume_sum.round(4)
    bd[["p_heavy", "day", "weight_sum", "volume_sum", "est_weight_only", "est_volume_only", "est_both",
        "trucks"]].to_csv(DATA / "days_base.csv", index=False)
    by_p = []
    for p, g in base.groupby("p_heavy"):
        s = summarize(g); s["p_heavy"] = p; by_p.append(s)
    by_p = pd.DataFrame(by_p)
    cols = ["p_heavy", "trucks_mean", "est_weight_only_mean", "est_volume_only_mean", "est_both_mean",
            "short_weight_only_pct", "short_volume_only_pct", "short_both_pct", "short_weight_only_trucks",
            "short_volume_only_trucks", "short_both_trucks", "weight_fill_pct", "volume_fill_pct"]
    by_p = by_p[cols].round(4)
    for c in [c for c in cols if c.endswith("_pct")]:
        by_p[c] = by_p[c].round(2)
    by_p.to_csv(RES / "base_by_share.csv", index=False)

    # 1日分の例：重くて小さい荷物50%の日の、車ごとの重さと大きさの埋まり方
    r, lv, lw = one_day(np.random.default_rng(SEED + 1), 0.5, 1.0, keep=True)
    ex = pd.DataFrame({"truck": np.arange(1, len(lv) + 1), "volume_fill_pct": (lv / V_CAP * 100).round(2),
                       "weight_fill_pct": (lw / W_CAP * 100).round(2)})
    ex.to_csv(RES / "example_day_p50.csv", index=False)
    ex_info = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}

    # 確かめ：荷物の大きさ（車に対する）×割合
    grid = []
    for sc in SCALES:
        for p in PS_GRID:
            g = pd.DataFrame([one_day(rng, p, sc) for _ in range(DAYS_GRID)])
            s = summarize(g); s.update({"scale": sc, "p_heavy": p}); grid.append(s)
    grid = pd.DataFrame(grid)
    grid["items"] = [int(round(N / sc)) for sc in grid.scale]
    grid = grid[["scale", "items"] + cols].round(4)
    for c in [c for c in cols if c.endswith("_pct")]:
        grid[c] = grid[c].round(2)
    grid.to_csv(RES / "grid.csv", index=False)

    single_min = by_p[["short_weight_only_pct", "short_volume_only_pct"]].max(axis=1)
    main_j = {"settings": {"items_per_day": N, "weight_cap_kg": W_CAP, "volume_cap_m3": V_CAP,
                           "heavy_small": TYPES["heavy"], "light_big": TYPES["light"], "days_per_share": DAYS_BASE},
              "base_p50": by_p[by_p.p_heavy == 0.5].iloc[0].to_dict(),
              "base_p0": by_p[by_p.p_heavy == 0.0].iloc[0].to_dict(),
              "base_p100": by_p[by_p.p_heavy == 1.0].iloc[0].to_dict(),
              "both_short_pct_range_base": [float(by_p.short_both_pct.min()), float(by_p.short_both_pct.max())],
              "worse_single_short_pct_min_base": float(single_min.min()),
              "example_day_p50": ex_info,
              "grid_range": {"short_weight_only_pct": [float(grid.short_weight_only_pct.min()), float(grid.short_weight_only_pct.max())],
                             "short_volume_only_pct": [float(grid.short_volume_only_pct.min()), float(grid.short_volume_only_pct.max())],
                             "short_both_pct": [float(grid.short_both_pct.min()), float(grid.short_both_pct.max())]}}
    with open(RES / "a1294_main.json", "w", encoding="utf-8") as f:
        json.dump(main_j, f, ensure_ascii=False, indent=1)

    # 図1：割合ごとの台数（本当と3つの見込み）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    x = by_p.p_heavy * 100
    ax.plot(x, by_p.trucks_mean, "o-", color=INK, label="両方の上限を守って積んだ台数")
    ax.plot(x, by_p.est_weight_only_mean, "s--", color=ORANGE, label="見込み：重さの上限だけ")
    ax.plot(x, by_p.est_volume_only_mean, "^--", color=BLUE, label="見込み：大きさの上限だけ")
    ax.plot(x, by_p.est_both_mean, ":", color=GREEN, lw=2, label="見込み：2つの見込みの大きいほう")
    ax.set_xlabel("重くて小さい荷物の割合（%）")
    ax.set_ylabel("台数（平均）")
    ax.set_ylim(0, None)
    ax.set_title(f"荷物{N:,}個の日の台数（割合ごとに{DAYS_BASE}日）")
    ax.legend(frameon=False, fontsize=9, loc="lower center")
    save(fig, "a1294_trucks_by_share.png", SRC)

    # 図2：例の日の車ごとの埋まり方
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    w = 0.4
    ax.bar(ex.truck - w / 2, ex.weight_fill_pct, w, color=ORANGE, label="重さの埋まり（%）")
    ax.bar(ex.truck + w / 2, ex.volume_fill_pct, w, color=BLUE, label="大きさの埋まり（%）")
    ax.set_xticks(ex.truck)
    ax.set_xlabel("車（使い始めた順）")
    ax.set_ylabel("上限に対する割合（%）")
    ax.set_ylim(0, 125)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_title("重くて小さい荷物50%の1日：車ごとの埋まり方")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
    save(fig, "a1294_example_day.png", SRC)

    # 図3：重くて小さい荷物50%で、荷物の大きさを変えたときの3つの見込みの足りなさ
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    g = grid[grid.p_heavy == 0.5]
    xs = np.arange(len(SCALES)); w = 0.26
    for i, (c, col, lab) in enumerate([("short_weight_only_pct", ORANGE, "重さの上限だけ"),
                                       ("short_volume_only_pct", BLUE, "大きさの上限だけ"),
                                       ("short_both_pct", GREEN, "2つの見込みの大きいほう")]):
        ax.bar(xs + (i - 1) * w, g[c], w, color=col, label=lab)
        for xx, yy in zip(xs + (i - 1) * w, g[c]):
            ax.text(xx, yy, str(yy), ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(xs, [f"{s}倍（{int(round(N / s)):,}個）" for s in SCALES])
    ax.set_xlabel("荷物1つの大きさと重さ（基本の何倍か）と1日の個数")
    ax.set_ylabel("見込みが本当より少ない割合（%）")
    ax.set_ylim(0, None)
    ax.set_title(f"重くて小さい荷物50%の日の見込みの足りなさ（各{DAYS_GRID}日）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1294_grid_p50.png", SRC)

    print(json.dumps(main_j, ensure_ascii=False, indent=1))
    print(by_p.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
