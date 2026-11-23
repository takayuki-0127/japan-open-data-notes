"""1005 項目を足す前のそろえ方（標準化・順位・最大値）で、順位は変わるのか？（架空のデータ）

架空の掃除機30機種。項目は「吸う力（W）」「動く時間（分）」「重さ（kg、軽いほど良い）」「音（dB、静かなほど良い）」の4つ。
機種ごとに4項目の「もとの良さ」（平均0・標準偏差1）を作成者が置き、単位の違う測った値に直す。
そろえ方を4通り（標準化・順位・最大値で割る・最小〜最大で0〜1）に変え、均等に足した合計の順位を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1005
SRC = "架空の掃除機の測った値（作成者が乱数で作成、seed 1005）"
rng = np.random.default_rng(SEED)

ITEMS = ["吸う力", "動く時間", "重さ", "音"]
UNITS = ["W", "分", "kg", "dB"]
HIGHER = np.array([True, True, False, False])  # 大きいほど良いか
METHODS = ["標準化", "順位", "最大値で割る", "最小〜最大で0〜1"]
BASE = {"n": 30, "rho": 0.3, "skew": 0.35, "noise_sd": 3.0}
N_SET = 1000
N_SENS = 500
TOP = 5


def make_set(rng, n=30, rho=0.3, skew=0.35, noise_sd=3.0, **_):
    """機種ごとのもとの良さ z（4項目）と、測った値 x"""
    cov = np.full((4, 4), rho) + np.eye(4) * (1 - rho)
    z = rng.multivariate_normal(np.zeros(4), cov, n)
    x = np.empty_like(z)
    # 吸う力：150W前後で右に長い（skew が大きいほど長い）。skew=0 のときは左右対称（標準偏差は0.35×150W）
    x[:, 0] = 150 * np.exp(skew * z[:, 0]) if skew > 0 else 150 * (1 + 0.35 * z[:, 0])
    x[:, 1] = 40 + 8 * z[:, 1]            # 動く時間：40分前後
    x[:, 2] = 2.5 - 0.25 * z[:, 2]        # 重さ：2.5kg前後（軽いほど良い）
    x[:, 3] = 65 - noise_sd * z[:, 3]     # 音：65dB前後（静かなほど良い）
    return z, x


def ranks_desc(s):
    """大きい順の順位（同点は同じ順位、いちばん良い順位）"""
    return (s[:, None] < s[None, :]).sum(1) + 1


def normalize(x, method):
    s = np.empty_like(x)
    for j in range(x.shape[1]):
        v = x[:, j]
        if method == "標準化":
            t = (v - v.mean()) / v.std()
            s[:, j] = t if HIGHER[j] else -t
        elif method == "順位":
            r = np.argsort(np.argsort(v if HIGHER[j] else -v)) + 1  # 良いほど大きい（1〜n）
            s[:, j] = r
        elif method == "最大値で割る":
            s[:, j] = v / v.max() if HIGHER[j] else v.min() / v
        else:
            t = (v - v.min()) / (v.max() - v.min())
            s[:, j] = t if HIGHER[j] else 1 - t
    return s


def eff_weight(s):
    """均等に足した合計の散らばり（分散）のうち、各項目が占める分"""
    tot = s.mean(1)
    c = np.array([np.cov(s[:, j], tot, bias=True)[0, 1] / 4 for j in range(4)])
    return c / tot.var()


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def set_stats(z, x):
    truth = z.mean(1)
    true_top = set(np.argsort(-truth)[:TOP])
    tots = {m: np.round(normalize(x, m).mean(1), 9) for m in METHODS}
    rk = {m: ranks_desc(tots[m]) for m in METHODS}
    first = {m: set(np.where(rk[m] == 1)[0]) for m in METHODS}
    tops = {m: set(np.argsort(-tots[m], kind="stable")[:TOP]) for m in METHODS}
    out = {"first_same_all": int(all(len(f) == 1 for f in first.values()) and len(set.union(*first.values())) == 1),
           "n_distinct_first": len(set.union(*first.values())),
           "n_in_any_top5": len(set.union(*tops.values())),
           "max_rank_move": int((np.stack([rk[m] for m in METHODS]).max(0) - np.stack([rk[m] for m in METHODS]).min(0)).max())}
    for m in METHODS:
        out[f"top5_overlap_std_{m}"] = len(tops["標準化"] & tops[m])
        out[f"hit5_{m}"] = len(true_top & tops[m]) / TOP
        out[f"rho_truth_{m}"] = spearman(tots[m], truth)
        out[f"first_is_true_first_{m}"] = int(np.argmax(truth) in first[m] and len(first[m]) == 1)
        ew = eff_weight(normalize(x, m))
        for j, it in enumerate(ITEMS):
            out[f"eff_{m}_{it}"] = float(ew[j])
    return out


def run(rng, reps, **kw):
    return pd.DataFrame([set_stats(*make_set(rng, **kw)) for _ in range(reps)])


def main():
    # 例の30機種
    z, x = make_set(np.random.default_rng(SEED), **BASE)
    ex = pd.DataFrame(np.round(x, 2), columns=[f"{a}_{u}" for a, u in zip(ITEMS, UNITS)])
    ex.insert(0, "model_id", np.arange(1, BASE["n"] + 1))
    ex.to_csv(DATA / "vacuums_example.csv", index=False)
    exr = pd.DataFrame({"model_id": ex.model_id, "本当の良さ": np.round(z.mean(1), 4)})
    for m in METHODS:
        t = normalize(x, m).mean(1)
        exr[f"合計_{m}"] = np.round(t, 4)
        exr[f"順位_{m}"] = ranks_desc(np.round(t, 9))
    exr["本当の順位"] = ranks_desc(z.mean(1))
    exr.to_csv(RES / "example_ranks.csv", index=False)
    ex_top5 = {m: exr.sort_values(f"順位_{m}", kind="stable").model_id.head(5).tolist() for m in METHODS}
    ex_top5["本当の良さ"] = exr.sort_values("本当の順位").model_id.head(5).tolist()
    ex_one = {"top5": ex_top5,
              "first": {m: exr.loc[exr[f"順位_{m}"] == 1, "model_id"].tolist() for m in METHODS},
              "max_rank_move": int((exr[[f"順位_{m}" for m in METHODS]].max(1) - exr[[f"順位_{m}" for m in METHODS]].min(1)).max()),
              "max_rank_move_model": int(exr.model_id[(exr[[f"順位_{m}" for m in METHODS]].max(1) - exr[[f"順位_{m}" for m in METHODS]].min(1)).idxmax()]),
              "n_models_moved_ge5": int(((exr[[f"順位_{m}" for m in METHODS]].max(1) - exr[[f"順位_{m}" for m in METHODS]].min(1)) >= 5).sum()),
              "n_top10_models": int(((exr[[f"順位_{m}" for m in METHODS]] <= 10).any(axis=1)).sum()),
              "n_top10_models_moved_ge5": int((((exr[[f"順位_{m}" for m in METHODS]] <= 10).any(axis=1)) & ((exr[[f"順位_{m}" for m in METHODS]].max(1) - exr[[f"順位_{m}" for m in METHODS]].min(1)) >= 5)).sum()),
              "rank_method_ties_at_9": int((exr["順位_順位"] == 9).sum()),
              "n_in_any_top5": len(set(sum([ex_top5[m] for m in METHODS], []))),
              "eff": {m: dict(zip(ITEMS, np.round(eff_weight(normalize(x, m)), 3).tolist())) for m in METHODS},
              "max_scaled_range": {it: [round(float(v.min()), 3), round(float(v.max()), 3)] for it, v in zip(ITEMS, normalize(x, "最大値で割る").T)},
              "raw_range": {it: [round(float(x[:, j].min()), 2), round(float(x[:, j].max()), 2)] for j, it in enumerate(ITEMS)}}

    # 1,000組の機種で
    sims = run(np.random.default_rng(SEED * 10), N_SET, **BASE)
    sims.to_csv(RES / "sets_1000.csv", index=False, float_format="%.4f")
    mean = sims.mean()
    main_tab = {"first_same_all": round(float(mean.first_same_all), 4),
                "n_distinct_first_mean": round(float(mean.n_distinct_first), 3),
                "n_in_any_top5_mean": round(float(mean.n_in_any_top5), 3),
                "max_rank_move_mean": round(float(mean.max_rank_move), 2)}
    by_method = []
    for m in METHODS:
        row = {"method": m,
               "top5_overlap_with_std": round(float(mean[f"top5_overlap_std_{m}"]), 3),
               "first_pair_same_as_std": None,
               "hit5_truth": round(float(mean[f"hit5_{m}"]), 4),
               "rank_corr_truth": round(float(mean[f"rho_truth_{m}"]), 4),
               "first_is_true_first": round(float(mean[f"first_is_true_first_{m}"]), 4)}
        for it in ITEMS:
            row[f"eff_{it}"] = round(float(mean[f"eff_{m}_{it}"]), 4)
        by_method.append(row)
    bm = pd.DataFrame(by_method).drop(columns="first_pair_same_as_std")
    bm.to_csv(RES / "by_method.csv", index=False)

    # 「最大値で割る」の効きの式：項目どうしの相関0なら、各項目の効きは「そろえた値の分散」の割合
    # （その組の 標準偏差÷最大値 の2乗）にほぼなる。30機種×1,000組で、式の値と数えた値を比べる
    fr, ms = [], []
    rr = np.random.default_rng(SEED + 8)
    for _ in range(N_SET):
        _, x0 = make_set(rr, n=BASE["n"], rho=0.0, skew=BASE["skew"], noise_sd=BASE["noise_sd"])
        s0 = normalize(x0, "最大値で割る")
        fr.append(s0.var(0) / s0.var(0).sum()); ms.append(eff_weight(s0))
    formula_rho0 = {"formula_share": dict(zip(ITEMS, np.round(np.mean(fr, 0), 4).tolist())),
                    "measured_share": dict(zip(ITEMS, np.round(np.mean(ms, 0), 4).tolist())),
                    "max_abs_diff_pt": round(float(np.abs(np.mean(fr, 0) - np.mean(ms, 0)).max() * 100), 2)}

    # 確かめ：置き方を1つずつ変える（各500組）
    sens = []
    grid = [("項目どうしの相関", "rho", [0.0, 0.3, 0.6]),
            ("吸う力の右への長さ", "skew", [0.0, 0.35, 0.7]),
            ("音の散らばり（dB）", "noise_sd", [1.5, 3.0, 6.0]),
            ("機種の数", "n", [10, 30, 100])]
    k = 0
    for label, key, vals in grid:
        for v in vals:
            kw = dict(BASE); kw[key] = v
            k += 1
            d = run(np.random.default_rng(SEED * 100 + k), N_SENS, **kw).mean()
            sens.append({"changed": label, "value": v,
                         "first_same_all": round(float(d.first_same_all), 4),
                         "n_distinct_first": round(float(d.n_distinct_first), 3),
                         "top5_overlap_std_max": round(float(d["top5_overlap_std_最大値で割る"]), 3),
                         "top5_overlap_std_rank": round(float(d["top5_overlap_std_順位"]), 3),
                         "top5_overlap_std_minmax": round(float(d["top5_overlap_std_最小〜最大で0〜1"]), 3),
                         "eff_sound_max": round(float(d["eff_最大値で割る_音"]), 4),
                         "eff_suction_std": round(float(d["eff_標準化_吸う力"]), 4),
                         "hit5_std": round(float(d["hit5_標準化"]), 4),
                         "hit5_rank": round(float(d["hit5_順位"]), 4),
                         "hit5_max": round(float(d["hit5_最大値で割る"]), 4),
                         "hit5_minmax": round(float(d["hit5_最小〜最大で0〜1"]), 4)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "robustness.csv", index=False)

    out = {"example_set": ex_one, "sets_1000": main_tab, "by_method": bm.to_dict("records"),
           "max_scaling_formula_rho0": formula_rho0,
           "robustness_ranges": {"first_same_all": [float(sens.first_same_all.min()), float(sens.first_same_all.max())],
                                 "top5_overlap_std_max": [float(sens.top5_overlap_std_max.min()), float(sens.top5_overlap_std_max.max())],
                                 "eff_sound_max": [float(sens.eff_sound_max.min()), float(sens.eff_sound_max.max())]},
           "settings": BASE}
    json.dump(out, open(RES / "a1005_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の30機種、そろえ方ごとの順位（上位10位に入ったことのある機種）
    cols = [f"順位_{m}" for m in METHODS]
    sel = exr[(exr[cols] <= 10).any(axis=1)].copy()
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for _, r in sel.iterrows():
        ys = [r[c] for c in cols]
        moved = max(ys) - min(ys) >= 5
        ax.plot(range(4), ys, "-o", color=ORANGE if moved else LIGHT, lw=1.6 if moved else 1, ms=4, zorder=3 if moved else 2)
        ax.text(3.08, ys[-1], f"{int(r.model_id)}", va="center", fontsize=7.5, color=INK if moved else GRAY)
        ax.text(-0.08, ys[0], f"{int(r.model_id)}", va="center", ha="right", fontsize=7.5, color=INK if moved else GRAY)
    ax.set_xticks(range(4)); ax.set_xticklabels(METHODS)
    ax.invert_yaxis(); ax.set_ylabel("均等に足した合計の順位（1が上）"); ax.set_xlim(-0.4, 3.4)
    ax.set_title("同じ30機種・同じ均等の重みでも、そろえ方で順位が動く（例の1組）")
    ax.text(0.5, -0.13, "オレンジ：4通りの中で順位が5つ以上動いた機種（左右の数字は機種の番号）", transform=ax.transAxes,
            ha="center", fontsize=8.5, color=ORANGE)
    save(fig, "a1005_bump.png", SRC)

    # 図2：そろえ方ごとの実際の効き（1,000組の平均）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    colors = [BLUE, GREEN, ORANGE, GRAY]
    left = np.zeros(4)
    for j, it in enumerate(ITEMS):
        v = bm[f"eff_{it}"].values * 100
        ax.barh(range(4), v, left=left, color=colors[j], label=it, height=0.6)
        for i in range(4):
            if v[i] >= 6:
                ax.text(left[i] + v[i] / 2, i, f"{v[i]:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
        left += v
    ax.set_yticks(range(4)); ax.set_yticklabels(METHODS); ax.invert_yaxis()
    ax.axvline(25, color=INK, lw=0.6, ls=":"); ax.axvline(50, color=INK, lw=0.6, ls=":"); ax.axvline(75, color=INK, lw=0.6, ls=":")
    ax.set_xlim(0, 100); ax.set_xlabel("合計の散らばりのうち各項目が占める分（%、1,000組の平均。点線は25%ずつ）")
    ax.legend(ncol=4, frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    ax.set_title("名目は均等（各25%）でも、「最大値で割る」では音がほとんど効かない", pad=26)
    save(fig, "a1005_effective_weight.png", SRC)

    # 図3：確かめ（1位が4通りで同じ割合）
    keymap = {"項目どうしの相関": "rho", "吸う力の右への長さ": "skew", "音の散らばり（dB）": "noise_sd", "機種の数": "n"}
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    labels = [f"{r.changed}　{r.value:g}" + ("（基本）" if r.value == BASE[keymap[r.changed]] else "") for r in sens.itertuples()]
    col = [BLUE if r.value == BASE[keymap[r.changed]] else LIGHT for r in sens.itertuples()]
    yy = np.arange(len(sens))[::-1]
    ax.barh(yy, sens.first_same_all * 100, color=col, height=0.7)
    for y, v in zip(yy, sens.first_same_all * 100):
        ax.text(v + 1, y, f"{v:.1f}%", va="center", fontsize=8)
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0, 100); ax.set_xlabel("1位が4通りのそろえ方で同じ機種だった組（%、各500組）")
    ax.set_title(f"置き方を1つずつ変えても、1位が4通りでそろうのは{sens.first_same_all.min()*100:.1f}〜{sens.first_same_all.max()*100:.1f}%")
    save(fig, "a1005_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
