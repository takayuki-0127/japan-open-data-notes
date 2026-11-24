"""1128 圧縮の画質の設定を下げると、ファイルの大きさと見た目の差は同じ割合で動くのか？（架空のデータ）

作成者が式と乱数で作った架空の白黒の画像（128×128画素、0〜255の値）を4種類置く。
  なめらか：ゆるい傾き（グラデーション）と大きな波
  色の板：架空の商品の写真に見立てた、背景の上に四角と丸の板を置いたもの
  細かい縞：周期3〜6画素の縞
  ざらざら：細かい粒の模様
圧縮は作成者が置いた簡単なもの：8×8画素のかたまりごとに、濃淡を波の成分（ゆるい波〜細かい波）に分け、
成分ごとの刻み（画質の設定で決まる）で丸めて捨てる。ファイルの大きさは、丸めたあとの値を可逆に詰めたバイト数。
画質の設定 q から刻みへの式は作成者が置いた：刻み = 0.5 × 2^((100−q)/12.5) ×（1 + α×(u+v)）（u, v は波の細かさ 0〜7）。
見た目の差は、①元の画像との画素の差の大きさ（二乗平均の平方根、0〜255の値で）、②かたまりの境目の段差。
"""
import json
import time
import zlib
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1128
SRC = "架空の白黒の画像と作成者が置いた簡単な圧縮（作成者が式と乱数で作成、seed 1128）"
N = 128
QS = [95, 90, 80, 70, 60, 50, 40, 30, 20, 10, 5]
TYPES = ["なめらか", "色の板", "細かい縞", "ざらざら"]
COLORS = {"なめらか": BLUE, "色の板": ORANGE, "細かい縞": GREEN, "ざらざら": INK}
BASE = {"alpha": 0.5, "noise": 1.0, "block": 8}
N_IMG = 16
GRID_ALPHA = [0.25, 0.5, 1.0]
GRID_NOISE = [0.5, 1.0, 2.0]
GRID_BLOCK = [4, 8, 16]
GRID_IMG = 6


def r(x, d=2):
    return round(float(x), d)


# ---------- 架空の画像 ----------
def make_image(kind, rng, noise=1.0):
    y, x = np.mgrid[0:N, 0:N].astype(float)
    if kind == "なめらか":
        th = rng.uniform(0, 2 * np.pi)
        ramp = (np.cos(th) * x + np.sin(th) * y) / N
        img = 128 + 70 * ramp + 20 * np.sin(2 * np.pi * x / rng.uniform(60, 120) + rng.uniform(0, 6)) \
            * np.cos(2 * np.pi * y / rng.uniform(60, 120))
        img += rng.normal(0, 1.0 * noise, (N, N))
    elif kind == "色の板":
        img = np.full((N, N), rng.uniform(170, 235))
        for _ in range(rng.integers(3, 6)):
            v = rng.uniform(30, 200)
            if rng.random() < 0.5:
                x0, y0 = rng.integers(0, N - 30, 2); w, h = rng.integers(20, 60, 2)
                img[y0:y0 + h, x0:x0 + w] = v
            else:
                cx, cy = rng.uniform(20, N - 20, 2); rr = rng.uniform(10, 30)
                img[(x - cx) ** 2 + (y - cy) ** 2 < rr ** 2] = v
        img += rng.normal(0, 2.0 * noise, (N, N))
    elif kind == "細かい縞":
        th = rng.uniform(0, np.pi); per = rng.uniform(3, 6)
        img = 128 + 40 * np.sin(2 * np.pi * (np.cos(th) * x + np.sin(th) * y) / per)
        img += rng.normal(0, 2.0 * noise, (N, N))
    else:  # ざらざら
        z = rng.normal(0, 1, (N, N))
        z = (z + np.roll(z, 1, 0) + np.roll(z, 1, 1) + np.roll(np.roll(z, 1, 0), 1, 1)) / 2  # 細かい粒
        img = 128 + 25 * noise * z
    return np.clip(np.round(img), 0, 255).astype(np.uint8)


# ---------- 作成者が置いた簡単な圧縮 ----------
_CM = {}


def cos_matrix(B):
    if B not in _CM:
        k = np.arange(B)
        C = np.sqrt(2 / B) * np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * B))
        C[0] /= np.sqrt(2)
        _CM[B] = C
    return _CM[B]


STEP_KIND = {"kind": "exp"}


def step_of(q, kind=None):
    """基本：12.5下げるごとに刻みが2倍。確かめ：刻みが画質に対してまっすぐ増える（画質5で同じくらいの刻み）"""
    kind = kind or STEP_KIND["kind"]
    if kind == "exp":
        return 0.5 * 2 ** ((100 - q) / 12.5)
    return 0.5 + (100 - q) * 1.0


