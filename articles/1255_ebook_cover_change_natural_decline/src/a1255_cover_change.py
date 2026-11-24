"""1255 表紙を変えた前後の売れ方を比べると、発売からの日数で自然に減る分はどうまざるのか？（架空のデータ）

架空の電子書籍。本ごとの1日の売れ方は、発売の直後が高く、日数とともに下がって底（初めの25%）に近づくと置く。
売れ方には数週間続く波（上下）があり、1日に売れた冊数はそのまわりで乱数で振れる。
表紙を変えた日からは、売れ方が作成者の置いた割合（基本は+10%）だけ上がる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1255
SRC = "架空の電子書籍の1日の売れ方（作成者が乱数で作成、seed 1255）"
N_T, N_C = 2000, 4000        # 表紙を変えた本・変えていない本
DAYS = 195
FLOOR = 0.25
WAVE_SD, WAVE_RHO = 0.3, 0.93
C_MIN, C_MAX = 45, 150
DROP = 0.7                   # 「落ちた」とみなす：直近14日が、その前の14日の7割を下回る
METHODS = {"m1": "① 前後をそのまま比べる", "m2": "② 変えていない本（同じ日数）と比べる",
           "m3": "③ 前の減り方を延ばして見込む", "m4": "④ 同じ決まりで日を選んだ変えていない本と比べる"}


def make_books(rng, n, tau_med, wave_sd=WAVE_SD):
    L = 3.0 * np.exp(rng.normal(0, 0.8, n))
    tau = tau_med * np.exp(rng.normal(0, 0.3, n))
    t = np.arange(DAYS)
    base = L[:, None] * (FLOOR + (1 - FLOOR) * np.exp(-t[None, :] / tau[:, None]))
    z = np.zeros((n, DAYS))
    z[:, 0] = rng.normal(0, wave_sd, n)
    e = rng.normal(0, wave_sd * np.sqrt(1 - WAVE_RHO ** 2), (n, DAYS))
    for d in range(1, DAYS):
        z[:, d] = WAVE_RHO * z[:, d - 1] + e[:, d]
    lam = base * np.exp(z - wave_sd ** 2 / 2)
    return L, tau, lam


def pick_day(rng, sales, rule):
    n = sales.shape[0]
    if rule == "fixed":
        return rng.integers(C_MIN, C_MAX + 1, n)
    cs = np.cumsum(np.pad(sales, ((0, 0), (1, 0))), axis=1)
    c = np.full(n, -1)
    for d in range(C_MIN, C_MAX + 1):
        last = cs[:, d] - cs[:, d - 14]
        prev = cs[:, d - 14] - cs[:, d - 28]
        hit = (c < 0) & (last < DROP * prev)
        c[hit] = d
    return c


def win_sums(sales, c, w):
    idx = np.arange(sales.shape[0])
    cs = np.cumsum(np.pad(sales, ((0, 0), (1, 0))), axis=1)
    return cs[idx, c] - cs[idx, c - w], cs[idx, c + w] - cs[idx, c]


def aligned(sales, c, w):
    rel = np.arange(-w, w)
    return rel, sales[np.arange(len(c))[:, None], c[:, None] + rel[None, :]].sum(0)


def run(rng, tau_med, rule, effect, w, keep=False, wave_sd=WAVE_SD):
    Lt, taut, lamt = make_books(rng, N_T, tau_med, wave_sd)
    Lc, tauc, lamc = make_books(rng, N_C, tau_med, wave_sd)
    # 表紙を変える日は、変える前の売れ方（効き目のない売れ方）を見て決める
    pre_t = rng.poisson(lamt)
    ct = pick_day(rng, pre_t, rule)
    ok = ct >= 0
    lam_eff = lamt.copy()
    for i in np.where(ok)[0]:
        lam_eff[i, ct[i]:] *= 1 + effect
    # 変える日より前は同じ乱数の冊数、後ろは効き目を入れて引き直す
    post = rng.poisson(lam_eff)
    mask = np.arange(DAYS)[None, :] >= np.where(ok, ct, DAYS)[:, None]
    st = np.where(mask, post, pre_t)[ok]
    ct = ct[ok]
    sc = rng.poisson(lamc)
    b, a = win_sums(st, ct, w)
    m1 = a.sum() / b.sum() - 1
    # ② 変えた本1冊ごとに、変えていない本をでたらめに1冊選び、同じ日数の前後を比べる
    j = rng.integers(0, N_C, len(ct))
    cb, ca = win_sums(sc[j], ct, w)
    m2 = (a.sum() / b.sum()) / (ca.sum() / cb.sum()) - 1
    # ③ 変えた本を変えた日でそろえて足し、前の w 日の対数の直線を延ばす
    rel, agg = aligned(st, ct, w)
    bef = rel < 0
    coef = np.polyfit(rel[bef], np.log(agg[bef]), 1)
    pred = np.exp(np.polyval(coef, rel[~bef]))
    m3 = agg[~bef].sum() / pred.sum() - 1
    # ④ 変えていない本にも同じ決まりで日を選び、その日の前後を比べる
    cc = pick_day(rng, sc, rule)
    okc = cc >= 0
    cb4, ca4 = win_sums(sc[okc], cc[okc], w)
    m4 = (a.sum() / b.sum()) / (ca4.sum() / cb4.sum()) - 1
    natural = (ca.sum() / cb.sum()) - 1     # 変えていない本の同じ日数の前後（自然に減る分）
    out = {"tau": tau_med, "rule": rule, "effect": effect, "window": w, "n_changed": int(ok.sum()),
           "change_day_median": float(np.median(ct)), "decay_days_median": round(float(np.median(taut[ok])), 2),
           "wave_sd": wave_sd,
           "m1": round(float(m1), 4), "m2": round(float(m2), 4), "m3": round(float(m3), 4), "m4": round(float(m4), 4),
           "control_same_days": round(float(natural), 4),
           "share_books_down_m1": round(float((a < b).mean()), 4)}
    if keep:
        out["_books"] = pd.DataFrame({"book_id": np.arange(1, ok.sum() + 1), "first_level": Lt[ok].round(4),
                                      "decay_days": taut[ok].round(2), "change_day": ct,
                                      "sold_before": b, "sold_after": a})
        cagg = aligned(sc[j], ct, w)[1]
        out["_agg"] = pd.DataFrame({"rel_day": rel, "changed_books": agg, "unchanged_same_days": cagg,
                                    "line_from_before": np.r_[np.full(bef.sum(), np.nan), pred].round(2)})
    return out


def main():
    t0 = time.time()
    rows, keep = [], {}
    gi = 0
    for tau in [20, 40, 80]:
        for rule in ["fixed", "drop"]:
            for eff in [0.0, 0.10]:
                for w in [14, 28, 42]:
                    rng = np.random.default_rng(SEED * 1000 + gi)
                    gi += 1
                    base = (tau == 40 and w == 28)
                    r = run(rng, tau, rule, eff, w, keep=base)
                    if base:
                        keep[(rule, eff)] = (r.pop("_books"), r.pop("_agg"))
                    rows.append(r)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    base = grid[(grid.tau == 40) & (grid.window == 28)].reset_index(drop=True)
    base.to_csv(RES / "base_methods.csv", index=False)

    keep[("fixed", 0.10)][0].to_csv(DATA / "books_fixed_day.csv", index=False)
    keep[("drop", 0.10)][0].to_csv(DATA / "books_after_drop.csv", index=False)
    keep[("fixed", 0.10)][1].to_csv(RES / "aligned_fixed_day.csv", index=False)
    keep[("drop", 0.10)][1].to_csv(RES / "aligned_after_drop.csv", index=False)

    # 確かめのまとめ（効き目+10%、18通り）
    g10 = grid[grid.effect == 0.10]
    g0 = grid[grid.effect == 0.0]
    summ = {}
    for rule in ["fixed", "drop"]:
        for nm, g in [("eff10", g10), ("eff0", g0)]:
            s = g[g.rule == rule]
            summ[f"{rule}_{nm}"] = {m: [float(s[m].min()), float(s[m].max())] for m in ["m1", "m2", "m3", "m4", "control_same_days"]}
            summ[f"{rule}_{nm}"]["n_m1_below_zero"] = int((s.m1 < 0).sum())
            summ[f"{rule}_{nm}"]["n"] = int(len(s))
    within = {}
    for nm, g in [("eff10", g10), ("eff0", g0)]:
        e = g.effect.iloc[0]
        for m in ["m1", "m2", "m3", "m4"]:
            within[f"{nm}_{m}_within_3pt"] = int(((g[m] - e).abs() <= 0.03).sum())
    # しくみを分ける：波を0にした「落ちた日に変える」（効き目+10%、0%）
    parts = []
    for k, eff in enumerate([0.10, 0.0]):
        r = run(np.random.default_rng(SEED * 7 + k), 40, "drop", eff, 28, wave_sd=0.0)
        parts.append(r)
    parts = pd.DataFrame(parts)
    parts.to_csv(RES / "no_wave_check.csv", index=False)
    main_json = {"no_wave_check": parts.to_dict("records"), "setup": {"n_changed": N_T, "n_unchanged": N_C, "days": DAYS, "floor": FLOOR,
                           "wave_sd": WAVE_SD, "wave_rho": WAVE_RHO, "change_day_range": [C_MIN, C_MAX], "drop_rule": DROP},
                 "methods": METHODS, "base": base.to_dict("records"), "grid_summary": summ, "within_3pt_of_true": within}
    with open(RES / "a1255_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：変えた日でそろえた売れ方（決めた日に変える、効き目+10%）
    for key, fname, ttl in [(("fixed", 0.10), "a1255_aligned_fixed.png", "決めた日に変えた2,000冊"),
                            (("drop", 0.10), "a1255_aligned_drop.png", "売れ方が落ちた日に変えた本")]:
        agg = keep[key][1]
        n = len(keep[key][0])
        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        ax.plot(agg.rel_day, agg.changed_books / n, color=BLUE, label="表紙を変えた本（1冊あたり）")
        ax.plot(agg.rel_day, agg.unchanged_same_days / n, color=GRAY, label="変えていない本（同じ発売からの日数）")
        ax.plot(agg.rel_day, agg.line_from_before / n, color=ORANGE, ls="--", label="前の28日の減り方を延ばした線")
        ax.axvline(0, color=INK, lw=0.8)
        ax.set_ylim(0, None)
        ax.set_xlabel("表紙を変えた日からの日数")
        ax.set_ylabel("1日に売れた冊数（1冊あたりの平均）")
        ax.set_title(f"{ttl}：変えた日でそろえた売れ方（本当の効き目+10%）")
        ax.legend(frameon=False, fontsize=9, loc="lower left")
        save(fig, fname, SRC + "。発売からの日数45〜150日目に変えた")

    # 図3：基本の置き方での4つの読み方
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
    for ax, eff, ttl in zip(axs, [0.10, 0.0], ["本当の効き目 +10%", "本当の効き目 0%"]):
        s = base[base.effect == eff].set_index("rule")
        x = np.arange(4)
        for k, (rule, c, lab) in enumerate([("fixed", BLUE, "決めた日に変える"), ("drop", ORANGE, "落ちた日に変える")]):
            v = [s.loc[rule, m] * 100 for m in ["m1", "m2", "m3", "m4"]]
            bars = ax.bar(x + (k - 0.5) * 0.38, v, 0.38, color=c, label=lab)
            for bb, vv in zip(bars, v):
                ax.text(bb.get_x() + bb.get_width() / 2, vv + (1 if vv >= 0 else -1), f"{vv:+.2f}",
                        ha="center", va="bottom" if vv >= 0 else "top", fontsize=7.5)
        ax.axhline(eff * 100, color=INK, ls="--", lw=1)
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(["①そのまま", "②変えていない\n本と比べる", "③前の減り方\nを延ばす", "④同じ決まりの\n本と比べる"], fontsize=9)
        ax.set_title(f"{ttl}（破線）")
    axs[0].set_ylabel("読み取った効き目（%）")
    axs[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.suptitle("前後28日ずつの読み方ごとの効き目（減り方の日数の中央値40日）", y=1.02)
    save(fig, "a1255_methods.png", SRC)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
