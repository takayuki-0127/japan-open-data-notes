"""1207 一部の読者に試しに送った結果は、残りの読者に送ったときの数字にどれだけ当たるのか？（架空のデータ）

作成者が置いた架空の会員向けのお知らせメール。読者20,000人。
登録してからの日数 t は0〜1,094日（一様）。1人ひとりの開く確率は、対数オッズの尺度で
  c0 − b×log(1＋t/30) ＋ u ＋ δ（u は人ごとの差：平均0・標準偏差0.8、δ は送った日の開かれやすさ：平均0・標準偏差 σ）
（基本 c0＝0.3、b＝0.5、σ＝0.15）。開いた人がリンクを押す確率は、対数オッズで −1.7＋0.5×w（w は人ごとの差、標準偏差1）。
1通の配信で、一部（基本10%）に先に送り（試しの日）、別の日に残りへ送る。試しの日と残りの日の δ は別々に引く。
どちらも同じ日数で締め、開いたか・押したかだけを数える（締めの日数は扱わない）。
試しの読者の選び方：① でたらめ ② 名簿の先頭から（登録の古い順） ③ 名簿の末尾から（登録の新しい順） ④ アドレスの文字順の先頭から
（アドレスの文字は登録の日数と関係ないと置く）。
(1) 選び方4通り×試しの割合5通り（2・5・10・20・50%）、送った日の振れは基本で、各500回
(2) 送った日の振れ σ を0・0.15・0.3、でたらめな選び方で、試しの割合5通り（各500回）
(3) 確かめ：σ 3通り×登録の日数の効き b 3通り（0・0.5・1）×試しの割合3通り（5・10・20%）×選び方2通り（でたらめ・古い順）＝54通り（各200回）
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1207
SRC = "架空の会員向けのお知らせメール（作成者が置いた開く確率・送った日の振れからの乱数、seed 1207）"
M = 20000
C0, B, SD_U, SIG = 0.3, 0.5, 0.8, 0.15
FRACS = [0.02, 0.05, 0.10, 0.20, 0.50]
SELS = ["① でたらめ", "② 名簿の先頭（登録の古い順）", "③ 名簿の末尾（登録の新しい順）", "④ アドレスの文字順の先頭"]
R_MAIN, R_GRID = 250, 60
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def expit(x):
    return 1 / (1 + np.exp(-x))


def one_run(rng, frac=0.10, sel=0, sig=SIG, b=B, keep=False):
    t = rng.integers(0, 1095, M)
    u = rng.normal(0, SD_U, M)
    w = rng.standard_normal(M)
    addr_key = rng.random(M)            # アドレスの文字順（登録の日数と関係ない）
    base = C0 - b * np.log1p(t / 30) + u
    n_p = int(round(M * frac))
    if sel == 0:
        order = rng.permutation(M)
    elif sel == 1:
        order = np.argsort(-t, kind="stable")
    elif sel == 2:
        order = np.argsort(t, kind="stable")
    else:
        order = np.argsort(addr_key, kind="stable")
    pilot = np.zeros(M, bool)
    pilot[order[:n_p]] = True
    d_p, d_r = rng.normal(0, sig, 2) if sig > 0 else (0.0, 0.0)
    p_open = expit(base + np.where(pilot, d_p, d_r))
    opened = rng.random(M) < p_open
    clicked = opened & (rng.random(M) < expit(-1.7 + 0.5 * w))
    po, ro = opened[pilot].mean(), opened[~pilot].mean()
    pc, rc = clicked[pilot].mean(), clicked[~pilot].mean()
    se = np.sqrt(po * (1 - po) / n_p)
    sec = np.sqrt(pc * (1 - pc) / n_p)
    res = {"pilot_open": po, "rest_open": ro, "pilot_click": pc, "rest_click": rc,
           "err_open": po - ro, "err_click": pc - rc,
           "relerr_open": (po - ro) / ro, "relerr_click": (pc - rc) / rc,
           "cover_open": abs(po - ro) <= 1.96 * se, "cover_click": abs(pc - rc) <= 1.96 * sec,
           "all_open_prob_no_day": expit(base).mean()}
    if keep:
        res["table"] = pd.DataFrame({"reader_id": np.arange(1, M + 1), "days_since_signup": t, "pilot": pilot.astype(int),
                                     "opened": opened.astype(int), "clicked": clicked.astype(int)})
    return res


def agg(xs, extra):
    df = pd.DataFrame(xs)
    out = dict(extra)
    out.update({
        "pilot_open": r(df.pilot_open.mean()), "rest_open": r(df.rest_open.mean()),
        "mean_err_open_pt": r(df.err_open.mean() * 100), "mean_abs_err_open_pt": r(df.err_open.abs().mean() * 100),
        "mean_abs_relerr_open_pct": r(df.relerr_open.abs().mean() * 100, 2),
        "share_relerr_open_over10_pct": r((df.relerr_open.abs() > 0.10).mean() * 100, 2),
        "cover95_open_pct": r(df.cover_open.mean() * 100, 2),
        "pilot_click": r(df.pilot_click.mean()), "rest_click": r(df.rest_click.mean()),
        "mean_err_click_pt": r(df.err_click.mean() * 100), "mean_abs_err_click_pt": r(df.err_click.abs().mean() * 100),
        "mean_abs_relerr_click_pct": r(df.relerr_click.abs().mean() * 100, 2),
        "share_relerr_click_over10_pct": r((df.relerr_click.abs() > 0.10).mean() * 100, 2),
        "cover95_click_pct": r(df.cover_click.mean() * 100, 2),
    })
    return out


def main():
    rng = np.random.default_rng(SEED)
    ex = one_run(np.random.default_rng(SEED + 1), keep=True)
    ex["table"].to_csv(DATA / "readers_example.csv", index=False)
    ex_s = {k: (r(v) if not isinstance(v, (bool, np.bool_)) else bool(v)) for k, v in ex.items() if k != "table"}

    rows = []
    for si, sname in enumerate(SELS):
        for fr in FRACS:
            rows.append(agg([one_run(rng, fr, si) for _ in range(R_MAIN)], {"selection": sname, "pilot_share": fr}))
    main_t = pd.DataFrame(rows)
    main_t.to_csv(RES / "by_selection.csv", index=False)

    rows = []
    for sig in [0.0, 0.15, 0.3]:
        for fr in FRACS:
            if sig == SIG:   # 基本の振れは (1) のでたらめの行をそのまま使う
                row = {"day_sd": sig, "pilot_share": fr}
                row.update({k: v for k, v in main_t[(main_t.selection == SELS[0]) & (main_t.pilot_share == fr)].iloc[0].items()
                            if k not in ("selection", "pilot_share")})
            else:
                row = agg([one_run(rng, fr, 0, sig) for _ in range(R_MAIN)], {"day_sd": sig, "pilot_share": fr})
            # 式：差の標準偏差 ≒ √(p(1−p)(1/n1＋1/n2) ＋ 2σ²(p(1−p))²)（送った日の振れは対数オッズの尺度を開封率に直した近似）
            p = row["rest_open"]
            n1 = M * fr
            v_s = p * (1 - p) * (1 / n1 + 1 / (M - n1))
            v_d = 2 * (sig * p * (1 - p)) ** 2
            row["formula_abs_err_open_pt"] = r(np.sqrt(v_s + v_d) * np.sqrt(2 / np.pi) * 100)
            # 式：試しだけの幅（±1.96×√(p(1−p)/n1)）に入る割合
            zc = 1.96 * np.sqrt(p * (1 - p) / n1) / np.sqrt(v_s + v_d)
            row["formula_cover95_open_pct"] = r(math.erf(zc / math.sqrt(2)) * 100, 2)
            rows.append(row)
    day_t = pd.DataFrame(rows)
    day_t.to_csv(RES / "by_day_sd.csv", index=False)

    rows = []
    for sig in [0.0, 0.15, 0.3]:
        for b in [0.0, 0.5, 1.0]:
            for fr in [0.05, 0.10, 0.20]:
                for si in [0, 1]:
                    rows.append(agg([one_run(rng, fr, si, sig, b) for _ in range(R_GRID)],
                                    {"day_sd": sig, "signup_effect": b, "pilot_share": fr, "selection": SELS[si]}))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    rnd, old = g[g.selection == SELS[0]], g[g.selection == SELS[1]]
    robust = {
        "n": int(len(g)),
        "random_cover_sig0_min": r(rnd[rnd.day_sd == 0].cover95_open_pct.min(), 2),
        "random_cover_sig0_max": r(rnd[rnd.day_sd == 0].cover95_open_pct.max(), 2),
        "random_cover_by_sig": rnd.groupby("day_sd").cover95_open_pct.agg(["min", "max"]).round(2).reset_index().to_dict("records"),
        "random_abs_err_by_sig": rnd.groupby("day_sd").mean_abs_err_open_pt.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
        "random_mean_err_abs_max": r(rnd.mean_err_open_pt.abs().max()),
        "old_mean_err_by_b": old.groupby("signup_effect").mean_err_open_pt.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
        "old_cover_b_pos_max": r(old[old.signup_effect > 0].cover95_open_pct.max(), 2),
        "old_b0_cover_min": r(old[old.signup_effect == 0].cover95_open_pct.min(), 2),
        "old_b0_cover_max": r(old[old.signup_effect == 0].cover95_open_pct.max(), 2),
    }
    mt = main_t.set_index(["selection", "pilot_share"])
    dt = day_t.set_index(["day_sd", "pilot_share"])
    headline = {
        "rest_open_random10": mt.loc[(SELS[0], 0.10), "rest_open"], "rest_click_random10": mt.loc[(SELS[0], 0.10), "rest_click"],
        "abs_err_open_random10": mt.loc[(SELS[0], 0.10), "mean_abs_err_open_pt"],
        "abs_relerr_open_random10": mt.loc[(SELS[0], 0.10), "mean_abs_relerr_open_pct"],
        "abs_relerr_click_random10": mt.loc[(SELS[0], 0.10), "mean_abs_relerr_click_pct"],
        "cover_open_random10": mt.loc[(SELS[0], 0.10), "cover95_open_pct"],
        "cover_click_random10": mt.loc[(SELS[0], 0.10), "cover95_click_pct"],
        "cover_open_random10_sig0": dt.loc[(0.0, 0.10), "cover95_open_pct"],
        "cover_open_random50": mt.loc[(SELS[0], 0.50), "cover95_open_pct"],
        "abs_err_open_random50": mt.loc[(SELS[0], 0.50), "mean_abs_err_open_pt"],
        "abs_err_open_random50_sig0": dt.loc[(0.0, 0.50), "mean_abs_err_open_pt"],
        "abs_err_open_random10_sig0": dt.loc[(0.0, 0.10), "mean_abs_err_open_pt"],
        "cover_open_random50_sig0": dt.loc[(0.0, 0.50), "cover95_open_pct"],
        "formula_cover_open_random50_sig0": dt.loc[(0.0, 0.50), "formula_cover95_open_pct"],
        "formula_abs_err_open_random10": dt.loc[(SIG, 0.10), "formula_abs_err_open_pt"],
        "formula_abs_err_open_random50": dt.loc[(SIG, 0.50), "formula_abs_err_open_pt"],
        "abs_err_open_random10_sig03": dt.loc[(0.3, 0.10), "mean_abs_err_open_pt"],
        "cover_open_random10_sig03": dt.loc[(0.3, 0.10), "cover95_open_pct"],
        "mean_err_old10": mt.loc[(SELS[1], 0.10), "mean_err_open_pt"], "mean_err_new10": mt.loc[(SELS[2], 0.10), "mean_err_open_pt"],
        "pilot_open_old10": mt.loc[(SELS[1], 0.10), "pilot_open"], "rest_open_old10": mt.loc[(SELS[1], 0.10), "rest_open"],
        "pilot_open_new10": mt.loc[(SELS[2], 0.10), "pilot_open"], "rest_open_new10": mt.loc[(SELS[2], 0.10), "rest_open"],
        "cover_old10": mt.loc[(SELS[1], 0.10), "cover95_open_pct"], "cover_addr10": mt.loc[(SELS[3], 0.10), "cover95_open_pct"],
    }
    out = {"settings": {"readers": M, "signup_days_max": 1094, "c0": C0, "click_c0": -1.7, "click_person_sd": 1.0, "z95": 1.96, "signup_effect": B, "person_sd": SD_U, "day_sd": SIG, "pilot_shares": FRACS,
                        "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline, "example_one_run": ex_s, "robust": robust}
    with open(RES / "a1207_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：試しの割合ごとの、残りの開封率との外れ（絶対値の平均）と、送った日の振れ
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for sig, c in zip([0.0, 0.15, 0.3], [GRAY, BLUE, ORANGE]):
        ss = day_t[day_t.day_sd == sig]
        ax.plot(ss.pilot_share * 100, ss.mean_abs_err_open_pt, marker="o", color=c,
                label=f"送った日の振れ σ={sig:g}" + ("（基本）" if sig == 0.15 else ""))
    for sig in [0.0, 0.15, 0.3]:
        ss = day_t[day_t.day_sd == sig]
        ax.plot(ss.pilot_share * 100, ss.formula_abs_err_open_pt, ls="--", color=INK, lw=0.8,
                label="式（近似）" if sig == 0 else None)
    ax.set_xscale("log")
    ax.set_xticks([2, 5, 10, 20, 50], ["2%", "5%", "10%", "20%", "50%"])
    ax.minorticks_off()
    ax.set_xlabel("試しに送った読者の割合（でたらめに選ぶ）")
    ax.set_ylabel("開封率の外れ（絶対値の平均、ポイント）")
    ax.set_ylim(0, day_t.mean_abs_err_open_pt.max() * 1.15)
    ax.set_title("試しを増やしても、送った日の振れの分は縮まない")
    ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1.0, 0.1))
    save(fig, "a1207_abs_error.png", SRC)

    # 図2：95%の幅に残りの開封率が入った割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for sig, c in zip([0.0, 0.15, 0.3], [GRAY, BLUE, ORANGE]):
        ss = day_t[day_t.day_sd == sig]
        ax.plot(ss.pilot_share * 100, ss.cover95_open_pct, marker="o", color=c,
                label=f"送った日の振れ σ={sig:g}" + ("（基本）" if sig == 0.15 else ""))
    for sig in [0.0, 0.15, 0.3]:
        ss = day_t[day_t.day_sd == sig]
        ax.plot(ss.pilot_share * 100, ss.formula_cover95_open_pct, ls="--", color=INK, lw=0.8,
                label="式（近似）" if sig == 0 else None)
    ax.axhline(95, color=GRAY, lw=0.8, ls=":")
    ax.text(2, 96, "95%", fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks([2, 5, 10, 20, 50], ["2%", "5%", "10%", "20%", "50%"])
    ax.minorticks_off()
    ax.set_xlabel("試しに送った読者の割合（でたらめに選ぶ）")
    ax.set_ylabel("試しの95%の幅に残りの開封率が入った割合（%）")
    ax.set_ylim(0, 105)
    ax.set_title("試しの開封率の「95%の幅」に、残りの開封率が入った割合")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1207_cover.png", SRC)

    # 図3：選び方ごとの試しと残りの開封率（試し10%）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sub = main_t[main_t.pilot_share == 0.10]
    x = np.arange(len(SELS))
    ax.bar(x - 0.18, sub.pilot_open * 100, 0.36, color=BLUE, label="試しの読者の開封率")
    ax.bar(x + 0.18, sub.rest_open * 100, 0.36, color=GRAY, label="残りの読者の開封率")
    for xi, a, b_ in zip(x, sub.pilot_open * 100, sub.rest_open * 100):
        ax.text(xi - 0.18, a + 0.4, f"{a:.2f}%", ha="center", fontsize=8.5)
        ax.text(xi + 0.18, b_ + 0.4, f"{b_:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x, [s.replace("（", "\n（") for s in SELS], fontsize=9)
    ax.set_ylabel(f"開封率（{R_MAIN}回の平均、%）")
    ax.set_ylim(0, max(sub.pilot_open.max(), sub.rest_open.max()) * 100 * 1.25)
    ax.set_title("試しの読者の選び方で、試しの開封率がずれる（試し10%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1207_selection.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
