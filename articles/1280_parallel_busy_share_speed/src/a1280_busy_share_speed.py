"""1280 1つあたりの働いていた時間の割合が高いことは、全体が速いことを意味するのか？（架空のデータ）

架空のアプリの処理。中身の仕事の量の合計は1,000秒分（どの置き方でも同じ）。
これを M 個の仕事に分け（大きさは乱数で散らばる）、同時に動かす数 W の所で処理する。空いた所が次の仕事を取りにいく。
置き方：
  分ける手間：仕事1つごとに o 秒（受け取って渡す手間。働いていた時間に数える）
  1か所しかない置き場所：仕事ごとに大きさの s の割合は、置き場所を1つずつしか使えない（使っている所が終わるまで待つ）
  待ち方：回りながら待つ（待つ時間も働いていた時間に数える）か、休んで待つ（数えない）
働いていた時間の割合＝働いていた時間の合計÷(W×全体の時間)。全体の時間＝最後の仕事が終わった時刻。
すべてシミュレーションで、実機では測っていない。
"""
import json
import time
import heapq
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1280
SRC = "架空のアプリの処理のシミュレーション（作成者が乱数で作成、seed 1280）"
WORK = 1000.0
WS = [2, 4, 8, 16, 32, 64]
FS = [1, 4, 16, 64]               # 仕事の数＝W×f
O_SETS = {"low": [0.001, 0.01, 0.05], "base": [0.01, 0.1, 0.5], "high": [0.1, 0.5, 2.0]}
SS = [0.0, 0.02, 0.1]
SIGMAS = [0.2, 0.5, 1.0]
BASE_SIGMA = 0.5


def chunks(rng, m, sigma):
    x = rng.lognormal(0, sigma, m)
    return x / x.sum() * WORK


def simulate(size, w, o, s, spin):
    """全体の時間・働いていた時間の合計・中身の仕事の時間・分ける手間・待ちの時間を返す"""
    m = len(size)
    ev = []
    seq = 0
    for k in range(w):
        heapq.heappush(ev, (0.0, seq, 0, k, 0.0)); seq += 1
    nxt = 0
    busy = 0.0
    wait_total = 0.0
    lock_free = 0.0
    end = 0.0
    while ev:
        t, _, kind, k, sz = heapq.heappop(ev)
        if kind == 0:                     # 空いた所が次を取りにいく
            end = max(end, t)
            if nxt < m:
                sz = size[nxt]; nxt += 1
                par = o + (1 - s) * sz
                busy += par
                if s > 0:
                    heapq.heappush(ev, (t + par, seq, 1, k, sz))
                else:
                    heapq.heappush(ev, (t + par, seq, 0, k, 0.0))
                seq += 1
        else:                             # 置き場所を使いにいく
            start = max(t, lock_free)
            wt = start - t
            wait_total += wt
            if spin:
                busy += wt
            busy += s * sz
            lock_free = start + s * sz
            heapq.heappush(ev, (lock_free, seq, 0, k, 0.0)); seq += 1
    return {"total_sec": end, "busy_sec": busy, "overhead_sec": o * m, "wait_sec": wait_total}


def run_set(rng, sigma, oset):
    rows = []
    for w in WS:
        for f in FS:
            size = chunks(rng, w * f, sigma)
            for o in oset:
                for s in SS:
                    for spin in ([False] if s == 0 else [False, True]):
                        r = simulate(size, w, o, s, spin)
                        r.update({"w": w, "chunks": w * f, "overhead_per_chunk": o, "shared_part": s,
                                  "wait_kind": "none" if s == 0 else ("spin" if spin else "sleep")})
                        rows.append(r)
    d = pd.DataFrame(rows)
    d["busy_share"] = d.busy_sec / (d.w * d.total_sec)
    d["useful_share"] = WORK / (d.w * d.total_sec)
    d["speed_vs_one"] = WORK / d.total_sec           # 中身の仕事を1か所で手間なしに動かしたときの何倍速いか
    return d


