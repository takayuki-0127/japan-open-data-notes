"""1285 1つ1つの部品の寸法が正規分布でないとき、何個重ねると、組み立て品の外れの割合は正規と見た見込みに近づくのか？（架空のデータ）

架空の書類トレー。同じ形のトレーを n 段重ねた高さを見る。1段の高さのずれは平均0・標準偏差0.10mm で、
形だけを変える（正規・平ら・山が2つ・片側に長い・すそが重い）。
組み立て品の許容差を「二乗の足し算」の±3倍（±3×√n×0.10mm）に置くと、正規と見た見込みでは外れは0.27%。
本当の外れの割合を、1段の分布を細かい刻みで n 回たたみ込んで出し（数値計算）、乱数で組んだ結果とも照らす。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1285
SRC = "架空の書類トレーの寸法の計算とシミュレーション（作成者が置いた分布、seed 1285）"
SD_MM = 0.10
DX = 0.005                      # 刻み（標準偏差を1とした単位）
LO, HI = -30.0, 30.0            # 1段の分布を置く範囲
NFFT = 2 ** 20
NS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, 40, 60]
KS = [2.0, 3.0, 4.0]            # 許容差＝±k×√n（標準偏差の単位）
MC_N, MC_RUNS = 5, 2_000_000

SHAPES = {
    "normal": ("正規（山が1つ）", {}),
    "flat": ("平ら", {}),
    "two_peaks_0.7": ("山が2つ（離れ0.7）", {"d": 0.7}),
    "two_peaks_0.9": ("山が2つ（離れ0.9）", {"d": 0.9}),
    "skew_k16": ("片側に長い（ゆるい）", {"k": 16}),
    "skew_k4": ("片側に長い（中くらい）", {"k": 4}),
    "skew_k1": ("片側に長い（強い）", {"k": 1}),
    "heavy_10pct_x3": ("すそが重い（1割が3倍に散らばる）", {"w": 0.10, "b": 3.0}),
    "heavy_2pct_x5": ("すそが重い（2%が5倍に散らばる）", {"w": 0.02, "b": 5.0}),
}
MAIN = ["flat", "two_peaks_0.9", "skew_k4", "heavy_10pct_x3"]

X = np.arange(LO, HI + DX / 2, DX)


def npdf(x, m=0.0, s=1.0):
    return np.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def masses(name, scale=1.0):
    """1段の分布を刻み DX のます目ごとの確率にする（平均0・標準偏差 scale）"""
    p = SHAPES[name][1]
    x = X / scale
    DX = globals()["DX"] / scale
    if name == "normal":
        m = npdf(x) * DX
    elif name == "flat":
        a = math.sqrt(3)
        lo, hi = x - DX / 2, x + DX / 2
        m = np.clip(np.minimum(hi, a) - np.maximum(lo, -a), 0, None) / (2 * a)
    elif name.startswith("two_peaks"):
        d = p["d"]; s = math.sqrt(1 - d * d)
        m = 0.5 * (npdf(x, -d, s) + npdf(x, d, s)) * DX
    elif name.startswith("skew"):
        k = p["k"]
        g = x * math.sqrt(k) + k          # 元の形の値
        with np.errstate(divide="ignore", invalid="ignore"):
            lp = (k - 1) * np.log(np.where(g > 0, g, 1)) - g - math.lgamma(k)
        dens = np.where(g > 0, np.exp(lp), 0.0) * math.sqrt(k)
        if k == 1:                         # 端で密度が跳ねるので、ます目の確率を直接出す
            lo = np.maximum(g - DX / 2, 0); hi = np.maximum(g + DX / 2, 0)
            m = np.exp(-lo) - np.exp(-hi)
        else:
            m = dens * DX
    elif name.startswith("heavy"):
        w, b = p["w"], p["b"]
        a = 1 / math.sqrt(1 - w + w * b * b)
        m = ((1 - w) * npdf(x, 0, a) + w * npdf(x, 0, a * b)) * DX
    m = m / m.sum()
    return m


def tail(s, x, c):
    """ます目の確率を、ます目の幅に均して ±c の外の確率を出す"""
    cum = np.cumsum(s)
    edge = x + DX / 2
    return max(0.0, float(np.interp(-c, edge, cum) + 1 - np.interp(c, edge, cum)))


def out_rates(m, ns, ks):
    """n 段の合計の、±k√n の外に出る確率"""
    F = np.fft.rfft(m, NFFT)
    res = {}
    for n in ns:
        s = np.fft.irfft(F ** n, NFFT)
        s = np.clip(s, 0, None)
        x = n * LO + np.arange(NFFT) * DX
        mean = (s * x).sum()
        sd = math.sqrt((s * (x - mean) ** 2).sum())
        for k in ks:
            c = k * math.sqrt(n)
            res[(n, k)] = (tail(s, x, c), mean, sd)
    return res


def sample(rng, name, size):
    p = SHAPES[name][1]
    if name == "normal":
        return rng.normal(0, 1, size)
    if name == "flat":
        return rng.uniform(-math.sqrt(3), math.sqrt(3), size)
    if name.startswith("two_peaks"):
        d = p["d"]
        return rng.choice([-d, d], size) + rng.normal(0, math.sqrt(1 - d * d), size)
    if name.startswith("skew"):
        k = p["k"]
        return (rng.gamma(k, 1.0, size) - k) / math.sqrt(k)
    w, b = p["w"], p["b"]
    a = 1 / math.sqrt(1 - w + w * b * b)
    return rng.normal(0, 1, size) * np.where(rng.random(size) < w, a * b, a)


def first_n_close(df, name, k, tol=0.10):
    """この n 以降（60まで）ずっと正規の見込みの ±10% に入る最小の n"""
    d = df[(df.shape_id == name) & (df.k == k)].sort_values("n")
    ok = (d.ratio_to_normal - 1).abs() <= tol
    first = None
    for n_, o in zip(d.n[::-1], ok[::-1]):
        if o:
            first = n_
        else:
            break
    return int(first) if first is not None else None


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for name in SHAPES:
        m = masses(name)
        r = out_rates(m, NS, KS)
        for (n, k), (o, mean, sd) in r.items():
            pn = 2 * (1 - ncdf(k))
            rows.append({"shape_id": name, "shape": SHAPES[name][0], "n": n, "k": k,
                         "out_pct": round(100 * o, 4), "normal_pct": round(100 * pn, 4),
                         "ratio_to_normal": round(o / pn, 4), "check_mean": round(mean, 4), "check_sd_over_sqrt_n": round(sd / math.sqrt(n), 4)})
    df = pd.DataFrame(rows)
    df.drop(columns=["check_mean", "check_sd_over_sqrt_n"]).to_csv(RES / "out_by_n.csv", index=False)

    # 27通り：9つの形×3つの幅で、正規の ±10% に近づく n
    grid = []
    for name in SHAPES:
        for k in KS:
            fn = first_n_close(df, name, k)
            d1 = df[(df.shape_id == name) & (df.k == k)].set_index("n")
            grid.append({"shape_id": name, "shape": SHAPES[name][0], "k": k, "normal_pct": float(d1.normal_pct.iloc[0]),
                         "ratio_n1": float(d1.ratio_to_normal[1]), "ratio_n5": float(d1.ratio_to_normal[5]),
                         "ratio_n10": float(d1.ratio_to_normal[10]), "ratio_n20": float(d1.ratio_to_normal[20]),
                         "first_n_within_10pct": fn if fn is not None else "60より多い"})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_first_n.csv", index=False)

    # 乱数で組んだ照らし合わせ（5段、200万台）
    mc = []
    for name in SHAPES:
        h = sample(rng, name, (MC_RUNS, MC_N)).sum(1)
        for k in KS:
            c = k * math.sqrt(MC_N)
            o = float((np.abs(h) > c).mean())
            calc = float(df[(df.shape_id == name) & (df.n == MC_N) & (df.k == k)].out_pct.iloc[0])
            mc.append({"shape_id": name, "k": k, "mc_out_pct": round(100 * o, 4), "calc_out_pct": calc})
    mc = pd.DataFrame(mc)
    mc.to_csv(RES / "check_simulation_n5.csv", index=False)

    # 1段だけ大きく、形が違うとき（5段：4段は正規、1段だけ標準偏差が s 倍で形が違う）
    dom = []
    for name in ["flat", "two_peaks_0.9", "skew_k1"]:
        mn = masses("normal")
        for s_ in [1, 2, 3, 5]:
            mbig = masses(name, s_)
            F = np.fft.rfft(mn, NFFT) ** 4 * np.fft.rfft(mbig, NFFT)
            sm = np.clip(np.fft.irfft(F, NFFT), 0, None)
            x = 5 * LO + np.arange(NFFT) * DX
            tot_sd = math.sqrt(4 + s_ ** 2)
            o3 = tail(sm, x, 3 * tot_sd)
            dom.append({"shape_id": name, "shape": SHAPES[name][0], "big_part_sd_times": s_,
                        "big_part_share_of_variance_pct": round(100 * s_ ** 2 / (4 + s_ ** 2), 1),
                        "out_pct": round(100 * o3, 4), "ratio_to_normal": round(o3 / (2 * (1 - ncdf(3))), 4)})
    dom = pd.DataFrame(dom)
    dom.to_csv(RES / "one_big_part.csv", index=False)

    # 例のデータ：1段の高さのずれ（各形1,000個、mm）
    ex = pd.DataFrame({sid: (sample(rng, sid, 1000) * SD_MM).round(4) for sid in MAIN + ["normal"]})
    ex.to_csv(DATA / "example_one_tray_mm.csv", index=False)

    chk = df.groupby("shape_id").agg(max_abs_mean=("check_mean", lambda v: float(np.abs(v).max())),
                                    sd_min=("check_sd_over_sqrt_n", "min"), sd_max=("check_sd_over_sqrt_n", "max"))
    main_json = {
        "setting": {"sd_each_mm": SD_MM, "tolerance": "±k×√n×標準偏差（k=2・3・4、基本3）", "grid_step_sd": DX, "ns": NS,
                    "shapes": {sid: {"name": v[0], **v[1]} for sid, v in SHAPES.items()},
                    "simulation_n": MC_N, "simulation_runs": MC_RUNS, "seed": SEED},
        "base_k3": {sid: {str(n): float(df[(df.shape_id == sid) & (df.k == 3.0) & (df.n == n)].out_pct.iloc[0]) for n in [1, 2, 3, 4, 5, 8, 10, 20, 60]}
                    for sid in ["normal"] + MAIN},
        "first_n_within_10pct_k3": {sid: grid[(grid.shape_id == sid) & (grid.k == 3.0)].first_n_within_10pct.iloc[0] for sid in SHAPES},
        "check_calc": {"normal_k3_all_n_pct": sorted(set(df[(df.shape_id == "normal") & (df.k == 3.0)].out_pct.tolist())),
                       "max_abs_mean": round(float(chk.max_abs_mean.max()), 6),
                       "sd_over_sqrt_n_min": float(chk.sd_min.min()), "sd_over_sqrt_n_max": float(chk.sd_max.max()),
                       "max_abs_diff_sim_vs_calc_pct_points": round(float((mc.mc_out_pct - mc.calc_out_pct).abs().max()), 4)},
    }
    with open(RES / "a1285_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1, default=str)

    # 図1：1段の形
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8), sharey=True)
    for ax, sid in zip(axes, MAIN):
        m = masses(sid)
        ax.plot(X * SD_MM, m / DX / SD_MM, color=BLUE)
        ax.plot(X * SD_MM, npdf(X) / SD_MM, color=GRAY, ls="--", lw=1)
        ax.set_xlim(-0.45, 0.45)
        ax.set_title(SHAPES[sid][0], fontsize=10)
        ax.set_xlabel("1段のずれ（mm）", fontsize=9)
    axes[0].set_ylabel("密度")
    axes[0].set_ylim(0, None)
    fig.suptitle("1段の高さのずれの形（標準偏差はどれも0.10mm、点線は正規）", y=1.04)
    save(fig, "a1285_shapes.png", SRC, y=-0.06)
    # 図2：段数と外れの割合（k=3）
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    cols = {"flat": BLUE, "two_peaks_0.9": GREEN, "skew_k4": ORANGE, "heavy_10pct_x3": INK}
    for sid in MAIN:
        d = df[(df.shape_id == sid) & (df.k == 3.0)]
        ax.plot(d.n, d.out_pct, "o-", ms=4, color=cols[sid], label=SHAPES[sid][0])
    ax.axhline(0.27, color=GRAY, ls="--", lw=1)
    ax.axhspan(0.27 * 0.9, 0.27 * 1.1, color=GRAY, alpha=0.15, lw=0)
    ax.text(1.05, 0.31, "正規と見た見込み0.27%（灰色の帯は±10%）", ha="left", fontsize=9, color=INK)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 3, 5, 10, 20, 60], ["1", "2", "3", "5", "10", "20", "60"])
    ax.set_xlabel("重ねた段数")
    ax.set_ylabel("±3×√段数×0.10mm の外に出る割合（%）")
    ax.set_ylim(0, None)
    ax.set_title("段数を増やすと、外れの割合は0.27%に近づく（速さは形しだい）")
    ax.legend(fontsize=9, frameon=False, loc="upper right", bbox_to_anchor=(1, 0.92))
    save(fig, "a1285_out_by_n.png", SRC)
    # 図3：近づく段数（27通り）
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    sids = [s for s in SHAPES if s != "normal"]
    yy = np.arange(len(sids))
    for j, k in enumerate(KS):
        vals = []
        for sid in sids:
            v = grid[(grid.shape_id == sid) & (grid.k == k)].first_n_within_10pct.iloc[0]
            vals.append(61 if isinstance(v, str) else v)
        ax.barh(yy + (j - 1) * 0.27, vals, 0.27, color=[LIGHT, BLUE, INK][j], label=f"±{k:.0f}×√段数（正規で{round(2 * (1 - ncdf(k)) * 100, 4):g}%）")
        for y, v in zip(yy + (j - 1) * 0.27, vals):
            ax.text(v + 0.5, y, "60より多い" if v == 61 else str(v), va="center", fontsize=7.5)
    ax.set_yticks(yy, [SHAPES[s][0] for s in sids], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 72)
    ax.set_xlabel("この段数から先はずっと、正規と見た見込みの±10%に入る（60段まで数えた）")
    ax.set_title("正規と見た外れの割合に近づくまでの段数")
    ax.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.4, -0.13), ncol=3)
    save(fig, "a1285_first_n.png", SRC, y=-0.1)
    print(json.dumps(main_json, ensure_ascii=False, indent=1, default=str))
    print(grid.to_string())
    print(dom.to_string())
    print(mc.to_string())


if __name__ == "__main__":
    main()
