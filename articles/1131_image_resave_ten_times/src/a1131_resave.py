"""1131 圧縮して保存し直すことを10回くり返すと、元の画像との差はどれだけ積み重なるのか？（架空のデータ）

作成者が式と乱数で作った架空の画像（明るさだけ、256×256画素、0〜255の段）を、作成者が置いた圧縮で保存し直す。
圧縮：8×8画素の区画ごとに、明るさを波の成分（ゆっくり変わる成分〜細かく変わる成分）に分け、
成分ごとの刻み（細かい成分ほど粗い）で丸めてから元に戻し、画素を0〜255の整数に丸める。
刻み＝基本の刻み（4＋3×（縦の番号＋横の番号））×画質の設定からの倍率。
保存し直し方（同じ設定・毎回区画の位置が1画素ずれる・画質の設定を交互に・画素を整数に丸めない）を変え、
10回目までの「元の画像との差」（画素ごとの差の二乗平均の平方根、0〜255の段）を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1131
SRC = "架空の画像と作成者が置いた圧縮（作成者が式と乱数で作成、seed 1131）"
N = 256          # 画像の一辺
B = 8            # 区画の一辺
N_IMG = 20       # 種類ごとの画像の数
SAVES = 10
QUALS = [50, 75, 90]
BASE_Q = 75
ALT_DROP = 15    # ③で交互に使う、1段低い画質の設定（画質−15）
TYPES = ["縞とグラデーション", "色の板", "細かい模様"]
SCEN = ["①同じ設定で保存し直す", "②毎回区画の位置が1画素ずれる", "③画質の設定を交互に（画質と画質−15）", "④画素を整数に丸めない（①の対照）"]
SCEN_SHORT = ["同じ設定", "1画素ずれる", "画質を交互に", "整数に丸めない"]


def r(x, d=3):
    return round(float(x), d)


# ---- 圧縮のしくみ ----
def basis():
    k = np.arange(B)
    C = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * B))
    C[0] *= np.sqrt(1 / B)
    C[1:] *= np.sqrt(2 / B)
    return C                                     # 直交（C @ C.T = 単位）


CM = basis()
UV = np.add.outer(np.arange(B), np.arange(B))
Q0 = 4.0 + 3.0 * UV                              # 基本の刻み（作成者が置いた）


def qscale(q):
    return 50.0 / q if q < 50 else (200 - 2 * q) / 100.0


def step_table(q):
    return np.maximum(Q0 * qscale(q), 1.0)


def compress(img, q, offset=0, to_int=True):
    """区画の位置を offset 画素ずらして圧縮し、戻す。to_int なら0〜255の整数に丸める"""
    o = offset % B
    P = np.pad(img, ((o, B - o), (o, B - o)), mode="edge") if o else np.pad(img, ((0, B), (0, B)), mode="edge")
    h = P.shape[0] // B
    X = P.reshape(h, B, h, B).transpose(0, 2, 1, 3) - 128.0
    Y = CM @ X @ CM.T
    S = step_table(q)
    Yq = np.round(Y / S) * S
    Xr = CM.T @ Yq @ CM + 128.0
    out = Xr.transpose(0, 2, 1, 3).reshape(P.shape)[o:o + N, o:o + N]
    if to_int:
        out = np.clip(np.round(out), 0, 255)
    return out


# ---- 架空の画像 ----
def make_image(rng, kind):
    y, x = np.mgrid[0:N, 0:N] / N
    if kind == 0:   # 縞とグラデーション
        ang = rng.uniform(0, np.pi)
        f = rng.uniform(6, 30)
        g = 60 + 120 * (x * np.cos(ang / 2) + y * np.sin(ang / 2)) / 1.5
        img = g + 40 * np.sin(2 * np.pi * f * (x * np.cos(ang) + y * np.sin(ang)))
    elif kind == 1:  # 色の板（商品の写真に見立てた、くっきりした境目の板）
        img = np.full((N, N), rng.uniform(150, 230))
        for _ in range(rng.integers(5, 10)):
            x0, y0 = rng.integers(0, N - 40, 2)
            w, hh = rng.integers(30, 120, 2)
            img[y0:y0 + hh, x0:x0 + w] = rng.uniform(20, 235)
        img = img + rng.normal(0, 2.0, (N, N))
    else:           # 細かい模様（でたらめな値を少しなめらかにしたもの）
        z = rng.normal(0, 1, (N + 4, N + 4))
        z = sum(z[i:i + N, :] for i in range(5)) / 5
        z = sum(z[:, i:i + N] for i in range(5)) / 5
        img = 128 + 55 * z / z.std()
    return np.clip(np.round(img), 0, 255)


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def chain(img, scen, q):
    """10回保存し直して、回ごとの元との差・前の回との差・変わった画素の割合を返す"""
    cur = img.copy()
    to_orig, to_prev, changed = [], [], []
    for i in range(SAVES):
        if scen == 0:
            nxt = compress(cur, q)
        elif scen == 1:
            nxt = compress(cur, q, offset=i)
        elif scen == 2:
            nxt = compress(cur, q if i % 2 == 0 else q - ALT_DROP)
        else:
            nxt = compress(cur, q, to_int=False)
        to_orig.append(rmse(nxt, img))
        to_prev.append(rmse(nxt, cur))
        changed.append(float(np.mean(np.abs(nxt - cur) > 1e-9)))
        cur = nxt
    return to_orig, to_prev, changed, cur


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    imgs = [[make_image(rng, k) for _ in range(N_IMG)] for k in range(len(TYPES))]
    rows = []
    examples = {}
    for qi, q in enumerate(QUALS):
        for k in range(len(TYPES)):
            for s in range(len(SCEN)):
                for j, img in enumerate(imgs[k]):
                    to_o, to_p, ch, last = chain(img, s, q)
                    for i in range(SAVES):
                        rows.append({"quality": q, "image_type": TYPES[k], "scenario": SCEN[s], "image_no": j + 1,
                                     "save": i + 1, "diff_to_original": round(to_o[i], 4),
                                     "diff_to_previous": round(to_p[i], 4), "changed_pixel_share": round(ch[i], 5)})
                    if q == BASE_Q and k == 1 and j == 0:
                        examples[s] = last
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "resave_chains.csv", index=False)
    # 対照：1段低い画質（画質−15）で1回だけ保存したときの差
    low = pd.DataFrame([{"quality": q, "image_type": TYPES[k], "image_no": j + 1,
                         "one_save_low": rmse(compress(img, q - ALT_DROP), img)}
                        for q in QUALS for k in range(len(TYPES)) for j, img in enumerate(imgs[k])])

    # 回ごとの平均（基本：画質75、3種類×20枚＝60枚）
    base = df[df.quality == BASE_Q]
    curve = base.groupby(["scenario", "save"], sort=False)[["diff_to_original", "diff_to_previous", "changed_pixel_share"]].mean().reset_index()
    curve = curve.round(4)
    curve.to_csv(RES / "curve_base.csv", index=False)

    # 1回目と10回目の比（画像ごとに比を出してから平均）
    piv = df.pivot_table(index=["quality", "image_type", "scenario", "image_no"], columns="save", values="diff_to_original").reset_index()
    piv["ratio10"] = piv[SAVES] / piv[1]
    piv["first"] = piv[1]; piv["tenth"] = piv[SAVES]
    piv = piv.merge(low, on=["quality", "image_type", "image_no"])
    piv["ratio10_low"] = piv["tenth"] / piv["one_save_low"]
    grid = piv.groupby(["quality", "image_type", "scenario"], sort=False)[["first", "tenth", "ratio10", "one_save_low", "ratio10_low"]].mean().reset_index()
    grid = grid.round(3)
    grid.to_csv(RES / "grid.csv", index=False)

    # 基本の表
    pb = piv[piv.quality == BASE_Q]
    table = []
    for s in SCEN:
        d = pb[pb.scenario == s]
        cv = curve[curve.scenario == s].set_index("save")
        last_change = df[(df.quality == BASE_Q) & (df.scenario == s)].groupby(["image_type", "image_no"])
        # 何回目で画素が1つも変わらなくなったか（10回目までに止まった画像の割合）
        stopped = last_change.apply(lambda g: bool((g.sort_values("save").changed_pixel_share.values[1:] == 0).any())).mean()
        table.append({"scenario": s, "first": r(d["first"].mean()), "save2": r(cv.loc[2, "diff_to_original"]),
                      "save3": r(cv.loc[3, "diff_to_original"]), "tenth": r(d["tenth"].mean()),
                      "ratio10": r(d["ratio10"].mean()), "ratio10_min": r(d["ratio10"].min()), "ratio10_max": r(d["ratio10"].max()),
                      "one_save_low": r(d["one_save_low"].mean()), "ratio10_to_one_save_low": r(d["ratio10_low"].mean()),
                      "prev_diff_save10": r(cv.loc[SAVES, "diff_to_previous"]),
                      "changed_share_save2": r(cv.loc[2, "changed_pixel_share"], 4),
                      "changed_share_save10": r(cv.loc[SAVES, "changed_pixel_share"], 4),
                      "stopped_by_10_share": r(stopped, 4)})
    tb = pd.DataFrame(table)
    tb.to_csv(RES / "summary_base.csv", index=False)

    # 種類ごと（画質75）
    by_type = grid[grid.quality == BASE_Q].copy()

    # 9通り（画質3×種類3）の範囲
    rng_tab = []
    for s in SCEN:
        g = grid[grid.scenario == s]
        rng_tab.append({"scenario": s, "ratio10_min": r(g.ratio10.min()), "ratio10_max": r(g.ratio10.max()),
                        "ratio10_low_min": r(g.ratio10_low.min()), "ratio10_low_max": r(g.ratio10_low.max()),
                        "first_min": r(g["first"].min()), "first_max": r(g["first"].max()),
                        "tenth_min": r(g.tenth.min()), "tenth_max": r(g.tenth.max())})
    rng_df = pd.DataFrame(rng_tab)

    # ②と①の10回目の比（9通り）
    g1 = grid[grid.scenario == SCEN[0]].set_index(["quality", "image_type"])
    g2 = grid[grid.scenario == SCEN[1]].set_index(["quality", "image_type"])
    shift_over_same = (g2.tenth / g1.tenth)

    # 区画をずらした回だけの寄与：②の2〜8回目の増え方
    cv2 = curve[curve.scenario == SCEN[1]].set_index("save").diff_to_original
    main_json = {
        "settings": {"image_size": N, "block": B, "images_per_type": N_IMG, "image_types": TYPES, "saves": SAVES,
                     "qualities": QUALS, "base_quality": BASE_Q, "alt_quality_drop": ALT_DROP,
                     "base_step_rule": "4+3*(u+v)", "quality_scale_rule": "q<50: 50/q, q>=50: (200-2q)/100",
                     "step_table_base_quality_min": r(step_table(BASE_Q).min()), "step_table_base_quality_max": r(step_table(BASE_Q).max())},
        "base_table": table,
        "curve_scenario2": {int(k): r(v) for k, v in cv2.items()},
        "curve_scenario1": {int(k): r(v) for k, v in curve[curve.scenario == SCEN[0]].set_index("save").diff_to_original.items()},
        "curve_scenario3": {int(k): r(v) for k, v in curve[curve.scenario == SCEN[2]].set_index("save").diff_to_original.items()},
        "by_type_base_quality": by_type.to_dict("records"),
        "grid_range_9": rng_tab,
        "shift_tenth_over_same_tenth_9": {"min": r(shift_over_same.min()), "max": r(shift_over_same.max())},
        "no_round_exact_same_as_first": bool((pb[pb.scenario == SCEN[3]]["ratio10"] - 1).abs().max() < 1e-9),
        "no_round_max_abs_ratio_minus_1": float(f"{(piv[piv.scenario == SCEN[3]]['ratio10'] - 1).abs().max():.2e}"),
    }
    ex_rmse = [r(rmse(examples[i], imgs[1][0])) for i in range(4)]
    main_json["example_board1_tenth_diff"] = dict(zip(SCEN, ex_rmse))
    with open(RES / "a1131_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図1：回ごとの元との差 ----
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    cols = [BLUE, ORANGE, GREEN, GRAY]
    for s, c, sh in zip(SCEN, cols, SCEN_SHORT):
        v = curve[curve.scenario == s]
        ax.plot(v.save, v.diff_to_original, marker="o", color=c, label=s, lw=2 if s != SCEN[3] else 1.2,
                ls="-" if s != SCEN[3] else "--")
    ax.set_ylim(0, None)
    ax.set_xticks(range(1, SAVES + 1))
    ax.set_xlabel("保存し直した回数", labelpad=2)
    ax.set_ylabel("元の画像との差（0〜255の段）")
    ax.set_title("保存し直すたびの元との差（画質75、60枚の平均）")
    ax.legend(fontsize=9, frameon=False, loc="lower center", ncol=2)
    save(fig, "a1131_curve.png", "出典：" + SRC)

    # ---- 図2：9通りの10回目÷1回目 ----
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    short = {"縞とグラデーション": "縞と\nグラデ", "色の板": "色の板", "細かい模様": "細かい\n模様"}
    labels = [f"{short[t]}\n画質{q}" for q in QUALS for t in TYPES]
    xs = np.arange(len(labels))
    w = 0.26
    for i, (s, c) in enumerate(zip(SCEN[:3], cols[:3])):
        vals = [float(grid[(grid.quality == q) & (grid.image_type == t) & (grid.scenario == s)].ratio10.iloc[0]) for q in QUALS for t in TYPES]
        ax.bar(xs + (i - 1) * w, vals, w, color=c, label=SCEN_SHORT[i])
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_ylim(0, None)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("10回目の差 ÷ 1回目の差")
    ax.set_title("10回目の差は1回目の何倍か（画質3×画像3の9通り）")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    save(fig, "a1131_ratio_grid.png", "出典：" + SRC)

    # ---- 図3：例の画像と元との差 ----
    fig, axs = plt.subplots(2, 4, figsize=(9.6, 5.4))
    orig = imgs[1][0]
    panels = [("元の画像", orig), ("①同じ設定で10回", examples[0]), ("②1画素ずれて10回", examples[1]), ("③画質を交互に10回", examples[2])]
    for i, (tt, im) in enumerate(panels):
        a = axs[0, i]
        a.imshow(im, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        a.set_title(tt if i == 0 else f"{tt}\n元との差 {ex_rmse[i - 1]:.2f}", fontsize=9)
        b = axs[1, i]
        if i == 0:
            b.axis("off")
            b.text(0.5, 0.5, "下の段：元との差の大きさ\n（白いほど大きい。\n差8段以上はまっ白）", ha="center", va="center", fontsize=9)
        else:
            b.imshow(np.abs(im - orig), cmap="gray", vmin=0, vmax=8, interpolation="nearest")
        for a2 in (a, b):
            a2.set_xticks([]); a2.set_yticks([])
            for sp in a2.spines.values():
                sp.set_visible(False)
    fig.suptitle("色の板の1枚目（256×256画素、画質75）", fontsize=11)
    save(fig, "a1131_example.png", "出典：" + SRC)

    main_json["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: main_json[k] for k in ["base_table", "grid_range_9", "shift_tenth_over_same_tenth_9", "no_round_exact_same_as_first", "no_round_max_abs_ratio_minus_1"]}, ensure_ascii=False, indent=1))
    print("example rmse", ex_rmse)
    print("sec", main_json["run_sec"])


if __name__ == "__main__":
    main()
