"""805 改善した店の平均は、古い口コミのせいでいつ追いつくのか？（架空のデータ）

架空の店。改善の前は本当の満足度 3.6 で H か月営業し、ある月から本当の満足度が 4.3 に上がる。
口コミは毎月 r 件（ポアソン分布）届き、1件の星は本当の満足度に応じた1〜5の分布から引く。
表示の仕方（全期間の平均・直近12か月の平均・新しい口コミほど重く数える平均）ごとに、
表示が 4.2（新しい満足度より0.1低い線）に届くまでの月数と、届いたあとの振れを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 805
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 805）"
STARS = np.arange(1, 6)
OLD, NEW, LINE, RIVAL = 3.6, 4.3, 4.2, 4.0
AFTER = 240          # 改善のあと何か月まで見るか
REPS = 200


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ作り方）"""
    mu = np.atleast_1d(np.asarray(mu, float))
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def simulate(rng, H=24, r=20, r_after=None, ramp=0, after=AFTER):
    """月ごとの件数と星の合計を返す。index 0..H-1 が改善前、H.. が改善後"""
    r_after = r if r_after is None else r_after
    months = H + after
    true = np.full(months, OLD)
    k = np.arange(after)
    if ramp > 0:
        true[H:] = OLD + (NEW - OLD) * np.minimum((k + 1) / ramp, 1)
    else:
        true[H:] = NEW
    rate = np.where(np.arange(months) < H, r, r_after)
    n = rng.poisson(rate)
    P = star_probs(true)
    cnt = np.array([rng.multinomial(ni, pi) for ni, pi in zip(n, P)])
    s = cnt @ STARS
    return n, s, true


def displays(n, s, H, window=12, half=6):
    """改善後の各月末（1..AFTER か月目）の表示"""
    cn, cs = np.cumsum(n), np.cumsum(s)
    idx = np.arange(H, len(n))                       # 改善後 t か月目の月末 = idx
    cum = cs[idx] / np.maximum(cn[idx], 1)
    def win(L):
        lo = idx - L
        nn = cn[idx] - np.where(lo >= 0, cn[np.maximum(lo, 0)], 0)
        ss = cs[idx] - np.where(lo >= 0, cs[np.maximum(lo, 0)], 0)
        return np.where(nn > 0, ss / np.maximum(nn, 1), np.nan)
    def expw(h):
        out = np.empty(len(idx))
        for j, i in enumerate(idx):
            w = 0.5 ** ((i - np.arange(i + 1)) / h)
            out[j] = (w * s[:i + 1]).sum() / max((w * n[:i + 1]).sum(), 1e-9)
        return out
    return cum, win, expw


def first_month(x, thr):
    hit = np.where(x >= thr)[0]
    return int(hit[0] + 1) if len(hit) else np.nan


