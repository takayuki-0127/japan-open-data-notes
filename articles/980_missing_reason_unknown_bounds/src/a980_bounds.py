"""980 欠けている理由が分からないとき、何まで言えるのか？（架空のデータ）

架空の店の会員2,000人に「また来たいか」を聞き、答えたのは6割。答えた人のデータはどの世界でも同じで、
答えなかった人の「また来たい」の割合だけが違う4つの世界を作成者が置く。
答えた人だけの割合・何も仮定しない幅・「答えなかった人は最大 δ 違う」と置いた幅・答えなかった人の一部への聞き直しで、
本当の割合をどれだけ言い当てられるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 980
SRC = "架空の店の会員アンケート（作成者が乱数で作成、seed 980）"
Z95 = 1.959964
N, R, P = 2000, 0.60, 0.70
WORLDS = [("同じ（でたらめに欠けた）", 0.0), ("15ポイント低い", -0.15), ("30ポイント低い", -0.30), ("10ポイント高い", 0.10)]
DELTAS = [0.1, 0.2, 0.3]
FOLLOW = [30, 100, 300]


def sim(rng, reps, n, r, p, d, follow=FOLLOW):
    """回ごとの数：答えた人数・答えた人の「また来たい」・答えなかった人の「また来たい」・聞き直しの数"""
    nr = rng.binomial(n, r, reps)
    sr = rng.binomial(nr, p)
    nn = n - nr
    sn = rng.binomial(nn, min(max(p + d, 0), 1))
    fu = {}
    for k in follow:
        kk = np.minimum(k, nn)
        fu[k] = (kk, rng.hypergeometric(sn, nn - sn, np.maximum(kk, 1)) * (kk > 0))
    return nr, sr, nn, sn, fu


def evaluate(n, nr, sr, nn, sn, fu):
    truth = (sr + sn) / n
    rh, ph = nr / n, sr / nr
    se = np.sqrt(ph * (1 - ph) / nr)
    out = {"truth": truth.mean() * 100, "naive_est": ph.mean() * 100,
           "naive_cover": (np.abs(ph - truth) <= Z95 * se).mean() * 100,
           "naive_width": (2 * Z95 * se).mean() * 100}
    lo, hi = sr / n, (sr + nn) / n
    out["bound_cover"] = ((truth >= lo - 1e-12) & (truth <= hi + 1e-12)).mean() * 100
    out["bound_width"] = (hi - lo).mean() * 100
    out["bound_lo"], out["bound_hi"] = lo.mean() * 100, hi.mean() * 100
    for dl in DELTAS:
        l = (sr + nn * np.clip(ph - dl, 0, 1)) / n
        h = (sr + nn * np.clip(ph + dl, 0, 1)) / n
        out[f"delta{dl}_cover"] = ((truth >= l - 1e-12) & (truth <= h + 1e-12)).mean() * 100
        out[f"delta{dl}_width"] = (h - l).mean() * 100
    for k, (kk, x) in fu.items():
        qh = x / kk
        est = (sr + nn * qh) / n
        fpc = np.clip(1 - kk / nn, 0, 1)
        sef = nn / n * np.sqrt(qh * (1 - qh) / kk * fpc)
        sef = np.where(sef > 0, sef, nn / n * np.sqrt(0.25 / kk * fpc))   # 聞き直しが全員同じ答えだったとき
        out[f"follow{k}_cover"] = (np.abs(est - truth) <= Z95 * sef + 1e-12).mean() * 100
        out[f"follow{k}_width"] = (2 * Z95 * sef).mean() * 100
        out[f"follow{k}_bias"] = (est - truth).mean() * 100
    return out


def main():
    rng = np.random.default_rng(SEED)

    # 1回分（data/members.csv）：答えた人は全世界で同じ、答えなかった人の本当の答えだけ世界ごとに違う
    r1 = np.random.default_rng(SEED)
    resp = r1.random(N) < R
    ans = np.where(resp, (r1.random(N) < P).astype(float), np.nan)
    df = pd.DataFrame({"member_id": np.arange(1, N + 1), "responded": resp.astype(int), "answer": ans})
    u = r1.random(N)
    nonr_idx = np.flatnonzero(~resp)
    fsel = np.zeros(N, int); fsel[r1.choice(nonr_idx, 100, replace=False)] = 1
    tw = {}
    for (name, d), col in zip(WORLDS, ["true_same", "true_minus15", "true_minus30", "true_plus10"]):
        y = np.where(resp, ans, (u < P + d).astype(float))   # 同じ乱数 u で、答えなかった人だけ置き方を変える
        df[col] = y.astype(int)
        tw[name] = round(float(y.mean() * 100), 2)
    df["followup_100"] = fsel
    df.to_csv(DATA / "members.csv", index=False)
    nr1, sr1 = int(resp.sum()), int(np.nansum(ans))
    rh, ph = nr1 / N, sr1 / nr1
    one = {"n": N, "respondents": nr1, "yes_respondents": sr1, "share_respondents": round(ph * 100, 2),
           "bound": [round(sr1 / N * 100, 2), round((sr1 + N - nr1) / N * 100, 2)],
           "truth_by_world": tw,
           # 「半分以上がまた来たい」が崩れるのは、答えなかった人の割合がこれを下回るとき（式）
           "tipping_nonresp_share_for_50": round((0.5 - sr1 / N) / (1 - rh) * 100, 2),
           "tipping_gap_points": round(ph * 100 - (0.5 - sr1 / N) / (1 - rh) * 100, 2)}

    # 2) 基本（答えた人60%）、4つの世界、各2,000回
    rows = []
    for name, d in WORLDS:
        nr, sr, nn, sn, fu = sim(rng, 2000, N, R, P, d)
        rows.append({"world": name, "d": d, **{k: round(float(v), 3) for k, v in evaluate(N, nr, sr, nn, sn, fu).items()}})
    base = pd.DataFrame(rows)
    base.to_csv(RES / "worlds_base.csv", index=False)

    # 3) 確かめ：答えた人の割合 40%・60%・80%、各世界2,000回
    grid = []
    for r in [0.4, 0.6, 0.8]:
        for name, d in WORLDS:
            nr, sr, nn, sn, fu = sim(np.random.default_rng(SEED * 10 + int(r * 10) * 7 + int((d + 1) * 100)), 2000, N, r, P, d)
            e = evaluate(N, nr, sr, nn, sn, fu)
            grid.append({"response_rate": r, "world": name, "d": d,
                         **{k: round(float(e[k]), 3) for k in ["truth", "naive_cover", "bound_width", "delta0.2_width",
                                                              "delta0.2_cover", "follow100_cover", "follow100_width"]}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_response_rate.csv", index=False)

    # 4) 2店の比べ方：A店（答えた人70%・答えた人の72%）とB店（50%・64%）、答えなかった人の置き方4×4、各2,000回
    two = []
    NA = NB = 1500
    for na, da in WORLDS:
        for nb, db in WORLDS:
            g = np.random.default_rng(SEED * 1000 + int((da + 1) * 100) * 3 + int((db + 1) * 100))
            a = sim(g, 2000, NA, 0.70, 0.72, da, follow=[])
            b = sim(g, 2000, NB, 0.50, 0.64, db, follow=[])
            ta, tb = (a[1] + a[3]) / NA, (b[1] + b[3]) / NB
            oa, ob = a[1] / a[0], b[1] / b[0]
            two.append({"A_world": na, "B_world": nb, "dA": da, "dB": db,
                        "obs_diff": round(float((oa - ob).mean() * 100), 3),
                        "true_diff": round(float((ta - tb).mean() * 100), 3),
                        "share_reps_true_A_gt_B": round(float((ta > tb).mean() * 100), 2)})
    two = pd.DataFrame(two)
    two.to_csv(RES / "two_stores.csv", index=False)
    # 式：差の幅（何も仮定しない）と、両店で逆向きに δ ずれたときに差が0になる δ
    rA, pA, rB, pB = 0.70, 0.72, 0.50, 0.64
    two_formula = {"obs_diff": round((pA - pB) * 100, 2),
                   "no_assumption_diff_bound": [round((rA * pA - (rB * pB + (1 - rB))) * 100, 2),
                                                round((rA * pA + (1 - rA) - rB * pB) * 100, 2)],
                   "tipping_delta_points": round((pA - pB) / ((1 - rA) + (1 - rB)) * 100, 2)}

    out = {"one_draw": one, "base_2000reps": base.set_index("world").to_dict("index"),
           "two_stores": {"formula": two_formula, "combos": len(two),
                          "combos_true_A_gt_B": int((two.true_diff > 0).sum()),
                          "true_diff_range": [float(two.true_diff.min()), float(two.true_diff.max())],
                          "obs_diff_range": [float(two.obs_diff.min()), float(two.obs_diff.max())]},
           "grid": {"naive_cover_range": [float(grid.naive_cover.min()), float(grid.naive_cover.max())],
                    "follow100_cover_range": [float(grid.follow100_cover.min()), float(grid.follow100_cover.max())],
                    "bound_width_by_rate": {str(r): float(grid[grid.response_rate == r].bound_width.mean()) for r in [0.4, 0.6, 0.8]}}}
    json.dump(out, open(RES / "a980_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：答えた人の割合はどの世界でも同じ。本当の割合と、何も仮定しない幅
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    names = [w[0] for w in WORLDS]
    ys = np.arange(4)[::-1]
    ax.axvspan(one["bound"][0], one["bound"][1], color=LIGHT, alpha=.45, lw=0)
    ax.text((one["bound"][0] + one["bound"][1]) / 2, 3.62, f"何も仮定しない幅 {one['bound'][0]:.1f}〜{one['bound'][1]:.1f}%",
            ha="center", fontsize=9, color=INK)
    ax.axvline(one["share_respondents"], color=ORANGE, lw=1.5, ls="--")
    ax.text(one["share_respondents"] + 0.6, -0.62, f"答えた人の割合 {one['share_respondents']:.1f}%（4つの世界で同じ）",
            color=ORANGE, fontsize=9)
    for yy, nm in zip(ys, names):
        ax.plot(tw[nm], yy, "o", color=INK, ms=8)
        ax.text(tw[nm] + 0.8, yy + 0.12, f"本当 {tw[nm]:.1f}%", fontsize=9)
    ax.set_yticks(ys); ax.set_yticklabels([f"答えなかった人が\n{n}" for n in names], fontsize=8.5)
    ax.set_xlim(35, 90); ax.set_ylim(-0.9, 3.9)
    ax.set_xlabel("「また来たい」の割合（%）")
    ax.set_title("答えたデータが同じでも、本当の割合は世界ごとに違う（1回分）", fontsize=11)
    save(fig, "a980_worlds.png", SRC)

    # 図2：4つの世界で、本当の割合が幅に入った割合
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    meths = [("naive_cover", "答えた人だけの95%の幅", GRAY), ("delta0.1_cover", "最大10ポイント違うと置いた幅", LIGHT),
             ("delta0.2_cover", "最大20ポイント違うと置いた幅", BLUE), ("follow100_cover", "答えなかった100人に聞き直した95%の幅", GREEN),
             ("bound_cover", "何も仮定しない幅", INK)]
    xs = np.arange(4); wd = 0.16
    for i, (k, lb, c) in enumerate(meths):
        ax.bar(xs + (i - 2) * wd, base[k], wd, color=c, label=lb)
    ax.set_xticks(xs); ax.set_xticklabels([f"答えなかった人が\n{n}" for n in names], fontsize=8.5)
    ax.set_ylabel("本当の割合が幅に入った回（%）"); ax.set_ylim(0, 105)
    ax.axhline(95, color=ORANGE, lw=.8, ls=":")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("答えた人だけの幅が当たるのは、欠け方がでたらめな世界だけ（各2,000回）", fontsize=11)
    save(fig, "a980_cover.png", SRC, y=-0.21)

    # 図3：2店の本当の差（答えなかった人の置き方4×4）
    mat = two.pivot(index="A_world", columns="B_world", values="true_diff").loc[names, names]
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    vmax = np.abs(mat.values).max()
    im = ax.imshow(mat.values, cmap="RdBu", vmin=-vmax, vmax=vmax)
    for i in range(4):
        for j in range(4):
            v = mat.values[i, j]
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(v) > vmax * .6 else INK)
    short = ["同じ", "15ポイント\n低い", "30ポイント\n低い", "10ポイント\n高い"]
    ax.set_xticks(range(4)); ax.set_xticklabels(short, fontsize=8.5)
    ax.set_yticks(range(4)); ax.set_yticklabels([x.replace("\n", "") for x in short], fontsize=8.5)
    ax.set_xlabel("B店の答えなかった人の割合（答えた人と比べて）", fontsize=9.5)
    ax.set_ylabel("A店の答えなかった人の割合（答えた人と比べて）", fontsize=9.5)
    ax.spines[:].set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=.8); cb.set_label("本当の差 A店−B店（ポイント）")
    ax.set_title(f"答えた人では A店が{two_formula['obs_diff']:.0f}ポイント上。本当の差は答えなかった人しだい", fontsize=11)
    save(fig, "a980_two_stores.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