def compress(img, q, alpha, B):
    C = cos_matrix(B)
    nb = N // B
    blocks = img.astype(float).reshape(nb, B, nb, B).transpose(0, 2, 1, 3) - 128
    coef = C @ blocks @ C.T  # (nb, nb, B, B)
    u = np.arange(B)
    Q = step_of(q) * (1 + alpha * (u[:, None] + u[None, :]) * 8 / B)
    qc = np.round(coef / Q).astype(np.int16)
    # 大きさ：同じ波の成分どうしを並べて可逆に詰めたバイト数
    payload = qc.reshape(nb * nb, B * B).T.copy().tobytes()
    size = len(zlib.compress(payload, 9))
    rec = C.T @ (qc * Q) @ C + 128
    rec = np.clip(np.round(rec.transpose(0, 2, 1, 3).reshape(N, N)), 0, 255).astype(np.uint8)
    return size, rec


def rms(a, b):
    return float(np.sqrt(np.mean((a.astype(float) - b.astype(float)) ** 2)))


def edge_step(img, B):
    """かたまりの境目をまたぐ隣どうしの差の平均 − 境目でない所の隣どうしの差の平均"""
    f = img.astype(float)
    dx = np.abs(np.diff(f, axis=1)); dy = np.abs(np.diff(f, axis=0))
    idx = np.arange(N - 1)
    bd = (idx % B) == B - 1
    on = np.concatenate([dx[:, bd].ravel(), dy[bd, :].ravel()]).mean()
    off = np.concatenate([dx[:, ~bd].ravel(), dy[~bd, :].ravel()]).mean()
    return float(on - off)


def run(rng, n_img, alpha, noise, B, keep=False):
    rows, ex = [], {}
    for kind in TYPES:
        for i in range(n_img):
            img = make_image(kind, rng, noise)
            e0 = edge_step(img, B)
            for q in QS:
                size, rec = compress(img, q, alpha, B)
                rows.append({"type": kind, "image": i, "q": q, "bytes": size, "rms": rms(img, rec),
                             "edge": edge_step(rec, B) - e0})
                if keep and i == 0 and q in (95, 50, 10):
                    ex[(kind, q)] = rec
            if keep and i == 0:
                ex[(kind, "orig")] = img
    df = pd.DataFrame(rows)
    ref = df[df.q == 95].set_index(["type", "image"])["bytes"]
    df["size_ratio"] = df["bytes"].values / ref.loc[list(zip(df["type"], df["image"]))].values
    return df, ex


def q_at_half(g):
    """大きさの比が0.5を切る画質（隣の2点の間をまっすぐ結んで読む）"""
    g = g.sort_values("q", ascending=False)
    qs, sr, rm = g.q.values, g.size_ratio.values, g.rms.values
    for k in range(1, len(qs)):
        if sr[k] <= 0.5 < sr[k - 1]:
            t = (sr[k - 1] - 0.5) / (sr[k - 1] - sr[k])
            return qs[k - 1] + t * (qs[k] - qs[k - 1]), rm[k - 1] + t * (rm[k] - rm[k - 1])
    return None, None