def main():
    rng = np.random.default_rng(SEED)

    # 0) 1軒分の例（H=24, r=20）
    n, s, true = simulate(rng, 24, 20)
    cum, win, expw = displays(n, s, 24)
    ex = pd.DataFrame({"month_after": np.arange(1, AFTER + 1), "true": true[24:], "n_month": n[24:],
                       "cumulative": cum, "last12": win(12), "exp_half6": expw(6)})
    pre = pd.DataFrame({"month_after": np.arange(-23, 1), "true": true[:24], "n_month": n[:24]})
    pd.concat([pre, ex], ignore_index=True).to_csv(DATA / "example_shop.csv", index=False, float_format="%.4f")

    # 1) 表示の仕方ごと（H=24、r=5 と r=20）：4.2 に届く月・1/2/5年後の表示・届いたあとの振れ
    methods = {"全期間の平均": ("cum", None), "直近3か月の平均": ("win", 3), "直近6か月の平均": ("win", 6),
               "直近12か月の平均": ("win", 12), "直近24か月の平均": ("win", 24),
               "重み付き（半減6か月）": ("exp", 6), "重み付き（半減12か月）": ("exp", 12)}
    rows = []
    for r in [5, 20]:
        for rep in range(REPS):
            n, s, _ = simulate(np.random.default_rng(SEED * 1000 + rep + r * 100000), 24, r)
            cum, win, expw = displays(n, s, 24)
            for name, (kind, par) in methods.items():
                x = cum if kind == "cum" else (win(par) if kind == "win" else expw(par))
                late = x[36:120]                                   # 37〜120か月目（どの窓も新しい口コミだけ）
                rows.append({"r": r, "rep": rep, "method": name, "first_4_2": first_month(x, LINE),
                             "first_4_0": first_month(x, RIVAL),
                             "at12": x[11], "at24": x[23], "at60": x[59],
                             "late_below_4_2": float(np.nanmean(late < LINE)), "late_sd": float(np.nanstd(late))})
    sim = pd.DataFrame(rows)
    g = sim.groupby(["r", "method"], sort=False)
    summ = pd.DataFrame({
        "first_4_2_median": g.first_4_2.median(), "first_4_2_reached_share": g.first_4_2.apply(lambda v: v.notna().mean()),
        "first_4_0_median": g.first_4_0.median(),
        "at12_mean": g.at12.mean(), "at24_mean": g.at24.mean(), "at60_mean": g.at60.mean(),
        "late_below_4_2_share": g.late_below_4_2.mean(), "late_sd": g.late_sd.mean()}).round(3).reset_index()
    summ.to_csv(RES / "methods_by_rate.csv", index=False)

    # 2) 全期間の平均：改善前の長さ H と毎月の件数 r で、4.2 に届く月は変わるか（理屈では 6H か月）
    grid = []
    for H in [12, 24, 36, 60]:
        for r in [5, 20, 50]:
            fm, f40 = [], []
            for rep in range(REPS):
                n, s, _ = simulate(np.random.default_rng(SEED * 7 + rep + H * 1000 + r * 100000), H, r,
                                   after=max(AFTER, 8 * H))
                cs, cn = np.cumsum(s)[H:], np.cumsum(n)[H:]
                cum = cs / np.maximum(cn, 1)
                fm.append(first_month(cum, LINE)); f40.append(first_month(cum, RIVAL))
            grid.append({"H": H, "r": r, "first_4_2_median": float(np.nanmedian(fm)),
                         "first_4_2_p10": float(np.nanpercentile(fm, 10)), "first_4_2_p90": float(np.nanpercentile(fm, 90)),
                         "first_4_0_median": float(np.nanmedian(f40)),
                         "theory_4_2": round(H * (LINE - OLD) / (NEW - LINE), 1), "theory_4_0": round(H * (RIVAL - OLD) / (NEW - RIVAL), 1)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "cumulative_by_history.csv", index=False)

    # 3) 確かめ：改善のあと客が増えて件数が2倍になる／改善が12か月かけて少しずつ進む
    rob = {}
    for name, kw in {"基本（H=24, r=20）": {}, "改善後に件数が2倍（r=20→40）": {"r_after": 40},
                     "改善が12か月かけて進む": {"ramp": 12}}.items():
        fm, f40, f12 = [], [], []
        for rep in range(REPS):
            n, s, _ = simulate(np.random.default_rng(SEED * 13 + rep), 24, 20, **kw)
            cum, win, _ = displays(n, s, 24)
            fm.append(first_month(cum, LINE)); f40.append(first_month(cum, RIVAL)); f12.append(first_month(win(12), LINE))
        rob[name] = {"cum_first_4_2_median": float(np.nanmedian(fm)), "cum_first_4_0_median": float(np.nanmedian(f40)),
                     "last12_first_4_2_median": float(np.nanmedian(f12))}

    # 4) 確かめ（レビューで追加、乱数なしの理屈の値）：改善の大きさと「追いついた」とみなす線を変えると、
    #    全期間の平均が線に届くまでは改善前の長さの何倍か。倍率 =（線 − 改善前）÷（改善後 − 線）
    #    件数が毎月同じなら、この倍率は件数によらない（2 の表で、数えた値が理屈の値とほぼ一致することを確かめた）
    theory = []
    for gain in [0.3, 0.7, 1.0]:
        for gap in [0.05, 0.1, 0.2]:
            new = round(OLD + gain, 2); line = round(new - gap, 2)
            mult = round((line - OLD) / (new - line), 2)
            theory.append({"old": OLD, "new": new, "gain": gain, "line": line, "gap_below_new": gap,
                           "multiplier_of_H": mult, "years_if_H24": round(24 * mult / 12, 1)})
    theory = pd.DataFrame(theory)
    theory.to_csv(RES / "theory_multiplier.csv", index=False)

    out = {"setting": {"old": OLD, "new": NEW, "line": LINE, "rival": RIVAL, "reps": REPS},
           "methods_H24": summ.to_dict("records"), "cumulative_by_history": grid.to_dict("records"),
           "robustness": rob, "theory_multiplier": theory.to_dict("records"),
           "example_shop": {"first_4_2_cum": first_month(ex.cumulative.values, LINE),
                            "first_4_2_last12": first_month(ex.last12.values, LINE),
                            "cum_at24": round(float(ex.cumulative.iloc[23]), 3),
                            "last12_at24": round(float(ex.last12.iloc[23]), 3)}}
    json.dump(out, open(RES / "a805_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1軒分の例
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    t = ex.month_after.values
    ax.plot(t, ex.true, color=INK, lw=1, ls=":", label="本当の満足度")
    ax.plot(t, ex.cumulative, color=ORANGE, lw=2, label="全期間の平均")
    ax.plot(t, ex.last12, color=BLUE, lw=1.4, label="直近12か月の平均")
    ax.plot(t, ex.exp_half6, color=GREEN, lw=1.4, label="重み付き（半減6か月）")
    ax.axhline(LINE, color=GRAY, lw=0.8, ls="--"); ax.text(242, LINE, "4.2", color=GRAY, fontsize=9, va="center")
    ax.set_xlim(0, 240); ax.set_ylim(3.5, 4.5)
    ax.set_xlabel("改善してからの月数（改善前は24か月、毎月20件ほど）"); ax.set_ylabel("表示される星の平均")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("全期間の平均は、改善のあとも何年も古い口コミに引っぱられる")
    save(fig, "a805_example.png", SRC)

    # 図2：改善前の長さと、全期間の平均が 4.2 に届く月
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for r, c, mk in [(5, LIGHT, "o"), (20, BLUE, "s"), (50, INK, "^")]:
        d = grid[grid.r == r]
        ax.plot(d.H, d.first_4_2_median / 12, marker=mk, color=c, lw=1.4, label=f"毎月{r}件")
    hh = np.array([12, 60])
    ax.plot(hh, hh * 6 / 12, color=ORANGE, ls="--", lw=1, label="理屈の線（改善前の長さ×6）")
    ax.set_xlabel("改善前に営業していた月数"); ax.set_ylabel("4.2に届くまでの年数（中央値）")
    ax.set_xticks([12, 24, 36, 60]); ax.legend(frameon=False, fontsize=9)
    ax.set_title("全期間の平均が追いつく時間は、件数ではなく改善前の長さで決まる")
    save(fig, "a805_history.png", SRC)

    # 図3：速さと振れの引きかえ（毎月5件。全期間の平均は140か月ほどかかるので図の外）
    d = summ[(summ.r == 5) & (summ.method != "全期間の平均")]
    off = {"直近3か月の平均": (6, 4), "直近6か月の平均": (6, 4), "直近12か月の平均": (6, 4),
           "直近24か月の平均": (-10, -14), "重み付き（半減6か月）": (6, 4), "重み付き（半減12か月）": (-40, 8)}
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for _, row in d.iterrows():
        c = GREEN if row.method.startswith("重み") else BLUE
        ax.scatter(row.first_4_2_median, row.late_below_4_2_share * 100, color=c, s=36)
        ax.annotate(row.method, (row.first_4_2_median, row.late_below_4_2_share * 100), xytext=off[row.method],
                    textcoords="offset points", fontsize=8.5, color=c)
    ax.set_xlim(0, 34); ax.set_ylim(0, 32)
    ax.set_xlabel("改善してから4.2に初めて届くまでの月数（中央値）")
    ax.set_ylabel("37〜120か月目に4.2を下回った月の割合（%）")
    ax.set_title("短く区切るほど早く追いつくが、表示は上下に振れる（毎月5件）")
    save(fig, "a805_tradeoff.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
