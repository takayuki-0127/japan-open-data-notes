"""947 まっすぐの距離と道のりの距離で、近い店は入れ替わるのか？（架空のデータ）

架空の町（40×40 の交差点、となりの交差点まで100m の碁盤の目の道）。町の真ん中を東西に川が流れ、
渡れるのは橋のある列だけ。家は交差点ごとに1軒（1,600軒）、店はランダムな交差点に6軒置く。
家ごとに「まっすぐの距離でいちばん近い店」と「道のりでいちばん近い店」を比べ、
入れ替わる家の割合と、まっすぐの距離で選んだときに余分に歩く道のりを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 947
SRC = "架空の町の道と店（作成者が乱数で作成、seed 947）"
G = 40
STEP_M = 100
RIVER_Y = 19  # y=19 と y=20 の間を川が流れる
XX, YY = np.meshgrid(np.arange(G), np.arange(G), indexing="xy")


def bridges_cols(n):
    """橋の列：川の上に等間隔に n 本（n=0 は橋なし＝川を渡れない、None は川なし）"""
    if n is None:
        return None
    return [int(round((i + 0.5) * G / n)) for i in range(n)]


def road_dist(shops, bridges):
    """店ごとの、全交差点までの道のりの距離（交差点の数）。碁盤の目で、川は橋の列だけ渡れる"""
    S = len(shops)
    d = np.full((S, G, G), np.inf)
    for i, (x, y) in enumerate(shops):
        d[i, y, x] = 0
    vmask = np.ones((G - 1, G), bool)  # 行 y と y+1 の間の縦の道
    if bridges is not None:
        vmask[RIVER_Y, :] = False
        vmask[RIVER_Y, bridges] = True
    while True:
        nd = d.copy()
        nd[:, :, 1:] = np.minimum(nd[:, :, 1:], d[:, :, :-1] + 1)
        nd[:, :, :-1] = np.minimum(nd[:, :, :-1], d[:, :, 1:] + 1)
        up = np.where(vmask[None], d[:, :-1, :] + 1, np.inf)
        dn = np.where(vmask[None], d[:, 1:, :] + 1, np.inf)
        nd[:, 1:, :] = np.minimum(nd[:, 1:, :], up)
        nd[:, :-1, :] = np.minimum(nd[:, :-1, :], dn)
        if np.array_equal(nd, d):
            return d
        d = nd


def evaluate(shops, bridges):
    sx = np.array([s[0] for s in shops]); sy = np.array([s[1] for s in shops])
    euc = np.sqrt((XX[None] - sx[:, None, None]) ** 2 + (YY[None] - sy[:, None, None]) ** 2)
    road = road_dist(shops, bridges)
    road_min = road.min(0)
    near_e = euc <= euc.min(0)[None] + 1e-9
    road_to_e = np.where(near_e, road, np.inf).min(0)
    mismatch = road_to_e > road_min + 1e-9
    extra = (road_to_e - road_min) * STEP_M
    euc_min = euc.min(0) * STEP_M
    ok = np.isfinite(road_min)
    ratio = np.where(euc.min(0) > 0, road_to_e / np.maximum(euc.min(0), 1e-9), np.nan)
    return {"mismatch": mismatch, "extra": extra, "euc_min": euc_min, "road_min": road_min * STEP_M,
            "ratio": ratio, "ok": ok, "road": road, "euc": euc}


def summarize_one(ev):
    m = ev["mismatch"] & ev["ok"]
    ex = ev["extra"][m]
    r = ev["ratio"][np.isfinite(ev["ratio"])]
    return {"mismatch_share": float(m.mean()),
            "extra_median_m": float(np.median(ex)) if m.any() else 0.0,
            "extra_ge_500_share_of_all": float((ev["extra"] >= 500).mean()),
            "within500_straight": float((ev["euc_min"] <= 500).mean()),
            "within500_road": float((ev["road_min"] <= 500).mean()),
            "ratio_median": float(np.median(r)), "ratio_mean": float(np.mean(r))}


def place_shops(rng, k):
    idx = rng.choice(G * G, size=k, replace=False)
    return [(int(i % G), int(i // G)) for i in idx]


def run(rng, n_rep, k=6, n_bridges=2):
    br = bridges_cols(n_bridges)
    rows = [summarize_one(evaluate(place_shops(rng, k), br)) for _ in range(n_rep)]
    return pd.DataFrame(rows)


def summ(df):
    return {"mismatch_mean": round(float(df.mismatch_share.mean()), 3),
            "mismatch_p10": round(float(df.mismatch_share.quantile(.1)), 3),
            "mismatch_p90": round(float(df.mismatch_share.quantile(.9)), 3),
            "extra_median_m": round(float(df.extra_median_m.median()), 1),
            "extra_ge_500_share": round(float(df.extra_ge_500_share_of_all.mean()), 3),
            "within500_straight": round(float(df.within500_straight.mean()), 3),
            "within500_road": round(float(df.within500_road.mean()), 3),
            "ratio_median": round(float(df.ratio_median.median()), 3),
            "ratio_mean": round(float(df.ratio_mean.mean()), 3)}


def main():
    rng = np.random.default_rng(SEED)
    # 例の町（店6軒・橋2本）
    shops = place_shops(rng, 6)
    br = bridges_cols(2)
    ev = evaluate(shops, br)
    road_near = ev["road"].argmin(0)
    euc_near = ev["euc"].argmin(0)
    homes = pd.DataFrame({"x": XX.ravel(), "y": YY.ravel(),
                          "nearest_straight": euc_near.ravel() + 1, "nearest_road": road_near.ravel() + 1,
                          "straight_m": ev["euc_min"].ravel().round(1), "road_m": ev["road_min"].ravel().astype(int),
                          "mismatch": ev["mismatch"].ravel().astype(int), "extra_m": ev["extra"].ravel().astype(int)})
    homes.to_csv(DATA / "homes_example_town.csv", index=False)
    pd.DataFrame({"shop": np.arange(1, 7), "x": [s[0] for s in shops], "y": [s[1] for s in shops]}).to_csv(
        DATA / "shops_example_town.csv", index=False)
    one = summarize_one(ev)
    one = {k: round(v, 3) for k, v in one.items()}
    one["n_mismatch_homes"] = int(ev["mismatch"].sum())
    one["bridges_x"] = br
    one["mismatch_across_river"] = int((ev["mismatch"] & ((YY <= RIVER_Y) != (np.array([s[1] for s in shops])[euc_near] <= RIVER_Y))).sum())
    one["extra_max_m"] = int(ev["extra"].max())
    v_, c_ = np.unique(ev["extra"][ev["mismatch"]], return_counts=True)
    one["extra_counts_m"] = {str(int(a)): int(b) for a, b in zip(v_, c_)}
    one["extra_le_200_homes"] = int(c_[v_ <= 200].sum())

    # 1) 店の置き場所を変えて500回（基本：店6軒・橋2本）
    base_df = run(rng, 500)
    base_df.round(4).to_csv(RES / "towns_500.csv", index=False)
    base = summ(base_df)

    # 2) 確かめ：橋の数（川なし・8・4・2・1本）、店の数（3・6・12軒）、各300回
    rob = []
    for label, kw_list in [("橋の数", [("川なし", dict(n_bridges=None)), ("8本", dict(n_bridges=8)),
                                    ("4本", dict(n_bridges=4)), ("2本（基本）", dict(n_bridges=2)),
                                    ("1本", dict(n_bridges=1))]),
                           ("店の数（橋2本）", [("3軒", dict(k=3)), ("6軒（基本）", dict(k=6)), ("12軒", dict(k=12))])]:
        for name, kw in kw_list:
            r2 = np.random.default_rng(SEED * 100 + len(rob))
            s = summ(run(r2, 300, **kw))
            rob.append({"変えたもの": label, "値": name, "入れ替わる家の割合": s["mismatch_mean"],
                        "10〜90%": f"{s['mismatch_p10']*100:.1f}〜{s['mismatch_p90']*100:.1f}%",
                        "余分な道のり（入れ替わる家の中央値、m）": s["extra_median_m"],
                        "500m以上余分に歩く家の割合": s["extra_ge_500_share"],
                        "まっすぐ500m以内に店": s["within500_straight"], "道のり500m以内に店": s["within500_road"],
                        "道のり÷まっすぐ（中央値）": s["ratio_median"], "道のり÷まっすぐ（平均）": s["ratio_mean"]})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    # 碁盤の目で向きがでたらめなときの 道のり÷まっすぐ の平均（|cos|+|sin| の平均＝4/π）
    theory = {"grid_ratio_mean_4_over_pi": round(4 / np.pi, 3)}

    out = {"example_town": one, "base_500_towns": base, "theory": theory, "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a947_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の町の地図
    pal = ["#2a78d6", "#eb6834", "#3aa07a", "#8a5cc2", "#c9a227", "#6b6b6b"]
    fig, ax = plt.subplots(figsize=(6.8, 6.6))
    for x in range(G):
        ax.plot([x, x], [0, RIVER_Y], color="#dddddd", lw=.4, zorder=0)
        ax.plot([x, x], [RIVER_Y + 1, G - 1], color="#dddddd", lw=.4, zorder=0)
    for y in range(G):
        ax.plot([0, G - 1], [y, y], color="#dddddd", lw=.4, zorder=0)
    ax.axhspan(RIVER_Y + 0.25, RIVER_Y + 0.75, color="#9fd0f0", zorder=1)
    for b in br:
        ax.plot([b, b], [RIVER_Y, RIVER_Y + 1], color=INK, lw=3, zorder=2)
        ax.text(b + 0.4, RIVER_Y + 1.25, "橋", fontsize=9, color=INK)
    cols = np.array(pal)[road_near.ravel()]
    mm = ev["mismatch"].ravel()
    ax.scatter(XX.ravel()[~mm], YY.ravel()[~mm], s=9, c=cols[~mm], alpha=.45, lw=0, zorder=3)
    ax.scatter(XX.ravel()[mm], YY.ravel()[mm], s=26, c=cols[mm], marker="x", lw=1.3, zorder=4)
    for i, (x, y) in enumerate(shops):
        ax.plot(x, y, marker="s", ms=13, color=pal[i], mec=INK, mew=1.2, zorder=5)
        ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=8, color="white", fontweight="bold", zorder=6)
    ax.set_xlim(-1, G); ax.set_ylim(-1, G); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.legend(handles=[Line2D([], [], marker="s", ls="", color=GRAY, mec=INK, ms=9, label="店（番号）"),
                       Line2D([], [], marker="o", ls="", color=GRAY, ms=4, label="家（色＝道のりでいちばん近い店）"),
                       Line2D([], [], marker="x", ls="", color=GRAY, ms=6, label="まっすぐで選ぶと別の店になる家")],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=1, frameon=False, fontsize=9)
    ax.set_title(f"例の町（店6軒・橋2本）：まっすぐの距離で近い店と\n道のりで近い店が入れ替わる家は{one['mismatch_share']*100:.1f}%", fontsize=11.5)
    save(fig, "a947_example_map.png", SRC, y=-0.01)

    # 図2：入れ替わる家の割合（置き方ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    lab = [f"{r['変えたもの'].replace('（橋2本）', '')}：{r['値']}" for r in rob.to_dict("records")]
    y = np.arange(len(rob))[::-1]
    v = rob["入れ替わる家の割合"].values * 100
    colb = [BLUE if "基本" in l else LIGHT for l in lab]
    ax.barh(y, v, color=colb, height=.65)
    for yi, vi in zip(y, v):
        ax.text(vi + 0.3, yi, f"{vi:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9)
    ax.set_xlabel("まっすぐの距離で選ぶと、道のりでいちばん近い店と違う店になる家の割合（%、各300回の平均）", fontsize=9)
    ax.set_xlim(0, max(v) * 1.18)
    ax.set_title("川と橋が少ないほど、近い店は入れ替わる（川がなくても0にはならない）", fontsize=11.5)
    save(fig, "a947_mismatch.png", SRC)

    # 図3：余分に歩く道のりの分布（基本、例の町）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ex = ev["extra"][ev["mismatch"]]
    vals, cnt = np.unique(ex, return_counts=True)
    ax.bar(vals, cnt, width=70, color=ORANGE, alpha=.85)
    for v_, c_ in zip(vals, cnt):
        ax.text(v_, c_ + 0.8, str(c_), ha="center", fontsize=8.5)
    ax.set_xticks(np.arange(0, ex.max() + 101, 200))
    ax.set_xlabel("まっすぐの距離で選んだ店まで、余分に歩く道のり（m）"); ax.set_ylabel("家の数")
    ax.set_title(f"入れ替わる家{one['n_mismatch_homes']}軒の余分な道のり（例の町）：中央値{one['extra_median_m']:.0f}m・最大{one['extra_max_m']:,}m", fontsize=11)
    save(fig, "a947_extra.png", SRC)
    print(json.dumps({k: v for k, v in out.items() if k != "robustness"}, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
