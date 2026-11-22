"""953 出店した場所の売上が高いのは、場所のおかげか？（選ばれ方）（架空のデータ）

架空の町（30×30 の区画）に出店の候補地を置く。候補地ごとに「本当の売上の力（万円／月）」を作成者が置き、
会社は出店前の見込み（本当の力に調べの誤差を足したもの）が基準を超えた場所だけに出店する。
駅前は出店の費用が高いので基準を高くした、と置く。出店した店の売上だけを見ると、
駅前の有利さ・場所の力・見込みの当たりがどう見えるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 953
SRC = "架空の町の出店候補地と売上（作成者が乱数で作成、seed 953）"
G = 30
BASE = {"n_cand": 400, "base": 300.0, "people_w": 80.0, "bonus": 20.0, "site_sd": 40.0, "est_sd": 30.0,
        "op_sd": 20.0, "hurdle": 400.0, "hurdle_gap": 40.0, "station_r": 5.0}
N_TOWN = 500
NEXT_K = 5


def people_field(rng):
    """人の多さ（0〜1）：でたらめな場所に置いた5つの山の重ね合わせ"""
    xx, yy = np.meshgrid(np.arange(G), np.arange(G), indexing="xy")
    f = np.zeros((G, G))
    for _ in range(5):
        cx, cy, w = rng.uniform(0, G), rng.uniform(0, G), rng.uniform(3, 7)
        f += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * w * w))
    return (f - f.min()) / (f.max() - f.min())


def make_town(rng, n_cand=400, base=300.0, people_w=80.0, bonus=20.0, site_sd=40.0, est_sd=30.0, op_sd=20.0,
              hurdle=400.0, hurdle_gap=40.0, station_r=5.0):
    f = people_field(rng)
    stations = rng.uniform(2, G - 2, (3, 2))
    cells = rng.choice(G * G, n_cand, replace=False)
    x, y = cells % G, cells // G
    dist = np.min(np.hypot(x[:, None] - stations[:, 0], y[:, None] - stations[:, 1]), axis=1)
    eki = dist <= station_r
    true = base + people_w * f[y, x] + bonus * eki + rng.normal(0, site_sd, n_cand)
    est = true + rng.normal(0, est_sd, n_cand)
    bar = hurdle + hurdle_gap * eki
    opened = est >= bar
    sales = true + rng.normal(0, op_sd, n_cand)        # 出店した場合の1年目の売上（出店した店だけが見える）
    df = pd.DataFrame({"x": x, "y": y, "ekimae": eki, "people": f[y, x], "true_power": true, "estimate": est,
                       "bar": bar, "opened": opened, "sales": np.where(opened, sales, np.nan)})
    return df, f, stations


def measures(df, k=NEXT_K):
    o = df[df.opened]
    oe, on = o[o.ekimae], o[~o.ekimae]
    ae, an = df[df.ekimae], df[~df.ekimae]
    r = {"n_cand": len(df), "n_ekimae": int(df.ekimae.sum()), "n_open": len(o), "n_open_eki": len(oe), "n_open_other": len(on),
         "open_sales_eki": oe.sales.mean(), "open_sales_other": on.sales.mean(),
         "open_gap": oe.sales.mean() - on.sales.mean(),
         "all_gap": ae.true_power.mean() - an.true_power.mean(),
         "open_sales_mean": o.sales.mean(), "all_power_mean": df.true_power.mean(),
         "shortfall_vs_est": (o.sales - o.estimate).mean(),
         "shortfall_true_vs_est": (o.true_power - o.estimate).mean()}
    # 次に出すなら：まだ出していない駅前の候補地のうち、見込みの高い順に k か所の本当の力
    rest_e = ae[~ae.opened].sort_values("estimate", ascending=False).head(k)
    rest_n = an[~an.opened].sort_values("estimate", ascending=False).head(k)
    r["next_eki_power"] = rest_e.true_power.mean() if len(rest_e) else np.nan
    r["next_other_power"] = rest_n.true_power.mean() if len(rest_n) else np.nan
    return r


def many(seed0, n, **p):
    rows, opened, cands = [], [], []
    for i in range(n):
        df, _, _ = make_town(np.random.default_rng(seed0 + i), **p)
        rows.append(measures(df))
        opened.append(df[df.opened].assign(town=i))
        cands.append(df[["ekimae", "true_power"]])
    return pd.DataFrame(rows), pd.concat(opened), pd.concat(cands)


def summ(res):
    """町をまたいで、出店した店をまとめて数える（駅前の店は1つの町に数か所しかないため）"""
    m, o, a = res
    oe, on = o[o.ekimae], o[~o.ekimae]
    tg = m.open_gap.dropna()
    return {"towns": int(len(m)), "n_open_total": int(len(o)), "n_open_eki_total": int(len(oe)),
            "n_open_mean": round(float(m.n_open.mean()), 2), "n_open_eki_mean": round(float(m.n_open_eki.mean()), 2),
            "eki_share_cand": round(float(a.ekimae.mean()), 4),
            "open_sales_eki": round(float(oe.sales.mean()), 2),
            "open_sales_other": round(float(on.sales.mean()), 2),
            "open_gap": round(float(oe.sales.mean() - on.sales.mean()), 2),
            "open_gap_town_p10": round(float(tg.quantile(.1)), 2),
            "open_gap_town_p90": round(float(tg.quantile(.9)), 2),
            "towns_with_eki_open": int(len(tg)),
            "all_gap": round(float(a[a.ekimae].true_power.mean() - a[~a.ekimae].true_power.mean()), 2),
            "open_true_gap": round(float(oe.true_power.mean() - on.true_power.mean()), 2),
            "open_sales_mean": round(float(o.sales.mean()), 2),
            "open_estimate_mean": round(float(o.estimate.mean()), 2),
            "all_power_mean": round(float(a.true_power.mean()), 2),
            "shortfall_vs_est": round(float((o.sales - o.estimate).mean()), 2),
            "next_eki_power": round(float(m.next_eki_power.mean()), 2),
            "next_other_power": round(float(m.next_other_power.mean()), 2),
            "open_minus_all": round(float(o.sales.mean() - a.true_power.mean()), 2),
            "next_eki_minus_open_eki": round(float(m.next_eki_power.mean() - oe.sales.mean()), 2),
            "next_other_minus_open_other": round(float(m.next_other_power.mean() - on.sales.mean()), 2)}


def main():
    # 1) 例の町（data に置く）
    df, f, stations = make_town(np.random.default_rng(SEED), **BASE)
    out_df = df.copy()
    out_df.insert(0, "site_id", np.arange(1, len(df) + 1))
    out_df.round({"people": 3, "true_power": 1, "estimate": 1, "bar": 1, "sales": 1}).to_csv(DATA / "sites_example_town.csv", index=False)
    pd.DataFrame({"station": ["駅1", "駅2", "駅3"], "x": stations[:, 0].round(2), "y": stations[:, 1].round(2)}).to_csv(
        DATA / "stations_example_town.csv", index=False)
    ex = {k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else int(v)) for k, v in measures(df).items()}

    # 2) 500の町で
    res = many(SEED * 1000, N_TOWN, **BASE)
    base = summ(res)
    res[0].round(3).to_csv(RES / "towns_500.csv", index=False)

    # 3) 確かめ：置き方を1つずつ変える（各300の町）。本当の駅前の差0・20・40 と 基準の差 0〜60 は全部の組み合わせ
    rob = []
    k = 0
    for bonus in [0.0, 20.0, 40.0]:
        for gap in [0.0, 20.0, 40.0, 60.0]:
            p = dict(BASE); p["bonus"] = bonus; p["hurdle_gap"] = gap
            s = summ(many(SEED * 100000 + k * 1000, 300, **p)); k += 1
            rob.append({"factor": "本当の駅前の差×基準の差", "bonus": bonus, "hurdle_gap": gap, "est_sd": p["est_sd"],
                        "site_sd": p["site_sd"], **s})
    for key, vals, lab in [("est_sd", [0.0, 15.0, 60.0], "見込みの誤差"), ("site_sd", [20.0, 60.0], "場所どうしの差")]:
        for v in vals:
            p = dict(BASE); p[key] = v
            s = summ(many(SEED * 100000 + k * 1000, 300, **p)); k += 1
            rob.append({"factor": lab, "bonus": p["bonus"], "hurdle_gap": p["hurdle_gap"], "est_sd": p["est_sd"],
                        "site_sd": p["site_sd"], **s})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    g20 = rob[(rob.factor == "本当の駅前の差×基準の差") & (rob.bonus == 20)]
    g0 = rob[(rob.factor == "本当の駅前の差×基準の差") & (rob.bonus == 0)]
    out = {"settings_base": BASE, "n_towns": N_TOWN, "next_k": NEXT_K, "example_town": ex, "towns_500": base,
           "bonus20_open_gap_range": {"min": float(g20.open_gap.min()), "max": float(g20.open_gap.max())},
           "bonus0_open_gap_range": {"min": float(g0.open_gap.min()), "max": float(g0.open_gap.max())},
           "shortfall_range": {"min": float(rob.shortfall_vs_est.min()), "max": float(rob.shortfall_vs_est.max())}}
    json.dump(out, open(RES / "a953_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の町の地図
    fig, ax = plt.subplots(figsize=(6.9, 6.0))
    im = ax.imshow(f, origin="lower", cmap="Greys", alpha=.35, extent=(-.5, G - .5, -.5, G - .5))
    cb = fig.colorbar(im, ax=ax, shrink=.8, pad=.03); cb.set_label("人の多さ（0〜1、作成者が置いた値）")
    for sx, sy in stations:
        ax.add_patch(plt.Circle((sx, sy), BASE["station_r"], fill=False, ec=ORANGE, ls="--", lw=1))
    ax.scatter(stations[:, 0], stations[:, 1], marker="s", s=50, color=ORANGE, zorder=4, label="駅（点線の円の中が駅前）")
    c = df[~df.opened]
    ax.scatter(c.x, c.y, s=10, color=GRAY, alpha=.6, lw=0, label=f"出店しなかった候補地（{len(c)}か所）")
    o = df[df.opened]
    ax.scatter(o.x, o.y, s=40, color=BLUE, ec="white", lw=.6, zorder=5, label=f"出店した場所（{len(o)}か所）")
    ax.set_xlim(-.5, G - .5); ax.set_ylim(-.5, G - .5); ax.set_aspect("equal")
    ax.set_xlabel("東西（区画）"); ax.set_ylabel("南北（区画）")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.1), ncol=2, frameon=False, fontsize=8.5)
    ax.set_title("架空の町の出店候補地（例の町）", fontsize=12)
    save(fig, "a953_town_map.png", SRC, y=-0.06)

    # 図2：出店した店の売上と、候補地全体の本当の力（500の町）
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.3), gridspec_kw={"width_ratios": [1, 1.1]})
    ax = axes[0]
    labs = ["候補地全体の\n本当の力", "出店前の見込み\n（出店した店）", "出店した店の\n1年目の売上"]
    vals = [base["all_power_mean"], base["open_estimate_mean"], base["open_sales_mean"]]
    ax.bar(labs, vals, color=[GRAY, LIGHT, BLUE])
    for i, v in enumerate(vals):
        ax.text(i, v + 4, f"{v:.1f}", ha="center", fontsize=9.5)
    ax.set_ylim(250, 470)
    ax.set_ylabel("売上（万円／月、500の町をまとめた平均）")
    ax.tick_params(axis="x", labelsize=9)
    ax.set_title("出店した店は、候補地全体より高く、見込みより低い", fontsize=10.5)
    ax = axes[1]
    xg = np.arange(2); w = .36
    now = [base["open_sales_eki"], base["open_sales_other"]]
    nxt = [base["next_eki_power"], base["next_other_power"]]
    ax.bar(xg - w / 2, now, w, color=BLUE, label="いまの店の1年目の売上")
    ax.bar(xg + w / 2, nxt, w, color=ORANGE, label="次に出す5か所の本当の力")
    for xx, v in zip(list(xg - w / 2) + list(xg + w / 2), now + nxt):
        ax.text(xx, v + 4, f"{v:.1f}", ha="center", fontsize=9.5)
    ax.set_xticks(xg); ax.set_xticklabels(["駅前", "駅前以外"])
    ax.set_ylim(250, 470)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("次に出す場所は、いまの店ほど売れない", fontsize=10.5)
    fig.tight_layout()
    save(fig, "a953_selection_bars.png", SRC)

    # 図3：出店した店で見える駅前の差（本当の差×基準の差）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    gg = rob[rob.factor == "本当の駅前の差×基準の差"]
    for bonus, c, mk in [(0.0, GRAY, "s"), (20.0, BLUE, "o"), (40.0, ORANGE, "^")]:
        g = gg[gg.bonus == bonus]
        ax.plot(g.hurdle_gap, g.open_gap, marker=mk, color=c, lw=2, label=f"本当の駅前の差 {bonus:g}万円")
        ax.axhline(bonus, color=c, lw=.8, ls=":")
    ax.set_xticks([0, 20, 40, 60])
    ax.set_xlabel("駅前の出店の基準を、駅前以外より何万円高くしたか")
    ax.set_ylabel("出店した店で見える駅前の差（万円／月）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("見える駅前の差は、本当の差だけでなく「基準の差」でも動いた\n（各300の町。点線は本当の差）", fontsize=11)
    save(fig, "a953_gap_robustness.png", SRC)


if __name__ == "__main__":
    main()
