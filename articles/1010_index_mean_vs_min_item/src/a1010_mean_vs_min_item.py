"""1010 平均で合わせるか、いちばん低い項目で合わせるかで、何が変わるのか？（架空のデータ）

架空のチェーン店300店の運営スコア。5項目（清潔さ・待ち時間の短さ・品ぞろえ・接客・会計の正確さ、各100点満点）を
毎月の調査で採点する。店ごとに項目の本当の点を置き、毎月の点は本当の点＋その月の測り方の振れ。
合計を「5項目の平均」で出すか「いちばん低い項目の点」で出すかで、上位の店・月ごとの安定・当たりがどう変わるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1010
SRC = "架空のチェーン店の運営スコア（作成者が乱数で作成、seed 1010）"
rng = np.random.default_rng(SEED)

ITEMS = ["清潔さ", "待ち時間の短さ", "品ぞろえ", "接客", "会計の正確さ", "店内の案内", "駐車場の使いやすさ", "営業時間の守り方"]
BASE = {"n_items": 5, "r": 0.6, "sd_err": 6.0}
N_STORE, TOP = 300, 30


def make(rng, n=N_STORE, n_items=5, r=0.6, sd_err=6.0):
    g = rng.standard_normal((n, 1))
    s = rng.standard_normal((n, n_items))
    true = 70 + 10 * (np.sqrt(r) * g + np.sqrt(1 - r) * s)
    obs = [np.clip(np.round(true + sd_err * rng.standard_normal(true.shape)), 0, 100) for _ in range(2)]
    return true, obs[0], obs[1]


def topset(v, k=TOP):
    return set(np.argsort(-v, kind="stable")[:k])


def rc(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def hit(a, b):
    return len(topset(a) & topset(b)) / TOP


def measure(true, o1, o2):
    tm, tn = true.mean(1), true.min(1)
    om, on = o1.mean(1), o1.min(1)
    om2, on2 = o2.mean(1), o2.min(1)
    # いちばん低い項目（同点は先の項目）
    am_true, am1, am2 = true.argmin(1), o1.argmin(1), o2.argmin(1)
    return {"rank_corr_mean_vs_min": rc(om, on), "top30_overlap_mean_vs_min": hit(om, on),
            "stab_rank_mean": rc(om, om2), "stab_rank_min": rc(on, on2),
            "stab_top30_mean": hit(om, om2), "stab_top30_min": hit(on, on2),
            "hit_mean_truemean": hit(om, tm), "hit_min_truemean": hit(on, tm),
            "hit_mean_truemin": hit(om, tn), "hit_min_truemin": hit(on, tn),
            "rank_mean_truemin": rc(om, tn), "rank_min_truemin": rc(on, tn),
            "bias_min": float((on - tn).mean()), "bias_mean": float((om - tm).mean()),
            "argmin_obs_eq_true": float((am1 == am_true).mean()), "argmin_same_next_month": float((am1 == am2).mean())}


def run(reps, seed0, **kw):
    rows = [measure(*make(np.random.default_rng(seed0 + r), **kw)) for r in range(reps)]
    return pd.DataFrame(rows)


def main():
    # 例の1回分
    true, o1, o2 = make(rng, **BASE)
    names = ITEMS[:BASE["n_items"]]
    df = pd.DataFrame({"store_id": np.arange(1, N_STORE + 1)})
    for j, nm in enumerate(names):
        df[f"true_{nm}"] = np.round(true[:, j], 2)
    for j, nm in enumerate(names):
        df[f"m1_{nm}"] = o1[:, j].astype(int)
    for j, nm in enumerate(names):
        df[f"m2_{nm}"] = o2[:, j].astype(int)
    df.to_csv(DATA / "stores_example.csv", index=False)
    om, on = o1.mean(1), o1.min(1)
    a, b = topset(om), topset(on)
    ex = {"top30_both": len(a & b), "top30_only_mean": len(a - b), "top30_only_min": len(b - a),
          **{k: round(v, 4) for k, v in measure(true, o1, o2).items()}}
    # 平均が上位30店に入り、いちばん低い項目では入らない店のうち、最も平均の高い店の例
    only_mean = sorted(a - b, key=lambda i: -om[i])
    only_min = sorted(b - a, key=lambda i: -on[i])
    def prof(i):
        return {"store_id": int(i + 1), "items_m1": dict(zip(names, o1[i].astype(int).tolist())),
                "mean_m1": round(float(om[i]), 1), "min_m1": int(on[i]),
                "rank_mean": int((om > om[i]).sum() + 1), "rank_min": int((on > on[i]).sum() + 1)}
    ex["example_only_mean"] = prof(only_mean[0])
    ex["example_only_min"] = prof(only_min[0])

    # 1) 基本の置き方で300回
    sim = run(300, SEED * 1000, **BASE)
    sim.round(5).to_csv(RES / "reps_300.csv", index=False)
    summ = sim.mean().round(4).to_dict()
    summ.update({f"{k}_p10": round(float(sim[k].quantile(.1)), 4) for k in ["hit_mean_truemin", "hit_min_truemin"]})
    summ.update({f"{k}_p90": round(float(sim[k].quantile(.9)), 4) for k in ["hit_mean_truemin", "hit_min_truemin"]})
    summ["share_reps_mean_better_on_truemin"] = round(float((sim.hit_mean_truemin > sim.hit_min_truemin).mean()), 4)
    summ["share_reps_min_better_on_truemin"] = round(float((sim.hit_min_truemin > sim.hit_mean_truemin).mean()), 4)

    # 2) 確かめ：測り方の振れ × 項目どうしの相関 × 項目の数（45通り、各60回）
    grid = []
    for sd in [0.0, 3.0, 6.0, 10.0, 15.0]:
        for r in [0.3, 0.6, 0.8]:
            for k in [3, 5, 8]:
                d = run(60, SEED * 7 + int(sd * 10) * 10000 + int(r * 10) * 100 + k, n_items=k, r=r, sd_err=sd).mean()
                grid.append({"sd_err": sd, "r": r, "n_items": k, **d.round(4).to_dict()})
    grid = pd.DataFrame(grid)
    grid["mean_minus_min_on_truemin"] = (grid.hit_mean_truemin - grid.hit_min_truemin).round(4)
    grid.to_csv(RES / "robustness.csv", index=False)
    noisy = grid[grid.sd_err > 0]
    g0 = grid[grid.sd_err == 0]
    rob = {"n_combos": int(len(grid)),
           "rank_corr_mean_vs_min_range": [float(grid.rank_corr_mean_vs_min.min()), float(grid.rank_corr_mean_vs_min.max())],
           "top30_overlap_range": [float(grid.top30_overlap_mean_vs_min.min()), float(grid.top30_overlap_mean_vs_min.max())],
           "n_noisy_combos": int(len(noisy)),
           "n_noisy_min_less_stable_rank": int((noisy.stab_rank_min < noisy.stab_rank_mean).sum()),
           "n_noisy_mean_beats_min_on_truemin": int((noisy.hit_mean_truemin > noisy.hit_min_truemin).sum()),
           "n_noisy_min_beats_mean_on_truemin": int((noisy.hit_min_truemin > noisy.hit_mean_truemin).sum()),
           "diff_on_truemin_range_noisy": [float(noisy.mean_minus_min_on_truemin.min()), float(noisy.mean_minus_min_on_truemin.max())],
           "sd0_hit_min_truemin_range": [float(g0.hit_min_truemin.min()), float(g0.hit_min_truemin.max())],
           "sd0_bias_min_maxabs": float(g0.bias_min.abs().max()),
           "bias_mean_range_all": [float(grid.bias_mean.min()), float(grid.bias_mean.max())],
           "n_mean_beats_sd10plus": int(((grid.sd_err >= 10) & (grid.hit_mean_truemin > grid.hit_min_truemin)).sum()),
           "n_mean_beats_sd6_r06plus": int(((grid.sd_err == 6) & (grid.r >= 0.6) & (grid.hit_mean_truemin > grid.hit_min_truemin)).sum()),
           "n_mean_beats_sd3": int(((grid.sd_err == 3) & (grid.hit_mean_truemin > grid.hit_min_truemin)).sum()),
           "sd0_hit_mean_truemin_range": [float(g0.hit_mean_truemin.min()), float(g0.hit_mean_truemin.max())],
           "sd0_stab_rank_min": float(g0.stab_rank_min.min()),
           "bias_min_range_noisy": [float(noisy.bias_min.min()), float(noisy.bias_min.max())],
           "argmin_obs_eq_true_range_noisy": [float(noisy.argmin_obs_eq_true.min()), float(noisy.argmin_obs_eq_true.max())],
           "argmin_same_next_month_range_noisy": [float(noisy.argmin_same_next_month.min()), float(noisy.argmin_same_next_month.max())],
           "min_beats_mean_combos": noisy[noisy.hit_min_truemin > noisy.hit_mean_truemin][
               ["sd_err", "r", "n_items", "hit_mean_truemin", "hit_min_truemin"]].to_dict("records"),
           "by_sd_r06_k5": grid[(grid.r == 0.6) & (grid.n_items == 5)][
               ["sd_err", "hit_mean_truemin", "hit_min_truemin", "stab_rank_mean", "stab_rank_min", "bias_min",
                "argmin_obs_eq_true"]].to_dict("records")}

    out = {"base": BASE, "true_item_mean": 70, "true_item_sd": 10, "items": ITEMS[:BASE["n_items"]], "n_stores": N_STORE, "top": TOP, "example": ex, "base_300reps": summ, "robustness": rob}
    json.dump(out, open(RES / "a1010_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の300店の平均といちばん低い項目
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    both = np.array([i in a and i in b for i in range(N_STORE)])
    oa = np.array([i in a and i not in b for i in range(N_STORE)])
    ob = np.array([i in b and i not in a for i in range(N_STORE)])
    rest = ~(both | oa | ob)
    ax.scatter(om[rest], on[rest], s=10, color=GRAY, alpha=.5, lw=0, label="どちらでも上位30店の外")
    ax.scatter(om[both], on[both], s=22, color=INK, lw=0, label=f"どちらでも上位30店（{int(both.sum())}店）")
    ax.scatter(om[oa], on[oa], s=26, color=BLUE, lw=0, label=f"平均だけで上位30店（{int(oa.sum())}店）")
    ax.scatter(om[ob], on[ob], s=26, color=ORANGE, lw=0, label=f"いちばん低い項目だけで上位30店（{int(ob.sum())}店）")
    ax.set_xlabel("5項目の平均（1か月目）"); ax.set_ylabel("いちばん低い項目の点（1か月目）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("平均といちばん低い項目で、上位30店の顔ぶれが変わる（例の300店）")
    save(fig, "a1010_scatter.png", SRC)

    # 図2：当たりと安定（300回の平均）
    fig, ax = plt.subplots(figsize=(7.8, 3.9))
    labels = ["本当の平均の上位30店を当てる", "本当のいちばん低い項目の上位30店を当てる", "翌月も上位30店に残る"]
    vm = [summ["hit_mean_truemean"], summ["hit_mean_truemin"], summ["stab_top30_mean"]]
    vn = [summ["hit_min_truemean"], summ["hit_min_truemin"], summ["stab_top30_min"]]
    y = np.arange(3)[::-1]
    ax.barh(y + 0.2, np.array(vm) * 100, height=0.38, color=BLUE, label="5項目の平均で並べる")
    ax.barh(y - 0.2, np.array(vn) * 100, height=0.38, color=ORANGE, label="いちばん低い項目で並べる")
    for yy, p, q in zip(y, vm, vn):
        ax.text(p * 100 + 1, yy + 0.2, f"{p*100:.1f}%", va="center", fontsize=8.5)
        ax.text(q * 100 + 1, yy - 0.2, f"{q*100:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlim(0, 100)
    ax.set_xlabel("上位30店のうちの割合（%、300回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    ax.set_title("いちばん低い項目の上位を当てたいときも、平均で並べたほうが少し当たった（振れ6点）", pad=28)
    save(fig, "a1010_hits.png", SRC)

    # 図3：測り方の振れと、本当のいちばん低い項目の上位30店の当たり（相関0.6）
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.7), sharey=True)
    for ax, k in zip(axes, [3, 5, 8]):
        g = grid[(grid.r == 0.6) & (grid.n_items == k)]
        ax.plot(g.sd_err, g.hit_mean_truemin * 100, "o-", color=BLUE, label="項目の平均で並べる" if k == 3 else None)
        ax.plot(g.sd_err, g.hit_min_truemin * 100, "o-", color=ORANGE, label="いちばん低い項目で並べる" if k == 3 else None)
        ax.set_title(f"項目{k}つ", fontsize=11); ax.set_xlabel("1か月の測り方の振れ（点）")
        ax.set_xticks([0, 3, 6, 10, 15]); ax.set_ylim(0, 105)
    axes[0].set_ylabel("本当のいちばん低い項目の\n上位30店を当てた割合（%）", linespacing=1.6)
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("振れが大きいほど、いちばん低い項目で並べた当たりは下がり、6点以上では平均を下回った（項目どうしの相関0.6）", fontsize=11)
    fig.tight_layout()
    save(fig, "a1010_noise.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:7000])


if __name__ == "__main__":
    main()
