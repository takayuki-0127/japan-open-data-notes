"""1165 毎日の差分だけを残す控えと、毎回全部を残す控えでは、量と戻すときに読む量はどう入れかわるのか？（架空のデータ）

作成者が置いた架空のアプリの保存データ 1,000GB（10MB の区切り10万個）。毎日、区切りの一部が書きかわる。
基本の書きかわり方：区切りの5%（よく書きかわる区切り）は1日30%、残りは1日0.5%の確率で書きかわる（1日に平均約2%）。
控えの取り方（全部の控えを F 日ごとに取り、その間の日は次のどちらか）：
  ・前日からの分（増分）：前の日の控えから書きかわった区切りだけ
  ・全部の控えからの分（差分）：最後の全部の控えから書きかわった区切りすべて
  ・F＝1 は毎日全部
過去28日のどの日の状態にも戻せるように、必要な控えを残す。
数えるもの：残している控えの量（毎日の平均・最大）、いちばん新しい日に戻すときに読む量（平均・最大）
確かめ：書きかわり方の形3通り×1日に書きかわる量3段×F（1・7・14・28日）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1165
SRC = "架空のアプリの保存データの書きかわり（作成者が置いた確率からの乱数、seed 1165）"
N_BLOCK, BLOCK_GB = 100_000, 0.01        # 10MB×10万＝1,000GB
DATA_GB = N_BLOCK * BLOCK_GB
KEEP = 28
DAYS, WARM = 336, 112                    # 113日目〜336日目（224日）を数える
FS = [1, 7, 14, 28]
PATTERNS = {"一様": (0.0, 0.0, 0.01975),          # (よく書きかわる区切りの割合, その確率, ほかの確率)
            "基本（5%が30%）": (0.05, 0.30, 0.005),
            "偏り強（2%が50%）": (0.02, 0.50, 0.00995)}
LEVELS = {"半分（約1%）": 0.5, "基本（約2%）": 1.0, "倍（約4%）": 2.0}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, hot_share, p_hot, p_cold, scale):
    """毎日の書きかわった区切りの数と、各日について「その日以前の d 日目から書きかわった数」を返す"""
    n_hot = int(round(N_BLOCK * hot_share))
    p = np.full(N_BLOCK, min(p_cold * scale, 1.0))
    p[:n_hot] = min(p_hot * scale, 1.0)
    last = np.full(N_BLOCK, -1, dtype=np.int32)     # 最後に書きかわった日
    daily = np.zeros(DAYS + 1, dtype=np.int64)
    lasts = np.zeros((DAYS + 1, N_BLOCK), dtype=np.int16)
    for d in range(1, DAYS + 1):
        ch = rng.random(N_BLOCK) < p
        daily[d] = ch.sum()
        last[ch] = d
        lasts[d] = last
    return daily, lasts


def evaluate(daily, lasts, F, kind):
    """kind: 'inc'（前日からの分）・'diff'（全部の控えからの分）。各日の残す量と戻すときに読む量（GB）"""
    full_day = lambda d: ((d - 1) // F) * F + 1          # 1日目・1+F日目…が全部の控え
    size = np.zeros(DAYS + 1)
    for d in range(1, DAYS + 1):
        f = full_day(d)
        if d == f:
            size[d] = DATA_GB
        elif kind == "inc":
            size[d] = daily[d] * BLOCK_GB
        else:
            size[d] = (lasts[d] > f).sum() * BLOCK_GB
    store, read = [], []
    for t in range(WARM + 1, DAYS + 1):
        lo = t - KEEP + 1
        f_lo = full_day(lo)
        if kind == "inc":
            keep = range(f_lo, t + 1)                        # 最も古い日の全部の控えから今日まで全部
        else:
            keep = set(range(lo, t + 1)) | {full_day(d) for d in range(lo, t + 1)}
        store.append(sum(size[d] for d in keep))
        f = full_day(t)
        if kind == "inc":
            read.append(size[f:t + 1].sum())
        else:
            read.append(DATA_GB + (size[t] if t != f else 0.0))
    return np.array(store), np.array(read), size


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    rows, base_series, diff_growth = [], {}, None
    gi = 0
    for pname, (hs, ph, pc) in PATTERNS.items():
        for lname, sc in LEVELS.items():
            gi += 1
            daily, lasts = simulate(np.random.default_rng(SEED * 100 + gi), hs, ph, pc, sc)
            dmean = daily[WARM + 1:].mean() * BLOCK_GB
            for F in FS:
                for kind in (["full"] if F == 1 else ["inc", "diff"]):
                    st, rd, size = evaluate(daily, lasts, F, "inc" if kind == "full" else kind)
                    row = {"pattern": pname, "level": lname, "full_every_days": F,
                           "kind": {"full": "毎日全部", "inc": "前日からの分", "diff": "全部の控えからの分"}[kind],
                           "daily_change_gb": r(dmean, 2),
                           "store_mean_gb": r(st.mean(), 1), "store_max_gb": r(st.max(), 1),
                           "store_ratio_to_data": r(st.mean() / DATA_GB, 3),
                           "read_mean_gb": r(rd.mean(), 1), "read_max_gb": r(rd.max(), 1),
                           "read_ratio_mean": r(rd.mean() / DATA_GB, 3), "read_ratio_max": r(rd.max() / DATA_GB, 3)}
                    rows.append(row)
                    if pname.startswith("基本") and lname.startswith("基本"):
                        base_series[(F, kind)] = (st, rd)
            if pname.startswith("基本") and lname.startswith("基本"):
                # 全部の控えからの分の大きさ：日数ごと（28日周期の平均）と、日数×1日の量
                g = []
                for k in range(1, 28):
                    v = [(lasts[f + k] > f).sum() * BLOCK_GB for f in range(WARM + 1, DAYS - 27, 28)]
                    g.append({"days_since_full": k, "diff_gb": r(np.mean(v), 1),
                              "days_times_daily_gb": r(k * dmean, 1),
                              "ratio": r(np.mean(v) / (k * dmean), 4)})
                diff_growth = pd.DataFrame(g)
                diff_growth.to_csv(RES / "base_diff_growth.csv", index=False)
                out["base_daily_change_gb"] = r(dmean, 2)
                out["base_daily_change_pct"] = r(dmean / DATA_GB * 100, 3)
                ex = pd.DataFrame({"day": np.arange(1, DAYS + 1), "changed_blocks": daily[1:],
                                   "changed_gb": np.round(daily[1:] * BLOCK_GB, 2)})
                ex.to_csv(DATA / "daily_changes_base.csv", index=False)
            print("sim", pname, lname, round(time.time() - T0, 1), flush=True)
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "grid.csv", index=False)
    base = tab[tab.pattern.str.startswith("基本") & tab.level.str.startswith("基本")].reset_index(drop=True)
    base.to_csv(RES / "base_schemes.csv", index=False)
    out["setting"] = {"data_gb": DATA_GB, "blocks": N_BLOCK, "block_mb": 10, "keep_days": KEEP,
                      "days_counted": DAYS - WARM, "patterns": {k: list(v) for k, v in PATTERNS.items()},
                      "levels": LEVELS,
                      "base_hot_blocks_gb": r(N_BLOCK * PATTERNS["基本（5%が30%）"][0] * BLOCK_GB, 1)}
    out["base"] = base.to_dict(orient="records")
    dg = diff_growth.set_index("days_since_full")
    out["base_diff_growth"] = {"k6_gb": dg.loc[6, "diff_gb"], "k6_naive_gb": dg.loc[6, "days_times_daily_gb"],
                               "k6_ratio": dg.loc[6, "ratio"], "k13_ratio": dg.loc[13, "ratio"],
                               "k27_gb": dg.loc[27, "diff_gb"], "k27_naive_gb": dg.loc[27, "days_times_daily_gb"],
                               "k27_ratio": dg.loc[27, "ratio"]}

    # 確かめのまとめ：F＝7 で、前日からの分と全部の控えからの分
    sm = []
    for (pn, ln), g in tab.groupby(["pattern", "level"], sort=False):
        i7 = g[(g.full_every_days == 7) & (g.kind == "前日からの分")].iloc[0]
        d7 = g[(g.full_every_days == 7) & (g.kind == "全部の控えからの分")].iloc[0]
        i28 = g[(g.full_every_days == 28) & (g.kind == "前日からの分")].iloc[0]
        d28 = g[(g.full_every_days == 28) & (g.kind == "全部の控えからの分")].iloc[0]
        f1 = g[g.full_every_days == 1].iloc[0]
        sm.append({"pattern": pn, "level": ln, "daily_change_gb": i7.daily_change_gb,
                   "full_store_gb": f1.store_mean_gb,
                   "inc7_store_gb": i7.store_mean_gb, "diff7_store_gb": d7.store_mean_gb,
                   "diff7_over_inc7_store": r(d7.store_mean_gb / i7.store_mean_gb, 3),
                   "inc7_read_max_gb": i7.read_max_gb, "diff7_read_max_gb": d7.read_max_gb,
                   "inc28_store_gb": i28.store_mean_gb, "diff28_store_gb": d28.store_mean_gb,
                   "diff28_over_inc28_store": r(d28.store_mean_gb / i28.store_mean_gb, 3),
                   "inc28_read_max_gb": i28.read_max_gb, "diff28_read_max_gb": d28.read_max_gb})
    sm = pd.DataFrame(sm)
    sm.to_csv(RES / "grid_summary.csv", index=False)
    nf = tab[tab.full_every_days > 1]
    out["grid"] = {"settings": int(len(sm)),
                   "diff7_over_inc7_min": r(sm.diff7_over_inc7_store.min(), 3),
                   "diff7_over_inc7_max": r(sm.diff7_over_inc7_store.max(), 3),
                   "diff28_over_inc28_min": r(sm.diff28_over_inc28_store.min(), 3),
                   "diff28_over_inc28_max": r(sm.diff28_over_inc28_store.max(), 3),
                   "inc28_read_ratio_max_min": r(nf[(nf.full_every_days == 28) & (nf.kind == "前日からの分")].read_ratio_max.min(), 3),
                   "inc28_read_ratio_max_max": r(nf[(nf.full_every_days == 28) & (nf.kind == "前日からの分")].read_ratio_max.max(), 3),
                   "diff28_read_ratio_max_min": r(nf[(nf.full_every_days == 28) & (nf.kind == "全部の控えからの分")].read_ratio_max.min(), 3),
                   "diff28_read_ratio_max_max": r(nf[(nf.full_every_days == 28) & (nf.kind == "全部の控えからの分")].read_ratio_max.max(), 3),
                   "store_ratio_nonfull_min": r(nf.store_ratio_to_data.min(), 3),
                   "store_ratio_nonfull_max": r(nf.store_ratio_to_data.max(), 3),
                   "full_store_ratio": r(tab[tab.full_every_days == 1].store_ratio_to_data.mean(), 3),
                   "diff_le_inc_store_count": int((sm.diff7_over_inc7_store < 1).sum() + (sm.diff28_over_inc28_store < 1).sum()),
                   "diff_read_le_inc_read_count": int((sm.diff7_read_max_gb <= sm.inc7_read_max_gb).sum()
                                                      + (sm.diff28_read_max_gb <= sm.inc28_read_max_gb).sum())}
    # 一様の形での 27日目の差分÷（日数×1日の量）
    out["headline"] = {"full_store_gb": base[base.full_every_days == 1].store_mean_gb.iloc[0]}
    b = base.set_index(["full_every_days", "kind"])
    for F in [7, 28]:
        for k, key in [("前日からの分", "inc"), ("全部の控えからの分", "diff")]:
            out["headline"][f"{key}{F}_store_gb"] = b.loc[(F, k), "store_mean_gb"]
            out["headline"][f"{key}{F}_read_max_gb"] = b.loc[(F, k), "read_max_gb"]
    print("grid", round(time.time() - T0, 1), flush=True)

    # 図1：残す量と戻すときに読む量（基本、横棒2枚）
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4), sharey=True)
    labs = ["毎日全部" if k == "毎日全部" else f"{F}日ごと全部＋{k}" for F, k in zip(base.full_every_days, base.kind)]
    colors = [INK if k == "毎日全部" else (BLUE if k == "前日からの分" else GREEN) for k in base.kind]
    yy = np.arange(len(base))[::-1]
    for ax, colname, ttl in [(axes[0], "store_mean_gb", "残している控えの量（GB、224日の平均）"),
                             (axes[1], "read_max_gb", "最新の日に戻すときに読む量（GB、最大）")]:
        ax.barh(yy, base[colname], color=colors)
        for y, v in zip(yy, base[colname]):
            ax.text(v + base[colname].max() * 0.01, y, f"{v:,.1f}", va="center", fontsize=8.5)
        ax.set_xlim(0, base[colname].max() * 1.22)
        ax.set_xlabel(ttl, fontsize=10)
    axes[1].axvline(DATA_GB, color=ORANGE, lw=1)
    axes[1].text(DATA_GB, len(base) - 0.45, " データの量1,000GB", color=ORANGE, fontsize=8)
    axes[0].set_yticks(yy)
    axes[0].set_yticklabels(labs, fontsize=9)
    fig.suptitle("残す量を減らす取り方ほど、戻すときに読む量が増える（基本の置き方）", fontsize=12)
    save(fig, "a1165_store_vs_read.png", SRC)

    # 図2：全部の控えからの分の大きさ（日数ごと）と、日数×1日の量
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(diff_growth.days_since_full, diff_growth.days_times_daily_gb, color=GRAY, ls="--",
            label="日数×1日に書きかわる量")
    ax.plot(diff_growth.days_since_full, diff_growth.diff_gb, color=BLUE, marker="o", ms=3.5,
            label="全部の控えからの分（実際）")
    ax.set_ylim(0, diff_growth.days_times_daily_gb.max() * 1.1)
    ax.set_xlabel("最後の全部の控えからの日数")
    ax.set_ylabel("控えの大きさ（GB）")
    ax.set_title("全部の控えからの分は、日数に比例しては増えない")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1165_diff_growth.png", SRC)

    # 図3：確かめ：全部の控えからの分÷前日からの分（残す量、F＝7・28）
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
    pats = list(PATTERNS)
    levs = list(LEVELS)
    cl = [LIGHT, BLUE, INK]
    for ax, F, colname in [(axes[0], 7, "diff7_over_inc7_store"), (axes[1], 28, "diff28_over_inc28_store")]:
        for j, ln in enumerate(levs):
            vals = [sm[(sm.pattern == pn) & (sm.level == ln)][colname].iloc[0] for pn in pats]
            ax.bar(np.arange(3) + (j - 1) * 0.26, vals, width=0.26, color=cl[j],
                   label=f"1日に書きかわる量：{ln}" if F == 7 else None)
            for i, v in enumerate(vals):
                ax.text(i + (j - 1) * 0.26, v + 0.03, f"{v:g}", ha="center", fontsize=7.5)
        ax.axhline(1, color=ORANGE, lw=1)
        ax.set_xticks(range(3))
        ax.set_xticklabels([p.replace("（", "\n（") for p in pats], fontsize=9)
        ax.set_title(f"{F}日ごとに全部を取るとき", fontsize=11)
        ax.set_xlabel("書きかわり方の形")
    axes[0].set_ylim(0, sm.diff28_over_inc28_store.max() * 1.12)
    axes[0].set_ylabel("残す量：全部の控えからの分÷前日からの分")
    fig.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, 1.04), ncol=3)
    fig.suptitle("9通りすべてで、全部の控えからの分のほうが残す量は多い", y=1.1, fontsize=12)
    save(fig, "a1165_grid_ratio.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1165_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