def pair_agree(d, col="busy_share"):
    """col が高いほうが全体の時間も短い組の割合（col が同じ組は除く）"""
    a = d[col].to_numpy(); t = d.total_sec.to_numpy()
    i, j = np.triu_indices(len(d), 1)
    da = a[i] - a[j]; dt = t[i] - t[j]
    ok = (np.abs(da) > 1e-9) & (np.abs(dt) > 1e-9)
    return float(((da[ok] > 0) == (dt[ok] < 0)).mean()), int(ok.sum())


def rank_corr(a, b):
    ra = pd.Series(a).rank().to_numpy(); rb = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def summarize(d):
    out = {}
    out["pair_agree_all"], out["pairs_all"] = pair_agree(d)
    same = [pair_agree(g) for _, g in d.groupby("w")]
    out["pair_agree_same_w_mean"] = float(np.mean([x[0] for x in same]))
    out["pair_agree_same_w_min"] = float(np.min([x[0] for x in same]))
    out["pair_agree_same_w_max"] = float(np.max([x[0] for x in same]))
    out["rank_corr_busy_speed"] = rank_corr(d.busy_share, d.speed_vs_one)
    out["rank_corr_useful_speed"] = rank_corr(d.useful_share, d.speed_vs_one)
    out["share_busy_ge_95"] = float((d.busy_share >= 0.95).mean())
    hi = d[d.busy_share >= 0.95]; lo = d[d.busy_share < 0.8]
    out["speed_median_busy_ge_95"] = float(hi.speed_vs_one.median()) if len(hi) else None
    out["speed_median_busy_lt_80"] = float(lo.speed_vs_one.median()) if len(lo) else None
    fast = d.nsmallest(max(1, len(d) // 10), "total_sec")
    out["busy_share_median_fastest10pct"] = float(fast.busy_share.median())
    out["busy_share_median_all"] = float(d.busy_share.median())
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base = run_set(rng, BASE_SIGMA, O_SETS["base"])
    cols = ["w", "chunks", "overhead_per_chunk", "shared_part", "wait_kind", "total_sec", "busy_share", "useful_share",
            "speed_vs_one", "busy_sec", "overhead_sec", "wait_sec"]
    base = base[cols].round(4)
    base.to_csv(RES / "base_configs.csv", index=False)
    summ = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in summarize(base).items()}

    # 例の5つ
    ex_def = [("A 4か所・ふつうに分ける", 4, 256, 0.01, 0.0, "none"),
              ("B 32か所・粗く分ける", 32, 32, 0.01, 0.0, "none"),
              ("C 32か所・細かく分けすぎ", 32, 2048, 0.5, 0.0, "none"),
              ("D 32か所・置き場所を回りながら待つ", 32, 128, 0.01, 0.1, "spin"),
              ("E 32か所・置き場所を休んで待つ", 32, 128, 0.01, 0.1, "sleep")]
    ex = []
    for lab, w, m, o, s, wk in ex_def:
        r = base[(base.w == w) & (base.chunks == m) & (base.overhead_per_chunk == o) & (base.shared_part == s) &
                 (base.wait_kind == wk)].iloc[0].to_dict()
        r["label"] = lab
        ex.append(r)
    ex = pd.DataFrame(ex)[["label"] + cols]
    ex.to_csv(RES / "examples.csv", index=False)

    # 確かめ：大きさの散らばり×分ける手間の範囲の9通り
    grng = np.random.default_rng(SEED + 1)
    grows = []
    for sg in SIGMAS:
        for on, oset in O_SETS.items():
            d = run_set(grng, sg, oset)
            sm = summarize(d)
            sm.update({"sigma": sg, "overhead_set": on, "n_configs": len(d)})
            grows.append(sm)
    grid = pd.DataFrame(grows)
    grid = grid[["sigma", "overhead_set", "n_configs"] + [c for c in grid.columns if c not in ("sigma", "overhead_set", "n_configs")]].round(4)
    grid.to_csv(RES / "grid.csv", index=False)

    # 1回分のデータ（基本の置き方・全部の置き方）
    base.to_csv(DATA / "configs_base.csv", index=False)

    main_json = {
        "setting": {"work_sec": WORK, "ws": WS, "chunks_per_w": FS, "overhead_base": O_SETS["base"], "shared_part": SS,
                    "sigma": BASE_SIGMA, "n_configs": int(len(base))},
        "base": summ,
        "examples": ex.round(4).to_dict(orient="records"),
        "grid_range": {c: [float(grid[c].min()), float(grid[c].max())] for c in
                       ["pair_agree_all", "pair_agree_same_w_mean", "rank_corr_busy_speed", "rank_corr_useful_speed",
                        "busy_share_median_fastest10pct", "busy_share_median_all"]},
    }
    with open(RES / "a1280_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：働いていた時間の割合と速さ（基本の置き方の全部）
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    cmap = {2: "#c9dcf3", 4: LIGHT, 8: "#7fb0e6", 16: BLUE, 32: "#1b4f8f", 64: INK}
    for w in WS:
        d = base[base.w == w]
        ax.scatter(d.busy_share * 100, d.speed_vs_one, s=14, color=cmap[w], label=f"{w}か所", alpha=0.85)
    ax.set_yscale("log")
    ax.set_yticks([2, 3, 5, 10, 20, 30, 50])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlabel("1つあたりの働いていた時間の割合（%）")
    ax.set_ylabel("速さ（手間なしの1か所の何倍、対数）")
    ax.set_title(f"基本の置き方{len(base)}通り：働いていた割合と速さ")
    ax.legend(frameon=False, fontsize=8, title="同時に動かす数", title_fontsize=8, ncol=2)
    save(fig, "a1280_busy_vs_speed.png", SRC)

    # 図2：例の5つ（働いていた割合と速さ）
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    y = np.arange(len(ex))[::-1]
    axes[0].barh(y, ex.busy_share * 100, color=[GRAY, BLUE, ORANGE, ORANGE, GREEN])
    axes[0].set_yticks(y); axes[0].set_yticklabels(ex.label, fontsize=9)
    axes[0].set_xlim(0, 110)
    axes[0].set_xlabel("働いていた時間の割合（%）")
    for yy, v in zip(y, ex.busy_share * 100):
        axes[0].text(v + 1, yy, f"{v:.2f}", va="center", fontsize=8)
    axes[1].barh(y, ex.speed_vs_one, color=[GRAY, BLUE, ORANGE, ORANGE, GREEN])
    axes[1].set_yticks(y); axes[1].set_yticklabels([])
    axes[1].set_xlim(0, ex.speed_vs_one.max() * 1.2)
    axes[1].set_xlabel("速さ（手間なしの1か所の何倍）")
    for yy, v in zip(y, ex.speed_vs_one):
        axes[1].text(v + 0.2, yy, f"{v:.2f}", va="center", fontsize=8)
    fig.suptitle("例の5つ：働いていた割合と速さ（仕事の量は同じ1,000秒分）", y=1.03)
    save(fig, "a1280_examples.png", SRC, y=-0.04)

    # 図3：確かめ9通りで「割合が高いほうが速い」組の割合
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    x = np.arange(len(grid))
    ax.bar(x - 0.2, grid.pair_agree_all * 100, 0.4, color=BLUE, label="すべての組")
    ax.bar(x + 0.2, grid.pair_agree_same_w_mean * 100, 0.4, color=ORANGE, label="同時に動かす数が同じ組（平均）")
    ax.axhline(50, color=GRAY, ls="--", lw=1)
    ax.set_ylim(0, 115)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    lab = {"low": "手間小", "base": "手間中", "high": "手間大"}
    ax.set_xticks(x); ax.set_xticklabels([f"{r.sigma:g}\n{lab[r.overhead_set]}" for r in grid.itertuples()], fontsize=9)
    ax.set_xlabel("仕事の大きさの散らばり／分ける手間の範囲")
    ax.set_ylabel("割合が高いほうが速かった組（%）")
    ax.set_title("9通りの置き方：働いていた割合が高いほうが速かった組の割合")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
    save(fig, "a1280_grid_pairs.png", SRC, y=-0.06)

    print(ex.to_string())
    print(json.dumps(main_json["base"], ensure_ascii=False, indent=1))
    print(grid.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
