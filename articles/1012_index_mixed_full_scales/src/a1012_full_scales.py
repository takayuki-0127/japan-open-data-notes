"""1012 10点満点と100点満点の項目を混ぜると、何が起きるのか？（架空のデータ）

架空の店200軒の覆面調査。4項目（接客・清潔さ・品ぞろえは10点満点、待ち時間の短さは100点満点）。
店ごとに項目の「本当の良さ」を置き、意図は「4項目を同じ重みで見る」とする。
そのまま足す・満点をそろえて足す・平均と標準偏差でそろえて足すの3通りで、
各項目が合計点にどれだけ効くか、意図した順位とどれだけ合うかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1012
SRC = "架空の店の覆面調査（作成者が乱数で作成、seed 1012）"
N = 200
ITEMS = ["接客", "清潔さ", "品ぞろえ", "待ち時間の短さ"]
FULL = np.array([10, 10, 10, 100])
CENTER = np.array([6.5, 6.5, 6.5, 65.0])
COMMON = 0.5            # 本当の良さの共通の分（項目どうしの相関0.25）
NOISE = 0.4             # 調べる人の見方の揺れ（本当の良さの単位）
SLOPE10, SLOPE100 = 1.2, 6.0   # 本当の良さ1あたりの点（10点満点の項目、100点満点の項目）
REPS, GRID_REPS = 1000, 300
METHODS = {"raw": "そのまま足す", "full": "満点をそろえて足す", "z": "平均と標準偏差でそろえて足す"}


def make_scores(rng, s10=SLOPE10, s100=SLOPE100, n=N):
    c = rng.normal(0, 1, (n, 1))
    q = COMMON * c + np.sqrt(1 - COMMON ** 2) * rng.normal(0, 1, (n, 4))   # 本当の良さ
    slope = np.array([s10, s10, s10, s100])
    x = CENTER + slope * (q + rng.normal(0, NOISE, (n, 4)))
    x = np.clip(np.round(x), 0, FULL)
    return q, x


def composite(x, how):
    if how == "raw":
        y = x.astype(float)
    elif how == "full":
        y = x / FULL * 10
    else:
        y = (x - x.mean(0)) / x.std(0)
    return y, y.sum(1)


def shares(y):
    """合計点の散らばりのうち、各項目が受け持つ割合（cov(項目, 合計)/var(合計)、足すと1）"""
    s = y.sum(1)
    return np.array([np.cov(y[:, i], s, bias=True)[0, 1] for i in range(y.shape[1])]) / s.var()


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def topk(a, b, k=20):
    return len(set(np.argsort(-a, kind="stable")[:k]) & set(np.argsort(-b, kind="stable")[:k]))


def formula_share(how, s10=SLOPE10, s100=SLOPE100):
    """丸め・切り捨てを無視した式の値"""
    a = np.array([s10, s10, s10, s100], float)
    if how == "full":
        a = a / FULL * 10
    elif how == "z":
        a = np.ones(4)
    r = np.full((4, 4), COMMON ** 2) + np.eye(4) * (1 - COMMON ** 2 + NOISE ** 2)
    cmat = np.outer(a, a) * r
    return cmat.sum(1) / cmat.sum()


def one_rep(rng, s10=SLOPE10, s100=SLOPE100):
    q, x = make_scores(rng, s10, s100)
    intended = q.mean(1)
    out = {}
    for m in METHODS:
        y, s = composite(x, m)
        sh = shares(y)
        out[m] = {"share_wait": float(sh[3]), "share_each10": float(sh[:3].mean()),
                  "spearman": spearman(s, intended), "top20": topk(s, intended),
                  "corr_with_wait_only": float(np.corrcoef(s, x[:, 3])[0, 1])}
    out["wait_only"] = {"spearman": spearman(x[:, 3], intended), "top20": topk(x[:, 3].astype(float), intended)}
    out["sd_points"] = x.std(0).tolist()
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data/stores.csv）
    q, x = make_scores(rng)
    d = pd.DataFrame({"store": [f"S{i + 1:03d}" for i in range(N)]})
    for i, name in enumerate(["service", "clean", "range", "wait"]):
        d[f"{name}_score"] = x[:, i].astype(int)
    d["intended"] = q.mean(1).round(4)
    for m in METHODS:
        _, s = composite(x, m)
        d[f"total_{m}"] = s.round(4)
        d[f"rank_{m}"] = pd.Series(-s).rank(method="min").astype(int)
    d["rank_intended"] = pd.Series(-d["intended"]).rank(method="min").astype(int)
    d.to_csv(DATA / "stores.csv", index=False)
    one = {"sd_points": [round(float(v), 3) for v in x.std(0)],
           "min_max": [[int(x[:, i].min()), int(x[:, i].max())] for i in range(4)],
           "corr_raw_total_vs_wait": round(float(np.corrcoef(d.total_raw, x[:, 3])[0, 1]), 4)}
    for m in METHODS:
        y, s = composite(x, m)
        one[m] = {"shares": [round(float(v), 4) for v in shares(y)], "top20": topk(s, d.intended.values),
                  "spearman": round(spearman(s, d.intended.values), 4)}

    # 基本の置き方（1,000回）
    rows = [one_rep(np.random.default_rng(SEED * 1000 + r)) for r in range(REPS)]
    base = []
    for m in METHODS:
        df = pd.DataFrame([r[m] for r in rows]).mean()
        f = formula_share(m)
        base.append({"key": m, "method": METHODS[m], "share_wait": round(df.share_wait, 4),
                     "share_wait_formula": round(float(f[3]), 4), "share_each10": round(df.share_each10, 4),
                     "spearman": round(df.spearman, 4), "top20": round(df.top20, 3),
                     "corr_with_wait_only": round(df.corr_with_wait_only, 4)})
    wo = pd.DataFrame([r["wait_only"] for r in rows]).mean()
    base.append({"key": "wait_only", "method": "待ち時間の短さだけ", "share_wait": 1.0, "share_wait_formula": 1.0,
                 "share_each10": 0.0, "spearman": round(wo.spearman, 4), "top20": round(wo.top20, 3),
                 "corr_with_wait_only": 1.0})
    base = pd.DataFrame(base)
    base.to_csv(RES / "methods_base.csv", index=False)
    sdp = np.array([r["sd_points"] for r in rows]).mean(0)

    # 確かめ：100点満点の項目の散らばり×10点満点の項目の散らばり（各300回）
    grid = []
    gi = 0
    for s10 in [0.6, 1.2, 2.4]:
        for s100 in [3.0, 6.0, 12.0, 24.0]:
            rr = [one_rep(np.random.default_rng(SEED * 100000 + gi * 1000 + r), s10, s100) for r in range(GRID_REPS)]
            gi += 1
            for m in METHODS:
                df = pd.DataFrame([r[m] for r in rr]).mean()
                grid.append({"slope10": s10, "slope100": s100, "method": METHODS[m],
                             "share_wait": round(df.share_wait, 4), "share_wait_formula": round(float(formula_share(m, s10, s100)[3]), 4),
                             "spearman": round(df.spearman, 4), "top20": round(df.top20, 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g_full = grid[grid.method == METHODS["full"]]
    g_raw = grid[grid.method == METHODS["raw"]]
    g_z = grid[grid.method == METHODS["z"]]
    summary = {"raw_share_wait_range": [float(g_raw.share_wait.min()), float(g_raw.share_wait.max())],
               "full_share_wait_range": [float(g_full.share_wait.min()), float(g_full.share_wait.max())],
               "z_share_wait_range": [float(g_z.share_wait.min()), float(g_z.share_wait.max())],
               "raw_top20_range": [float(g_raw.top20.min()), float(g_raw.top20.max())],
               "full_top20_range": [float(g_full.top20.min()), float(g_full.top20.max())],
               "z_top20_range": [float(g_z.top20.min()), float(g_z.top20.max())],
               "max_abs_share_formula_gap": round(float((grid.share_wait - grid.share_wait_formula).abs().max()), 4)}
    bb = base[base.key.isin(list(METHODS))]
    summary["base_max_abs_share_formula_gap"] = round(float((bb.share_wait - bb.share_wait_formula).abs().max()), 4)
    out = {"one_draw": one, "base_1000reps": base.to_dict("records"),
           "mean_sd_points_base": [round(float(v), 3) for v in sdp], "grid_summary": summary}
    json.dump(out, open(RES / "a1012_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分、そのまま足した合計と待ち時間の短さの点
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(x[:, 3], d.total_raw, s=12, color=BLUE, alpha=.6, lw=0)
    ax.set_xlabel("待ち時間の短さ（100点満点）"); ax.set_ylabel("4項目をそのまま足した合計（130点満点）")
    ax.set_title(f"そのまま足すと、合計点はほぼ100点満点の1項目で決まる\n（店200軒、1回分、相関{one['corr_raw_total_vs_wait']:.3f}）")
    save(fig, "a1012_scatter.png", SRC)

    # 図2：やり方ごとの各項目の効き方
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    b = base[base.key.isin(list(METHODS))].iloc[::-1]
    left = np.zeros(len(b))
    cols = [LIGHT, GRAY, GREEN, ORANGE]
    for i, name in enumerate(ITEMS):
        v = (b.share_each10.values if i < 3 else b.share_wait.values) * 100
        ax.barh(b.method, v, left=left, color=cols[i], label=name + ("（100点満点）" if i == 3 else "（10点満点）"),
                edgecolor="white")
        if i == 3:
            for k, (l, vv) in enumerate(zip(left, v)):
                ax.text(l + vv / 2, k, f"{vv:.1f}%", ha="center", va="center", fontsize=9, color=INK)
        left += v
    for k, t in enumerate(b.top20.values):
        ax.text(101, k, f"上位20軒の当たり {t:.1f}軒", va="center", fontsize=8.5)
    ax.set_xlim(0, 100); ax.set_xlabel("合計点の散らばりのうち、各項目が受け持つ割合（%、1,000回の平均）")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.25))
    ax.set_title(f"意図は4項目を同じ重み（各25%）。待ち時間の短さはそのままで{base.share_wait[0]*100:.1f}%、"
                 f"満点をそろえると{base.share_wait[1]*100:.1f}%", fontsize=12)
    save(fig, "a1012_shares.png", SRC, y=-0.2)

    # 図3：散らばりの置き方と、満点をそろえたときの待ち時間の効き方
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.arange(4)
    for s10, col, mk in [(0.6, LIGHT, "o"), (1.2, BLUE, "o"), (2.4, INK, "o")]:
        g = g_full[g_full.slope10 == s10]
        ax.plot(xs, g.share_wait * 100, color=col, marker=mk, label=f"満点をそろえる：10点満点の項目が良さ1あたり{s10}点")
    g = g_z[g_z.slope10 == 1.2]
    ax.plot(xs, g.share_wait * 100, color=GREEN, marker="s", ls="--", label="平均と標準偏差でそろえる：10点満点の項目が1.2点")
    ax.axhline(25, color=GRAY, lw=1, ls=":"); ax.text(3.1, 28, "意図（25%）", fontsize=8.5, color=GRAY)
    ax.set_xticks(xs); ax.set_xticklabels(["3点", "6点（基本）", "12点", "24点"])
    ax.set_xlabel("100点満点の項目（待ち時間の短さ）が、本当の良さ1あたり何点動くか")
    ax.set_ylabel("待ち時間の短さが受け持つ割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("満点をそろえても、効き方は点の散らばりで決まる（各300回）")
    save(fig, "a1012_by_spread.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
