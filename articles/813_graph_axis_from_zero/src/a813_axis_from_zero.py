"""813 縦軸を0から始めないと、差は何倍に見えるのか？（架空のデータ）

架空の会社1,000社の月ごとの売上（12か月）を作り、縦軸の始め方ごとに
「描かれた高さの比」が「本当の数字の比」の何倍の差に見えるかを数える。
見た目の差の倍率 = （描かれた高さの比 − 1）÷（本当の比 − 1）。0から始めれば1倍。
"""
import json
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 813
SRC = "架空の会社の月ごとの売上（作成者が乱数で作成、seed 813）"
rng = np.random.default_rng(SEED)
N_CO = 1000


def make_companies(rng, n=N_CO, months=12, cv=(0.01, 0.15)):
    level = np.exp(rng.normal(np.log(3000), 0.5, n))            # 月の売上の水準（万円）
    trend = rng.normal(0.03, 0.05, n)                             # 1年での伸び
    c = rng.uniform(cv[0], cv[1], n)                              # 月ごとの振れ（変動係数）
    t = np.arange(months) / 11
    sales = level[:, None] * (1 + trend[:, None] * t[None, :]) * (1 + c[:, None] * rng.normal(0, 1, (n, months)))
    sales = np.maximum(sales, level[:, None] * 0.3)
    return sales, c


def lie(drawn_ratio, true_ratio):
    return (drawn_ratio - 1) / (true_ratio - 1)


def auto_limits(y, margin=0.05):
    """線グラフの既定（データの範囲の上下に margin を足す）"""
    lo, hi = y.min(1), y.max(1)
    r = hi - lo
    return lo - margin * r, hi + margin * r


_AX = {}


def mpl_limits(y, mode="data", margin=0.05):
    """matplotlib で実際に描いて縦軸の範囲を取る"""
    key = (mode, margin)
    if key not in _AX:
        with matplotlib.rc_context({"axes.autolimit_mode": mode, "axes.ymargin": margin}):
            fig, ax = plt.subplots()
            line, = ax.plot(np.arange(len(y)), y)
        _AX[key] = (fig, ax, line)
    fig, ax, line = _AX[key]
    with matplotlib.rc_context({"axes.autolimit_mode": mode, "axes.ymargin": margin}):
        line.set_data(np.arange(len(y)), y)
        ax.relim(); ax.autoscale_view()
        return ax.get_ylim()


def drawn_ratio(y, lo):
    """最大の月と最小の月の、軸の下端から測った高さの比"""
    return (y.max(-1) - lo) / (y.min(-1) - lo)