def summarize(df):
    agg = df.groupby(["type", "q"]).agg(bytes=("bytes", "mean"), size_ratio=("size_ratio", "mean"),
                                        rms=("rms", "mean"), edge=("edge", "mean")).reset_index()
    out = {}
    for kind in TYPES:
        g = agg[agg.type == kind].set_index("q")
        qh, rh = q_at_half(g.reset_index())
        out[kind] = {
            "bytes_q95": r(g.loc[95, "bytes"], 0), "bytes_q50": r(g.loc[50, "bytes"], 0),
            "bytes_q10": r(g.loc[10, "bytes"], 0),
            "size_ratio_q50": r(g.loc[50, "size_ratio"], 3), "size_ratio_q10": r(g.loc[10, "size_ratio"], 3),
            "rms_q95": r(g.loc[95, "rms"]), "rms_q90": r(g.loc[90, "rms"]), "rms_q50": r(g.loc[50, "rms"]),
            "rms_q10": r(g.loc[10, "rms"]),
            "edge_q50": r(g.loc[50, "edge"]), "edge_q10": r(g.loc[10, "edge"]),
            # 90→50 と 50→10 の動き
            "size_shrink_90_50": r(g.loc[90, "bytes"] / g.loc[50, "bytes"]),
            "rms_grow_90_50": r(g.loc[50, "rms"] / g.loc[90, "rms"]),
            "size_shrink_50_10": r(g.loc[50, "bytes"] / g.loc[10, "bytes"]),
            "rms_grow_50_10": r(g.loc[10, "rms"] / g.loc[50, "rms"]),
            "q_half": None if qh is None else r(qh, 1), "rms_at_half": None if rh is None else r(rh),
            # 画質95→5 の全体の動きのうち、95→50 で起きた割合（%）
            "share_size_drop_95_50": r((g.loc[95, "bytes"] - g.loc[50, "bytes"]) / (g.loc[95, "bytes"] - g.loc[5, "bytes"]) * 100, 1),
            "share_rms_rise_95_50": r((g.loc[50, "rms"] - g.loc[95, "rms"]) / (g.loc[5, "rms"] - g.loc[95, "rms"]) * 100, 1),
        }
    return agg, out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df, ex = run(rng, N_IMG, BASE["alpha"], BASE["noise"], BASE["block"], keep=True)
    agg, by_type = summarize(df)
    df.round(4).to_csv(DATA / "images_by_quality.csv", index=False)
    agg.round(4).to_csv(RES / "by_type_quality.csv", index=False)

    step_tab = {str(q): r(step_of(q, "exp"), 3) for q in QS}
    step_tab_lin = {str(q): r(step_of(q, "lin"), 3) for q in QS}

    # 確かめ：画質と刻みの関係をまっすぐにしたとき（同じ乱数の画像）
    STEP_KIND["kind"] = "lin"
    dfl, _ = run(np.random.default_rng(SEED), N_IMG, BASE["alpha"], BASE["noise"], BASE["block"])
    aggl, by_type_lin = summarize(dfl)
    aggl.round(4).to_csv(RES / "by_type_quality_linear_step.csv", index=False)
    STEP_KIND["kind"] = "exp"

    # 確かめ：27通り
    grows = []
    for alpha, noise, B in itertools.product(GRID_ALPHA, GRID_NOISE, GRID_BLOCK):
        d2, _ = run(rng, GRID_IMG, alpha, noise, B)
        _, s2 = summarize(d2)
        for kind in TYPES:
            s = s2[kind]
            grows.append({"alpha": alpha, "noise": noise, "block": B, "type": kind,
                          "size_shrink_90_50": s["size_shrink_90_50"], "rms_grow_90_50": s["rms_grow_90_50"],
                          "size_shrink_50_10": s["size_shrink_50_10"], "rms_grow_50_10": s["rms_grow_50_10"],
                          "size_ratio_q50": s["size_ratio_q50"], "rms_q50": s["rms_q50"], "rms_q95": s["rms_q95"],
                          "q_half": s["q_half"], "rms_at_half": s["rms_at_half"],
                          "share_size_drop_95_50": s["share_size_drop_95_50"],
                          "share_rms_rise_95_50": s["share_rms_rise_95_50"]})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)

    gsum = {}
    for kind in TYPES:
        g = grid[grid.type == kind]
        gsum[kind] = {
            "size_shrink_90_50": [r(g.size_shrink_90_50.min()), r(g.size_shrink_90_50.max())],
            "rms_grow_90_50": [r(g.rms_grow_90_50.min()), r(g.rms_grow_90_50.max())],
            "size_shrink_50_10": [r(g.size_shrink_50_10.min()), r(g.size_shrink_50_10.max())],
            "rms_grow_50_10": [r(g.rms_grow_50_10.min()), r(g.rms_grow_50_10.max())],
            "size_ratio_q50": [r(g.size_ratio_q50.min(), 3), r(g.size_ratio_q50.max(), 3)],
            "q_half": [r(g.q_half.min(), 1), r(g.q_half.max(), 1)] if g.q_half.notna().all() else None,
            "n_q_half_missing": int(g.q_half.isna().sum()),
            "share_size_drop_95_50": [r(g.share_size_drop_95_50.min(), 1), r(g.share_size_drop_95_50.max(), 1)],
            "share_rms_rise_95_50": [r(g.share_rms_rise_95_50.min(), 1), r(g.share_rms_rise_95_50.max(), 1)],
            "rms_at_half": [r(g.rms_at_half.min()), r(g.rms_at_half.max())],
        }
    # 50→10 で「大きさの縮み（倍）より画素の差の増え（倍）が大きい」組の数
    more = grid.rms_grow_50_10 > grid.size_shrink_50_10
    gsum["n_rms_grow_gt_size_shrink_50_10"] = int(more.sum())
    gsum["n_rms_grow_gt_size_shrink_90_50"] = int((grid.rms_grow_90_50 > grid.size_shrink_90_50).sum())
    gsum["n_rows"] = int(len(grid))
    gap = grid.share_size_drop_95_50 - grid.share_rms_rise_95_50
    gsum["n_size_share_gt_rms_share"] = int((gap > 0).sum())
    gsum["share_gap_range"] = [r(gap.min(), 1), r(gap.max(), 1)]
    gsum["share_size_drop_95_50_all"] = [r(grid.share_size_drop_95_50.min(), 1), r(grid.share_size_drop_95_50.max(), 1)]
    gsum["share_rms_rise_95_50_all"] = [r(grid.share_rms_rise_95_50.min(), 1), r(grid.share_rms_rise_95_50.max(), 1)]

    # q=50 での大きさの比の順と画素の差の順
    q50 = agg[agg.q == 50].set_index("type")
    order_size = list(q50.sort_values("size_ratio").index)
    order_rms = list(q50.sort_values("rms").index)

    res = {
        "base": BASE, "image_size": N, "n_images_per_type": N_IMG, "qualities": QS,
        "step_by_quality": step_tab, "step_by_quality_linear": step_tab_lin,
        "by_type_linear_step": {k: {kk: v[kk] for kk in ["share_size_drop_95_50", "share_rms_rise_95_50", "q_half",
                                                          "rms_at_half", "size_ratio_q50", "rms_q50"]}
                                for k, v in by_type_lin.items()},
        "by_type": by_type,
        "order_q50": {"size_ratio_small_to_large": order_size, "rms_small_to_large": order_rms},
        "grid": {"alpha": GRID_ALPHA, "noise": GRID_NOISE, "block": GRID_BLOCK, "n_images_per_type": GRID_IMG,
                 "summary": gsum},
    }

    # ---------- 図1：例の画像 ----------
    fig, axes = plt.subplots(4, 3, figsize=(8.4, 11.4))
    for i, kind in enumerate(TYPES):
        sub = df[(df.type == kind) & (df.image == 0)].set_index("q")
        for j, key in enumerate(["orig", 50, 10]):
            ax = axes[i, j]
            ax.imshow(ex[(kind, key)], cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
            if key == "orig":
                ax.set_title(f"{kind}：元の画像\n（画質95の大きさ {int(sub.loc[95, 'bytes']):,}バイト）", fontsize=10)
            else:
                ax.set_title(f"画質{key}：大きさ{sub.loc[key, 'size_ratio'] * 100:.1f}%\n画素の差 {sub.loc[key, 'rms']:.2f}",
                             fontsize=10)
    fig.suptitle("例の画像（128×128画素、大きさは画質95を100%として）", fontsize=12, y=0.995)
    fig.tight_layout()
    save(fig, "a1128_example.png", SRC)

    # ---------- 図2：画質ごとの大きさと画素の差 ----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for kind in TYPES:
        g = agg[agg.type == kind].sort_values("q")
        axes[0].plot(g.q, g.size_ratio * 100, "-o", ms=4, color=COLORS[kind], label=kind)
        axes[1].plot(g.q, g.rms, "-o", ms=4, color=COLORS[kind], label=kind)
    axes[0].set_ylim(0, 105); axes[0].set_ylabel("大きさ（画質95を100%として、%）")
    axes[1].set_ylim(0, None); axes[1].set_ylabel("元の画像との画素の差（0〜255の値）")
    for ax in axes:
        ax.set_xlabel("画質の設定"); ax.invert_xaxis(); ax.grid(alpha=0.3)
    axes[0].set_title("大きさは画質を下げはじめると大きく減る")
    axes[1].set_title("画素の差は画質を下げきった所で大きく増える")
    axes[0].legend(fontsize=9)
    fig.suptitle("刻みを画質12.5ごとに2倍と置いたとき（各16枚の平均）", fontsize=11, y=1.02)
    fig.tight_layout()
    save(fig, "a1128_size_vs_diff.png", SRC)

    # ---------- 図3：27通りの「95→50で起きた割合」 ----------
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    for kind in TYPES:
        g = grid[grid.type == kind]
        ax.scatter(g.share_size_drop_95_50, g.share_rms_rise_95_50, s=26, color=COLORS[kind], label=kind, alpha=0.8)
    ax.plot([0, 100], [0, 100], color=GRAY, lw=1, ls="--", label="同じ割合の線")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel("画質95→5の大きさの減りのうち、95→50で起きた割合（%）")
    ax.set_ylabel("画質95→5の画素の差の増えのうち、95→50で起きた割合（%）")
    ax.set_title(f"置き方27通り×4種類：{gsum['n_size_share_gt_rms_share']}/{len(grid)}組で線より下\n（刻みを画質12.5ごとに2倍と置いたとき、大きさの減りが先に起きる）")
    ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout()
    save(fig, "a1128_robust.png", SRC)

    res["run_sec"] = r(time.time() - t0, 1)
    with open(RES / "a1128_main.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
