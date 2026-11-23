"""973 前の値で埋めると、変化はどう見えるのか？（架空のデータ）

架空の会社の200店の月の売上（24か月）。本当の売上を作成者が置き、報告の抜け（ところどころの月）と、
途中で報告をやめた店を置く。抜けを「前の値で埋める」「報告のあった店だけで比べる」「前後の値を線でつなぐ」
の3つで扱い、店ごとの前の月との変化・全店の前年同月比・改装した店の上がり方がどう見えるかを比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 973
SRC = "架空の会社の店の月の売上（作成者が乱数で作成、seed 973）"
S, T = 200, 24
G = 0.01            # 会社全体の伸び（1か月あたり）
TREND_SD = 0.005    # 店ごとの伸びの差（1か月あたり、標準偏差）
NOISE = 0.04        # 月ごとの振れ（標準偏差、掛け算）
Q = 0.20            # 報告の抜け（2か月目以降の店×月のうち、でたらめに抜ける割合）
D = 0.15            # 途中で報告をやめた店の割合（7〜24か月目のどこかでやめ、その後は報告なし）
RENOV, STEP = 40, 0.15   # 13か月目から売上が15%上がった店（改装した店）
REPS = 500
MECH = {"random": "でたらめな店がやめる", "down": "伸びの低い店ほどやめる"}
WAYS = ["本当の売上", "前の値で埋める", "報告のあった店だけ", "前後を線でつなぐ"]


def make_sales(rng, g=G):
    level = np.exp(rng.normal(np.log(500), 0.4, S))            # 1か月目の売上（万円）
    trend = rng.normal(0, TREND_SD, S)
    t = np.arange(T)
    log_y = (np.log(level)[:, None] + (g + trend)[:, None] * t[None, :]
             + rng.normal(0, NOISE, (S, T)))
    renov = np.zeros(S, bool); renov[rng.choice(S, RENOV, replace=False)] = True
    log_y[renov, 12:] += np.log(1 + STEP)                       # 13か月目（列12）から
    return np.exp(log_y), trend, renov


def make_missing(rng, trend, q=Q, d=D, mech="random"):
    miss = rng.random((S, T)) < q
    miss[:, 0] = False                                          # 1か月目は全店が報告
    nd = int(round(d * S))
    if nd:
        if mech == "random":
            who = rng.choice(S, nd, replace=False)
        else:
            w = np.exp(-2.0 * (trend - trend.mean()) / trend.std())
            who = rng.choice(S, nd, replace=False, p=w / w.sum())
        start = rng.integers(6, T, nd)                          # 7〜24か月目（列6〜23）からやめる
        for i, s0 in zip(who, start):
            miss[i, s0:] = True
    else:
        who = np.array([], int)
    return miss, who


def locf(y, miss):
    f = y.copy()
    for t in range(1, T):
        f[:, t] = np.where(miss[:, t], f[:, t - 1], y[:, t])
    return f


def interp(y, miss):
    """前後に報告がある抜けは、対数の線でつなぐ。最後の報告より後は埋めない（NaN）"""
    f = np.where(miss, np.nan, np.log(y))
    t = np.arange(T)
    for i in range(S):
        ok = ~miss[i]
        last = t[ok].max()
        f[i, :last + 1] = np.interp(t[:last + 1], t[ok], f[i, ok])
    return np.exp(f)


def stats(y, miss, renov):
    lf = locf(y, miss)
    li = interp(y, miss)
    obs = np.where(miss, np.nan, y)
    out = {}
    # 全店の前年同月比（24か月目÷12か月目）
    out["yoy"] = {"本当の売上": y[:, 23].sum() / y[:, 11].sum() - 1,
                  "前の値で埋める": lf[:, 23].sum() / lf[:, 11].sum() - 1,
                  "報告のあった店だけ": np.nanmean(obs[:, 23]) / np.nanmean(obs[:, 11]) - 1,
                  "前後を線でつなぐ": np.nanmean(li[:, 23]) / np.nanmean(li[:, 11]) - 1}
    # 店ごとの前の月との変化（2〜24か月目）
    ch_true = y[:, 1:] / y[:, :-1] - 1
    ch_lf = lf[:, 1:] / lf[:, :-1] - 1
    out["zero_true"] = float((np.abs(ch_true) < 1e-12).mean())
    out["zero_lf"] = float((np.abs(ch_lf) < 1e-12).mean())
    out["big_true"] = float((np.abs(ch_true) >= 0.10).mean())
    out["big_lf"] = float((np.abs(ch_lf) >= 0.10).mean())
    out["sd_true"] = float(ch_true.std()); out["sd_lf"] = float(ch_lf.std())
    out["miss_share_2_24"] = float(miss[:, 1:].mean())
    # 改装した店：13か月目・14か月目の、12か月目からの上がり（店の平均）
    r = renov
    for k, m in [("renov13", 12), ("renov14", 13), ("renov18", 17)]:
        out[k] = {"本当の売上": float((y[r, m] / y[r, 11] - 1).mean()),
                  "前の値で埋める": float((lf[r, m] / lf[r, 11] - 1).mean())}
    # 改装しなかった店の同じ比（会社全体の伸びの分）を引いて、改装の分だけを見る
    nr = ~renov
    for k, m in [("base13", 12), ("base14", 13), ("base18", 17)]:
        out[k] = {"本当の売上": float((y[nr, m] / y[nr, 11] - 1).mean()),
                  "前の値で埋める": float((lf[nr, m] / lf[nr, 11] - 1).mean())}
    out["total"] = {"本当の売上": y.sum(0), "前の値で埋める": lf.sum(0),
                    "報告のあった店だけ": np.nanmean(obs, 0) * S, "前後を線でつなぐ": np.nanmean(li, 0) * S}
    return out, lf, li


def main():
    rng = np.random.default_rng(SEED)
    # 1) 基本の置き方：2つのやめ方 × 500回
    res = {}
    keep_total = {}
    example = None
    for mech in MECH:
        r2 = np.random.default_rng(SEED * 10 + (mech == "down"))
        rows = []
        tot = {w: [] for w in WAYS}
        for rep in range(REPS):
            y, trend, renov = make_sales(r2)
            miss, who = make_missing(r2, trend, mech=mech)
            o, lf, li = stats(y, miss, renov)
            if mech == "random" and rep == 0:
                example = (y, miss, lf, li, renov, who)
            row = {f"yoy_{w}": o["yoy"][w] for w in WAYS}
            row.update({k: o[k] for k in ["zero_true", "zero_lf", "big_true", "big_lf", "sd_true", "sd_lf",
                                          "miss_share_2_24"]})
            for k in ["renov13", "renov14", "renov18", "base13", "base14", "base18"]:
                for w in ["本当の売上", "前の値で埋める"]:
                    row[f"{k}_{w}"] = o[k][w]
            rows.append(row)
            for w in WAYS:
                tot[w].append(o["total"][w] / o["total"]["本当の売上"][0])
        d = pd.DataFrame(rows)
        res[mech] = d
        keep_total[mech] = {w: np.mean(tot[w], 0) for w in WAYS}

    base = {}
    for mech, d in res.items():
        b = {"yoy_mean": {w: round(float(d[f"yoy_{w}"].mean()), 4) for w in WAYS},
             "yoy_p10": {w: round(float(d[f"yoy_{w}"].quantile(.1)), 4) for w in WAYS},
             "yoy_p90": {w: round(float(d[f"yoy_{w}"].quantile(.9)), 4) for w in WAYS},
             "yoy_gap_points": {w: round(float((d[f"yoy_{w}"] - d["yoy_本当の売上"]).mean() * 100), 2) for w in WAYS[1:]},
             "miss_share_2_24": round(float(d["miss_share_2_24"].mean()), 4),
             "zero_change_share": {"本当の売上": round(float(d.zero_true.mean()), 4),
                                   "前の値で埋める": round(float(d.zero_lf.mean()), 4)},
             "change_ge_10pct_share": {"本当の売上": round(float(d.big_true.mean()), 4),
                                       "前の値で埋める": round(float(d.big_lf.mean()), 4)},
             "change_sd": {"本当の売上": round(float(d.sd_true.mean()), 4),
                           "前の値で埋める": round(float(d.sd_lf.mean()), 4)}}
        for k in ["13", "14", "18"]:
            b[f"renov_minus_base_{k}"] = {w: round(float((d[f"renov{k}_{w}"] - d[f"base{k}_{w}"]).mean()), 4)
                                         for w in ["本当の売上", "前の値で埋める"]}
        base[mech] = b
    pd.DataFrame([{"やめ方": MECH[m], "扱い方": w, "前年同月比の平均": base[m]["yoy_mean"][w],
                   "10%点": base[m]["yoy_p10"][w], "90%点": base[m]["yoy_p90"][w],
                   "本当との差（ポイント）": base[m]["yoy_gap_points"].get(w, 0.0)}
                  for m in MECH for w in WAYS]).to_csv(RES / "yoy_by_way.csv", index=False)

    # 2) 確かめ：抜け × やめた店 × 会社全体の伸び × やめ方（72通り、各100回）
    rob = []
    for mech in MECH:
        for q in [0.0, 0.1, 0.2, 0.4]:
            for dd in [0.0, 0.15, 0.30]:
                for g in [0.0, 0.01, 0.02]:
                    r3 = np.random.default_rng(SEED * 1000 + int(q * 100) * 10000 + int(dd * 100) * 100
                                               + int(g * 1000) + (mech == "down") * 7)
                    acc = []
                    for rep in range(100):
                        y, trend, renov = make_sales(r3, g)
                        miss, _ = make_missing(r3, trend, q, dd, mech)
                        o, _, _ = stats(y, miss, renov)
                        acc.append([o["yoy"][w] for w in WAYS] + [o["zero_lf"], o["miss_share_2_24"], o["big_lf"],
                                    o["big_true"], o["renov13"]["前の値で埋める"] - o["base13"]["前の値で埋める"],
                                    o["renov13"]["本当の売上"] - o["base13"]["本当の売上"]])
                    a = np.mean(acc, 0)
                    rob.append({"やめ方": MECH[mech], "抜けの割合": q, "やめた店の割合": dd, "会社全体の伸び（月）": g,
                                "前年同月比：本当": round(a[0], 4), "前年同月比：前の値で埋める": round(a[1], 4),
                                "前年同月比：報告のあった店だけ": round(a[2], 4), "前年同月比：線でつなぐ": round(a[3], 4),
                                "前の値で埋める－本当（ポイント）": round((a[1] - a[0]) * 100, 2),
                                "報告のあった店だけ－本当（ポイント）": round((a[2] - a[0]) * 100, 2),
                                "変化0の割合（前の値で埋める）": round(a[4], 4), "抜けた店×月の割合": round(a[5], 4),
                                "10%以上動いた割合（前の値で埋める）": round(a[6], 4), "10%以上動いた割合（本当）": round(a[7], 4),
                                "改装の13か月目の上がり（前の値で埋める）": round(a[8], 4),
                                "改装の13か月目の上がり（本当）": round(a[9], 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    rr = rob[(rob["抜けの割合"] > 0) | (rob["やめた店の割合"] > 0)]
    rand = rr[rr["やめ方"] == MECH["random"]]
    down = rr[(rr["やめ方"] == MECH["down"]) & (rr["やめた店の割合"] > 0)]
    nodrop = rr[rr["やめた店の割合"] == 0]
    grow = rr[rr["会社全体の伸び（月）"] > 0]
    robsum = {
        "zero_minus_missing_max_abs": round(float((rr["変化0の割合（前の値で埋める）"] - rr["抜けた店×月の割合"]).abs().max()), 4),
        "random_locf_gap_min": float(rand["前の値で埋める－本当（ポイント）"].min()),
        "random_locf_gap_max": float(rand["前の値で埋める－本当（ポイント）"].max()),
        "random_locf_gap_growth_only_max": float(rand[rand["会社全体の伸び（月）"] > 0]["前の値で埋める－本当（ポイント）"].max()),
        "random_drop_gap_abs_max": float(rand["報告のあった店だけ－本当（ポイント）"].abs().max()),
        "down_locf_gap_min": float(down["前の値で埋める－本当（ポイント）"].min()),
        "down_locf_gap_max": float(down["前の値で埋める－本当（ポイント）"].max()),
        "down_drop_gap_min": float(down["報告のあった店だけ－本当（ポイント）"].min()),
        "down_drop_gap_max": float(down["報告のあった店だけ－本当（ポイント）"].max()),
        "nodrop_locf_gap_abs_max": float(nodrop["前の値で埋める－本当（ポイント）"].abs().max()),
        "growth_configs_with_dropouts_n": int(((grow["やめた店の割合"] > 0)).sum()),
        "g0_with_drop_random_locf_gap_abs_max": float(rand[(rand["会社全体の伸び（月）"] == 0) & (rand["やめた店の割合"] > 0)]
                                                      ["前の値で埋める－本当（ポイント）"].abs().max()),
        "down_g0_locf_gap_min": float(down[down["会社全体の伸び（月）"] == 0]["前の値で埋める－本当（ポイント）"].min()),
        "down_g0_locf_gap_max": float(down[down["会社全体の伸び（月）"] == 0]["前の値で埋める－本当（ポイント）"].max()),
        "down_growth_locf_gap_min": float(down[down["会社全体の伸び（月）"] > 0]["前の値で埋める－本当（ポイント）"].min()),
        "down_growth_locf_gap_max": float(down[down["会社全体の伸び（月）"] > 0]["前の値で埋める－本当（ポイント）"].max()),
        "nodrop_drop_gap_abs_max": float(nodrop["報告のあった店だけ－本当（ポイント）"].abs().max()),
        "n_configs_with_missing": int(len(rr)),
        "renov13_locf_over_true_min": round(float((rr["改装の13か月目の上がり（前の値で埋める）"] / rr["改装の13か月目の上がり（本当）"]).min()), 4),
        "renov13_locf_over_true_max": round(float((rr["改装の13か月目の上がり（前の値で埋める）"] / rr["改装の13か月目の上がり（本当）"]).max()), 4),
    }

    # 例の1回分のデータ
    y, miss, lf, li, renov, who = example
    rows = []
    for i in range(S):
        for t in range(T):
            rows.append({"store_id": i + 1, "month": t + 1, "renovated": int(renov[i]), "stopped": int(i in set(who)),
                         "sales_true": round(float(y[i, t]), 2),
                         "sales_reported": "" if miss[i, t] else round(float(y[i, t]), 2),
                         "filled_previous": round(float(lf[i, t]), 2),
                         "filled_line": "" if np.isnan(li[i, t]) else round(float(li[i, t]), 2)})
    pd.DataFrame(rows).to_csv(DATA / "stores_example.csv", index=False)

    out = {"setup": {"stores": S, "months": T, "growth_per_month": G, "trend_sd": TREND_SD, "noise_sd": NOISE,
                     "missing_random": Q, "stopped_share": D, "renovated": RENOV, "renov_step": STEP, "reps": REPS},
           "base": base, "robustness_summary": robsum,
           "example": {"stopped_stores": int(len(who)), "missing_share_2_24": round(float(miss[:, 1:].mean()), 4)}}
    json.dump(out, open(RES / "a973_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の店（改装した店・途中でやめた店）の売上の線
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.9))
    t = np.arange(1, T + 1)
    i_ren = int(np.where(renov & (miss[:, 12] | miss[:, 13]) & ~np.isin(np.arange(S), who))[0][0])
    def stop_col(i):
        tail = np.cumsum(~miss[i][::-1])[::-1] == 0          # その月から後に報告がない
        return int(np.argmax(tail))
    stopped = [i for i in who if 8 <= stop_col(i) <= 14]
    i_stop = int(stopped[0]) if stopped else int(who[0])
    for ax, i, ttl in [(axs[0], i_ren, "改装した店（13か月目から+15%）"), (axs[1], i_stop, "途中で報告をやめた店")]:
        ax.plot(t, y[i], color=GRAY, lw=1.5, label="本当の売上")
        ax.plot(t, lf[i], color=ORANGE, lw=1.6, drawstyle="steps-post", label="前の値で埋める")
        ax.scatter(t[~miss[i]], y[i, ~miss[i]], s=16, color=BLUE, zorder=3, label="報告のあった月")
        ax.scatter(t[miss[i]], lf[i, miss[i]], s=22, facecolor="white", edgecolor=ORANGE, zorder=3, label="埋めた月")
        ax.set_xlabel("月"); ax.set_ylabel("売上（万円）"); ax.set_title(f"{ttl}・店{i + 1}", fontsize=11.5)
        ax.set_xticks([1, 6, 12, 18, 24])
    axs[0].axvline(13, color=INK, lw=0.7, ls=":")
    axs[1].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("前の値で埋めると、抜けた月は「変化なし」になり、上がった月は次に報告した月まで遅れて見える（例の1回分）", fontsize=12)
    fig.tight_layout()
    save(fig, "a973_example_stores.png", SRC)

    # 図2：全店の売上（1か月目＝1）の線、2つのやめ方
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    colw = {"本当の売上": INK, "前の値で埋める": ORANGE, "報告のあった店だけ": BLUE, "前後を線でつなぐ": GREEN}
    for ax, mech in zip(axs, MECH):
        for w in WAYS:
            ax.plot(t, keep_total[mech][w], color=colw[w], lw=2 if w == "本当の売上" else 1.5,
                    ls="--" if w == "前後を線でつなぐ" else "-", label=w)
        ax.set_title(f"{MECH[mech]}（500回の平均）", fontsize=11.5); ax.set_xlabel("月"); ax.set_xticks([1, 6, 12, 18, 24])
        yy = base[mech]["yoy_mean"]
        ax.text(0.02, 0.97, "前年同月比（24か月目÷12か月目）\n" + "\n".join(f"{w}：{yy[w] * 100:+.1f}%" for w in WAYS),
                transform=ax.transAxes, va="top", fontsize=8.5)
    axs[0].set_ylabel("全店の売上の合計（1か月目＝1）")
    axs[1].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("やめた店を前の値で止めると伸びは小さく、報告のあった店だけで比べると伸びの低い店がやめたとき大きく見える", fontsize=12)
    fig.tight_layout()
    save(fig, "a973_total.png", SRC)

    # 図3：確かめ。前年同月比のずれ（前の値で埋める・報告のあった店だけ）を、やめた店の割合ごとに
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    for ax, mech in zip(axs, MECH.values()):
        d = rob[(rob["やめ方"] == mech) & (rob["会社全体の伸び（月）"] == 0.01)]
        for col, c, mk in [("前の値で埋める－本当（ポイント）", ORANGE, "o"), ("報告のあった店だけ－本当（ポイント）", BLUE, "s")]:
            for q, ls in [(0.0, ":"), (0.2, "-"), (0.4, "--")]:
                dq = d[d["抜けの割合"] == q]
                ax.plot(dq["やめた店の割合"] * 100, dq[col], marker=mk, color=c, ls=ls, lw=1.3,
                        label=f"{col.split('－')[0]}（抜け{int(q * 100)}%）")
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_title(f"{mech}（会社全体の伸び月1%）", fontsize=11.5); ax.set_xlabel("途中で報告をやめた店の割合（%）")
        ax.set_xticks([0, 15, 30])
    axs[0].set_ylabel("前年同月比の本当とのずれ（ポイント）")
    h, l = axs[0].get_legend_handles_labels()
    fig.suptitle("前年同月比のずれは、ところどころの抜けよりも、途中でやめた店の数とやめ方で決まる（各100回の平均）", fontsize=12)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.legend(h, l, frameon=False, fontsize=8.5, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0))
    save(fig, "a973_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
