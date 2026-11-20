"""810 低評価に返信した店は、その後の平均が上がるのか？（選ばれ方の偏り）（架空のデータ）

架空の店3,000軒。店ごとに「本当の満足度」（来た人全員が星を付けたときの平均）を置き、期間中は変わらないとする。
口コミは 前の期間A（30件）→ 直前の期間B（10件）→ 返信を始めたあとの期間C（20件）の順に付く。
直前の期間Bの平均が低かった店ほど、低評価に返信を始めやすい。返信そのものの効き目は作成者が置く（基本は0）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 810
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 810）"
rng = np.random.default_rng(SEED)
N_SHOP, N_A, N_B, N_C = 3000, 30, 10, 20
DIP = 3.3                  # 期間Bの平均がこれ以下なら「低評価が続いた」
P_REPLY_DIP, P_REPLY_OTHER = 0.6, 0.1
N_REP = 200
STARS = np.arange(1, 6)


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ作り方）"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def period_mean(rng, true, k):
    p = star_probs(np.clip(true, 1.05, 4.95))
    return (rng.multinomial(k, p) * STARS).sum(1) / k


def make_shops(rng, n=N_SHOP, effect=0.0, n_b=N_B, motivated=False):
    """effect：返信そのものの効き目（期間Cの本当の満足度に足す）
    motivated=True：やる気のある店（3割）は返信しやすく、返信と関係なく期間Cに0.15よくなる"""
    true = np.clip(rng.normal(3.8, 0.35, n), 2.5, 4.8)
    a, b = period_mean(rng, true, N_A), period_mean(rng, true, n_b)
    dip = b <= DIP
    if motivated:
        mot = rng.random(n) < 0.3
        p = np.where(dip, np.where(mot, 0.9, 0.45), np.where(mot, 0.2, 0.06))
    else:
        mot = np.zeros(n, bool)
        p = np.where(dip, P_REPLY_DIP, P_REPLY_OTHER)
    reply = rng.random(n) < p
    true_c = true + effect * reply + 0.15 * mot
    c = period_mean(rng, true_c, N_C)
    return pd.DataFrame({"shop_id": np.arange(1, n + 1), "true": true, "mean_A": a, "mean_B": b, "mean_C": c,
                         "dip": dip, "reply": reply})


def estimates(df):
    r, o = df[df.reply], df[~df.reply]
    naive = (r.mean_C - r.mean_B).mean()
    did = naive - (o.mean_C - o.mean_B).mean()
    # 直前の平均（期間B）が同じ0.1刻みの店どうしで、返信した店としなかった店を比べる
    bins = np.floor(df.mean_B * 10 + 1e-9) / 10
    d = df.assign(bin=bins, ch=df.mean_C - df.mean_B)
    t = d.groupby(["bin", "reply"]).ch.mean().unstack()
    w = d[d.reply].groupby("bin").size()
    t = t.dropna()
    w = w.reindex(t.index).fillna(0)
    matched = float(((t[True] - t[False]) * w).sum() / w.sum())
    long_before = (r.mean_C - r.mean_A).mean()
    return {"返信した店の前後（B→C）": naive, "返信しなかった店の前後を引く": did,
            "直前の平均が同じ店どうしで比べる": matched, "前の期間Aと比べる": long_before}


def run(effect=0.0, n_b=N_B, motivated=False, reps=N_REP, seed_add=0):
    rows = []
    for r in range(reps):
        df = make_shops(np.random.default_rng(SEED * 1000 + seed_add + r), effect=effect, n_b=n_b, motivated=motivated)
        rows.append(estimates(df))
    e = pd.DataFrame(rows)
    return {k: {"mean": round(float(e[k].mean()), 3), "p10": round(float(e[k].quantile(.1)), 3),
                "p90": round(float(e[k].quantile(.9)), 3)} for k in e.columns}


def main():
    df = make_shops(rng)
    df.round(4).to_csv(DATA / "shops.csv", index=False, float_format="%.4f")
    g = df.groupby("reply")[["true", "mean_A", "mean_B", "mean_C"]].mean()
    one = {"shops_reply": int(df.reply.sum()), "shops_no_reply": int((~df.reply).sum()),
           "reply_share_among_dip": round(float(df[df.dip].reply.mean()), 3),
           "dip_share": round(float(df.dip.mean()), 3),
           "periods": {("reply" if k else "no_reply"): {c: round(float(v), 3) for c, v in row.items()}
                       for k, row in g.iterrows()}}

    base = run(0.0)
    eff = run(0.1, seed_add=50000)
    mot = run(0.0, motivated=True, seed_add=90000)
    win = {nb: run(0.0, n_b=nb, reps=100, seed_add=100000 + nb)["返信した店の前後（B→C）"] for nb in [5, 10, 20]}

    tbl = pd.DataFrame({"効き目0（基本）": {k: v["mean"] for k, v in base.items()},
                        "効き目+0.10": {k: v["mean"] for k, v in eff.items()},
                        "効き目0・やる気のある店が返信しやすい": {k: v["mean"] for k, v in mot.items()}})
    tbl.index.name = "比べ方"
    tbl.to_csv(RES / "estimates.csv")

    out = {"settings": {"shops": N_SHOP, "reviews_A_B_C": [N_A, N_B, N_C], "dip_threshold": DIP,
                        "p_reply_dip": P_REPLY_DIP, "p_reply_other": P_REPLY_OTHER, "reps": N_REP},
           "one_draw": one, "effect_0": base, "effect_0_10": eff, "effect_0_motivated": mot,
           "naive_by_window_B": {str(k): v for k, v in win.items()}}
    json.dump(out, open(RES / "a810_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：期間ごとの平均（返信した店・しなかった店）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = ["前の期間A\n（30件）", "直前の期間B\n（10件）", "返信のあとC\n（20件）"]
    for k, col, lab in [(True, ORANGE, "低評価に返信した店"), (False, BLUE, "返信しなかった店")]:
        v = g.loc[k, ["mean_A", "mean_B", "mean_C"]].values
        ax.plot(xs, v, marker="o", color=col, lw=2, label=lab)
        for x, y in zip(xs, v):
            ax.text(x, y + (0.025 if k else -0.045), f"{y:.2f}", ha="center", fontsize=9, color=col)
        ax.axhline(g.loc[k, "true"], color=col, lw=1, ls=":")
    ax.set_ylabel("星の平均（店の平均）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.text(0.5, (g.loc[True, "true"] + g.loc[False, "true"]) / 2, "点線：本当の満足度（どの期間も同じ）", fontsize=8, color=GRAY, ha="center")
    ax.set_ylim(3.4, 3.92)
    ax.set_title("返信の効き目は0と置いたのに、返信した店の平均は上がって見える")
    save(fig, "a810_periods.png", SRC)

    # 図2：比べ方ごとの見積もり（効き目0と+0.10）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    names = list(base.keys())
    y = np.arange(len(names))
    ax.barh(y + 0.2, [base[k]["mean"] for k in names], height=0.38, color=BLUE, label="本当の効き目 0")
    ax.barh(y - 0.2, [eff[k]["mean"] for k in names], height=0.38, color=GREEN, label="本当の効き目 +0.10")
    def lab(v):
        return "0.00" if abs(v) < 0.005 else f"{v:+.2f}"
    for i, k in enumerate(names):
        ax.text(max(base[k]["mean"], 0) + 0.005, i + 0.2, lab(base[k]["mean"]), va="center", fontsize=8)
        ax.text(max(eff[k]["mean"], 0) + 0.005, i - 0.2, lab(eff[k]["mean"]), va="center", fontsize=8)
    ax.axvline(0, color=INK, lw=.8); ax.axvline(0.1, color=GREEN, lw=1, ls=":")
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("見積もった返信の効き目（星、200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("前後を比べるだけでは、効き目を大きく見積もる")
    save(fig, "a810_methods.png", SRC)

    # 図3：直前の期間Bの件数と、前後比べの見かけの効き目
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ks = list(win.keys())
    vals = [win[k]["mean"] for k in ks]
    ax.bar([f"{k}件" for k in ks], vals, color=ORANGE)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.01, f"+{v:.2f}", ha="center", fontsize=9)
    ax.set_xlabel("返信を決めるときに見た直前の口コミの件数（期間B）")
    ax.set_ylabel("見かけの効き目（星）"); ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title("直前の件数が少ないほど、たまたまの落ち込みで見かけの効き目が大きい")
    save(fig, "a810_window.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