def main():
    sales, c = make_companies(rng)
    true_ratio = sales.max(1) / sales.min(1)
    df = pd.DataFrame(np.round(sales, 1), columns=[f"m{i+1:02d}" for i in range(12)])
    df.insert(0, "company_id", np.arange(1, N_CO + 1)); df.insert(1, "cv", np.round(c, 4))
    df.to_csv(DATA / "companies.csv", index=False)

    # 1) 縦軸を「小さいほうの値の f 倍」から始めたとき（2つの値の比べ）
    fixed = []
    for f in [0, 0.5, 0.8, 0.9, 0.95]:
        for d in [0.02, 0.05, 0.10, 0.30]:
            a, b = 1.0, 1 + d
            dr = (b - f * a) / (a - f * a)
            fixed.append({"base_fraction": f, "true_diff_pct": d * 100, "drawn_ratio": round(dr, 3),
                          "lie_factor": round(lie(dr, b / a), 3)})
    fixed = pd.DataFrame(fixed)
    fixed.to_csv(RES / "fixed_base.csv", index=False)

    # 2) 線グラフの既定の自動の目盛り（上下5%の余白）
    lo, hi = auto_limits(sales)
    dr_auto = drawn_ratio(sales, lo)
    lf_auto = lie(dr_auto, true_ratio)
    # matplotlib で実際に描いた範囲と一致するか（先頭50社）
    chk = []
    for i in range(50):
        l2, h2 = mpl_limits(sales[i], "data")
        chk.append(abs(l2 - lo[i]) / (hi[i] - lo[i]))
    # 3) 目盛りを切りのいい数に丸める自動（matplotlib の round_numbers）
    lo_r = np.array([mpl_limits(sales[i], "round_numbers")[0] for i in range(N_CO)])
    dr_round = drawn_ratio(sales, lo_r)
    lf_round = lie(dr_round, true_ratio)

    per = pd.DataFrame({"company_id": np.arange(1, N_CO + 1), "true_ratio": np.round(true_ratio, 4),
                        "true_diff_pct": np.round((true_ratio - 1) * 100, 2),
                        "auto_drawn_ratio": np.round(dr_auto, 3), "auto_lie": np.round(lf_auto, 2),
                        "round_axis_min": np.round(lo_r, 1), "round_drawn_ratio": np.round(dr_round, 3),
                        "round_lie": np.round(lf_round, 2), "round_from_zero": lo_r <= 0})
    per.to_csv(RES / "per_company.csv", index=False)

    def q(x):
        return {"median": round(float(np.median(x)), 2), "p10": round(float(np.quantile(x, .1)), 2),
                "p90": round(float(np.quantile(x, .9)), 2)}

    bands = []
    for lo_b, hi_b in [(0, 10), (10, 20), (20, 40), (40, 1000)]:
        m = ((true_ratio - 1) * 100 >= lo_b) & ((true_ratio - 1) * 100 < hi_b)
        bands.append({"true_diff_band": f"{lo_b}〜{hi_b}%" if hi_b < 1000 else f"{lo_b}%以上", "companies": int(m.sum()),
                      "auto_lie_median": round(float(np.median(lf_auto[m])), 1),
                      "round_lie_median": round(float(np.median(lf_round[m])), 1),
                      "round_lie_p10": round(float(np.quantile(lf_round[m], .1)), 1),
                      "round_lie_p90": round(float(np.quantile(lf_round[m], .9)), 1)})
    bands = pd.DataFrame(bands)
    bands.to_csv(RES / "by_true_diff.csv", index=False)

    # 4) 確かめ：置き方を変える
    sens = []
    for name, months, cv, margin in [("基本（12か月・振れ1〜15%・余白5%）", 12, (0.01, 0.15), 0.05),
                                     ("余白10%", 12, (0.01, 0.15), 0.10),
                                     ("6か月", 6, (0.01, 0.15), 0.05),
                                     ("24か月", 24, (0.01, 0.15), 0.05),
                                     ("振れ1〜5%", 12, (0.01, 0.05), 0.05),
                                     ("振れ5〜30%", 12, (0.05, 0.30), 0.05)]:
        s, _ = make_companies(np.random.default_rng(SEED + months * 7 + int(cv[1] * 100) + int(margin * 100)), 300, months, cv)
        tr = s.max(1) / s.min(1)
        la = lie(drawn_ratio(s, auto_limits(s, margin)[0]), tr)
        lr_lo = np.array([mpl_limits(s[i], "round_numbers", margin)[0] for i in range(len(s))])
        lr = lie(drawn_ratio(s, lr_lo), tr)
        sens.append({"setting": name, "true_diff_median_pct": round(float(np.median(tr - 1) * 100), 1),
                     "auto_drawn_ratio": round(float(np.median(drawn_ratio(s, auto_limits(s, margin)[0]))), 2),
                     "auto_lie_median": round(float(np.median(la)), 1),
                     "round_lie_median": round(float(np.median(lr)), 1),
                     "round_from_zero_share": round(float((lr_lo <= 0).mean()), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"n_companies": N_CO,
           "true_diff_pct": q((true_ratio - 1) * 100),
           "fixed_base_lie_factor": {f"{f:g}": float(fixed[fixed.base_fraction == f].lie_factor.iloc[0]) for f in fixed.base_fraction.unique()},
           "auto": {"drawn_ratio": q(dr_auto), "lie_factor": q(lf_auto),
                    "matplotlib_check_max_rel_diff_50": float(max(chk))},
           "round_numbers": {"drawn_ratio": q(dr_round), "lie_factor": q(lf_round),
                             "share_axis_from_zero": round(float((lo_r <= 0).mean()), 3),
                             "axis_min_over_data_min": q(lo_r / sales.min(1))},
           "by_true_diff": bands.to_dict("records"), "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a813_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ売上を、0から始めた棒と自動の線で
    i = int(np.argsort(np.abs(true_ratio - np.median(true_ratio)))[0])
    y = sales[i]; mo = np.arange(1, 13)
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.8))
    axs[0].bar(mo, y, color=BLUE); axs[0].set_ylim(0, y.max() * 1.1)
    axs[0].set_title("縦軸を0から（棒）", fontsize=11)
    axs[1].plot(mo, y, color=ORANGE, marker="o", ms=4)
    axs[1].set_ylim(*auto_limits(y[None, :]))
    axs[1].set_title("縦軸は自動（線グラフの既定）", fontsize=11)
    for ax in axs:
        ax.set_xticks(mo); ax.set_xlabel("月"); ax.set_ylabel("売上（万円）")
    fig.suptitle(f"同じ1社の売上。最大の月は最小の月の{true_ratio[i]:.2f}倍だが、右では{dr_auto[i]:.0f}倍の高さに描かれる",
                 fontsize=11.5)
    fig.tight_layout()
    save(fig, "a813_pair.png", SRC)

    # 図2：本当の差と見た目の差の倍率（1,000社）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = (true_ratio - 1) * 100
    ax.scatter(x, lf_auto, s=7, color=ORANGE, alpha=.5, lw=0, label="自動（上下5%の余白）")
    ax.scatter(x, lf_round, s=7, color=BLUE, alpha=.5, lw=0, label="自動（切りのいい数に丸める）")
    ax.axhline(1, color=INK, lw=1); ax.text(x.max() * 0.98, 1.15, "0から始めた場合（1倍）", ha="right", fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([3, 5, 10, 20, 50, 100], ["3%", "5%", "10%", "20%", "50%", "100%"])
    ax.set_yticks([1, 3, 10, 30, 100, 300, 1000], ["1倍", "3倍", "10倍", "30倍", "100倍", "300倍", "1000倍"])
    ax.minorticks_off()
    ax.set_xlabel("本当の差：最大の月が最小の月より何%多いか（対数の目盛り）")
    ax.set_ylabel("見た目の差の倍率（対数の目盛り）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("本当の差が小さい会社ほど、自動の目盛りでは差が大きく見える（1,000社）")
    save(fig, "a813_lie_auto.png", SRC)

    # 図3：縦軸の始め方と見た目の差の倍率
    fs = np.linspace(0, 0.95, 96)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(fs * 100, 1 / (1 - fs), color=BLUE)
    for f in [0, 0.5, 0.8, 0.9, 0.95]:
        v = out["fixed_base_lie_factor"][f"{f:g}"]
        ax.plot(f * 100, v, "o", color=ORANGE)
        if f == 0:
            ax.text(2, v + 0.8, "0から：1倍", fontsize=9, ha="left")
        else:
            ax.text(f * 100 - 1.5, v + 0.8, f"{f*100:.0f}%から：{v:.0f}倍", fontsize=9, ha="right")
    ax.set_xlabel("縦軸の始まり（小さいほうの値の何%から始めるか）"); ax.set_ylabel("見た目の差の倍率")
    ax.set_xlim(-3, 100); ax.set_ylim(0, 22)
    ax.set_title("縦軸の始まりを小さいほうの値に近づけるほど、差は大きく見える")
    save(fig, "a813_base_fraction.png", SRC)
    for fig_, _, _ in _AX.values():
        plt.close(fig_)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
