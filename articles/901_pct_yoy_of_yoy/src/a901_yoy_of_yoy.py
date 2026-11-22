"""901 「前年比の前年比」は、何を表しているのか？（架空のデータ）

架空の店5,000店の6年分の月の売上。店ごとに年ごとの「本当の伸び」を置き、月の売上には季節の形と
たまたまの振れを掛ける。前年比（今年÷前年同月）と、前年比の前年比（今年の前年比÷前年の前年比）を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 901
SRC = "架空の店の月の売上（作成者が乱数で作成、seed 901）"
N_SHOP = 5000
YEARS = 6
G_MEAN, G_SD = 0.05, 0.03   # 年ごとの本当の伸び（平均5%、年ごとに標準偏差3%で変わる）
SIGMA = 0.06                # 月のたまたまの振れ（対数の標準偏差）


def make(rng, n=N_SHOP, g_sd=G_SD, sigma=SIGMA):
    T = 12 * YEARS
    g = rng.normal(G_MEAN, g_sd, (n, YEARS))
    slope = np.repeat(np.log1p(g) / 12, 12, axis=1)            # 月ごとの本当の伸び（対数）
    L = np.cumsum(slope, axis=1)                                 # 本当の水準（対数、季節を除く）
    season = 0.15 * np.sin(2 * np.pi * (np.arange(T) + rng.uniform(0, 12, (n, 1))) / 12)
    e = rng.normal(0, sigma, (n, T))
    logS = np.log(1000) + L + season + e
    return L, e, logS


def yoy_parts(L, e, logS):
    """t=24..T-1 の月について、前年比・前年比の前年比（見かけと本当）"""
    r = logS[:, 12:] - logS[:, :-12]                 # 前年比（対数）、t=12..
    tr = L[:, 12:] - L[:, :-12]                      # 本当の前年比（対数）
    yy = r[:, 12:] - r[:, :-12]                      # 前年比の前年比（対数）、t=24..
    tyy = tr[:, 12:] - tr[:, :-12]
    return r[:, 12:], tr[:, 12:], yy, tyy


def annual_total(logS):
    """12か月の移動合計（年計）"""
    S = np.exp(logS)
    c = np.cumsum(S, axis=1)
    tot = c[:, 11:] - np.concatenate([np.zeros((S.shape[0], 1)), c[:, :-12]], axis=1)   # t=11..
    return np.log(tot)


def summarize(L, e, logS):
    r, tr, yy, tyy = yoy_parts(L, e, logS)
    down = yy < 0
    lt = annual_total(logS)                        # index 0 = t11
    lr = lt[:, 12:] - lt[:, :-12]                  # t=23..
    lyy = lr[:, 12:] - lr[:, :-12]                 # t=35..
    tyy35 = tyy[:, 11:]                            # 本当の月の前年比の前年比、t=35..
    yy35 = yy[:, 11:]
    nyy = e[:, 24:] - 2 * e[:, 12:-12] + e[:, :-24]
    return {
        "share_yy_below_100": float(down.mean()),
        "share_sales_up_among_yy_below_100": float((r[down] > 0).mean()),
        "share_sales_up_all": float((r > 0).mean()),
        "sign_agree_true_yy": float(((yy < 0) == (tyy < 0)).mean()),
        "sign_agree_true_yy_t35": float(((yy35 < 0) == (tyy35 < 0)).mean()),
        "sign_agree_annual_total_t35": float(((lyy < 0) == (tyy35 < 0)).mean()),
        "sign_agree_yoy_vs_true_yoy": float(((r < 0) == (tr < 0)).mean()),
        "sd_log_yy": float(yy.std()), "sd_log_true_yy": float(tyy.std()), "sd_noise_part": float(nyy.std()),
        "sd_log_yoy": float(r.std()), "sd_log_true_yoy": float(tr.std()),
        "corr_yy_lastyear_noise": float(np.corrcoef(yy.ravel(), e[:, 12:-12].ravel())[0, 1]),
        "share_big_drop_lt95": float((yy < np.log(0.95)).mean()),
        "share_big_drop_true_slowdown_lt95": float((tyy[yy < np.log(0.95)] < np.log(0.95)).mean()),
        "share_big_drop_lastyear_noise_pos": float((e[:, 12:-12][yy < np.log(0.95)] > 0).mean()),
    }


def r4(d):
    return {k: round(v, 4) for k, v in d.items()}


def main():
    rng = np.random.default_rng(SEED)

    # 例の1店：本当の伸びは毎年5%で一定、3年目の7月だけ改装で15%少ない月を置く
    T = 12 * YEARS
    L1 = np.cumsum(np.full(T, np.log1p(0.05) / 12))
    season = 0.15 * np.sin(2 * np.pi * np.arange(T) / 12)
    e1 = rng.normal(0, 0.01, T)
    dip = 24 + 6                                   # 3年目の7月
    e1[dip] += np.log(0.85)
    S1 = np.round(1000 * np.exp(L1 + season + e1)).astype(int)
    ex = pd.DataFrame({"year": np.arange(T) // 12 + 1, "month": np.arange(T) % 12 + 1, "sales": S1})
    ex["yoy"] = ex.sales / ex.sales.shift(12)
    ex["yoy_of_yoy"] = ex.yoy / ex.yoy.shift(12)
    ex["two_year"] = ex.sales / ex.sales.shift(24)
    ex.to_csv(DATA / "example_shop.csv", index=False, float_format="%.4f")
    pick = ex.iloc[[dip, dip + 12, dip + 24, dip + 36]]
    example = [{"year": int(a.year), "month": int(a.month), "sales": int(a.sales),
                "yoy": None if pd.isna(a.yoy) else round(float(a.yoy), 4),
                "yoy_of_yoy": None if pd.isna(a.yoy_of_yoy) else round(float(a.yoy_of_yoy), 4),
                "two_year": None if pd.isna(a.two_year) else round(float(a.two_year), 4)} for _, a in pick.iterrows()]
    chk = ex.dropna()
    ident = float((chk.yoy * chk.yoy.shift(12) - chk.two_year).abs().max())

    # 本体：5,000店
    L, e, logS = make(rng)
    base = r4(summarize(L, e, logS))

    # 確かめ：振れ sigma × 伸びの変わり方 g_sd
    sens = []
    for i, sg in enumerate([0.02, 0.06, 0.12]):
        for j, gs in enumerate([0.01, 0.03, 0.06]):
            Ls, es, ls = make(np.random.default_rng(SEED * 10 + 3 * i + j), 3000, gs, sg)
            d = summarize(Ls, es, ls)
            sens.append({"sigma": sg, "g_sd": gs, **{k: round(d[k], 4) for k in
                         ["sign_agree_true_yy", "sign_agree_annual_total_t35", "share_sales_up_among_yy_below_100",
                          "corr_yy_lastyear_noise", "share_big_drop_true_slowdown_lt95"]}})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    rng_s = {c + "_min": float(sens[c].min()) for c in sens.columns[2:]}
    rng_s.update({c + "_max": float(sens[c].max()) for c in sens.columns[2:]})

    theory = {"noise_var_multiple_yy_vs_level": 6, "noise_var_multiple_yoy_vs_level": 2,
              "corr_yy_lastyear_noise_if_noise_only": round(-2 / np.sqrt(6), 4),
              "sd_noise_part_theory": round(SIGMA * np.sqrt(6), 4)}
    out = {"settings": {"n_shop": N_SHOP, "years": YEARS, "growth_mean": G_MEAN, "growth_sd_by_year": G_SD,
                        "sigma_month": SIGMA, "seed": SEED},
           "example_shop": example, "identity_max_err": float(f"{ident:.2e}"), "base": base, "theory": theory,
           "sensitivity_range": rng_s}
    json.dump(out, open(RES / "a901_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1店
    fig, axs = plt.subplots(3, 1, figsize=(7.2, 7.0), sharex=True)
    x = np.arange(T)
    axs[0].plot(x, ex.sales, color=INK, lw=1.2); axs[0].set_ylabel("売上（万円）")
    axs[1].plot(x, ex.yoy * 100, color=BLUE, lw=1.4); axs[1].axhline(105, color=GRAY, lw=1, ls="--")
    axs[1].set_ylabel("前年比（%）")
    axs[2].plot(x, ex.yoy_of_yoy * 100, color=ORANGE, lw=1.4); axs[2].axhline(100, color=GRAY, lw=1, ls="--")
    axs[2].set_ylabel("前年比の前年比（%）")
    for k, ax in enumerate(axs):
        for d in [dip, dip + 12, dip + 24]:
            ax.axvline(d, color=GRAY, lw=.6, ls=":")
    axs[0].annotate("改装で15%少ない月", (dip, ex.sales[dip]), (dip + 3, ex.sales[dip] - 60), fontsize=9,
                    arrowprops=dict(arrowstyle="-", color=GRAY))
    axs[1].text(T - 1, 112, "点線：本当の伸び 105%", ha="right", fontsize=8.5, color=GRAY)
    axs[2].set_xticks(np.arange(0, T, 12)); axs[2].set_xticklabels([f"{y}年目" for y in range(1, YEARS + 1)])
    axs[0].set_title("1か月の落ち込みが、前年比では2回、前年比の前年比では3回出る（例の1店）")
    save(fig, "a901_example.png", SRC, y=0.03)

    # 図2：前年比の前年比と、前年同月のたまたまの振れ
    r, tr, yy, tyy = yoy_parts(L, e, logS)
    idx = np.random.default_rng(SEED + 1).choice(yy.size, 4000, replace=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(e[:, 12:-12].ravel()[idx] * 100, np.exp(yy.ravel()[idx]) * 100, s=5, color=BLUE, alpha=.35, lw=0)
    ax.axhline(100, color=GRAY, lw=1, ls="--")
    ax.set_xlabel("前年同月のたまたまの振れ（%、プラスは前年がたまたま多かった月）")
    ax.set_ylabel("前年比の前年比（%）")
    ax.set_title(f"前年比の前年比は、前年のたまたまの振れでほぼ決まる（相関 {base['corr_yy_lastyear_noise']:.2f}）")
    save(fig, "a901_lastyear.png", SRC)

    # 図3：確かめ（伸びが速まったか鈍ったかを当てた割合）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for gs, c in zip([0.01, 0.03, 0.06], [LIGHT, BLUE, INK]):
        g = sens[sens.g_sd == gs]
        ax.plot(g.sigma * 100, g.sign_agree_true_yy * 100, "o-", color=c, label=f"月ごと（伸びの年ごとの変わり {gs*100:.0f}%）")
        ax.plot(g.sigma * 100, g.sign_agree_annual_total_t35 * 100, "s--", color=c, alpha=.8,
                label=f"年計（伸びの年ごとの変わり {gs*100:.0f}%）")
    ax.axhline(50, color=GRAY, lw=1)
    ax.text(2, 47.5, "当てずっぽう 50%", ha="left", fontsize=8.5, color=GRAY)
    ax.set_xlabel("月の売上のたまたまの振れ（%、作成者が置いた値）"); ax.set_ylabel("向きが合った割合（%）")
    ax.set_ylim(40, 100); ax.set_xticks([2, 6, 12])
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    ax.set_title("前年比の前年比で「伸びが鈍ったか」を当てた割合（各3,000店）")
    save(fig, "a901_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
