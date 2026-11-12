"""A363 たまにしか売れない商品の需要は、どの方法で予測するのがよいか
0の日が多い架空の需要に、移動平均・指数平滑・クロストン法・SBA・TSB（売れる確率と1回の量を分けて見る）を当て、
予測の偏りと、その予測で発注したときの欠品・在庫を比べる。乱数の種は363。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N_SKU, T, WARM, LEAD = 363, 400, 730, 365, 5
SIZE_MEAN = 3.0
METHODS = ["移動平均（56日）", "指数平滑", "クロストン法", "SBA（クロストン法の補正）", "TSB（売れる確率を毎日見直す）"]
COLS = [GRAY, LIGHT, BLUE, GREEN, ORANGE]
SRC = "架空のデータ（作成者が乱数で作成、seed 363）"


def make_demand(rng, p_path):
    """p_path[t]＝その日に売れる確率。売れた日の量は 1＋ポアソン（平均3個）"""
    occ = rng.random((N_SKU, T)) < p_path[None, :]
    size = 1 + rng.poisson(SIZE_MEAN - 1, (N_SKU, T))
    return occ * size


def rate_forecasts(d, alpha=0.1, beta=0.05, window=56):
    """各方法の「1日あたりの需要」の予測。f[m][:, t] は t 日目の朝の予測（t-1 日までの実績で作る）"""
    n, T_ = d.shape
    f = {m: np.zeros((n, T_)) for m in METHODS}
    c = np.concatenate([np.zeros((n, 1)), np.cumsum(d, axis=1)], axis=1)
    ses = d[:, :window].mean(axis=1).copy()
    z = np.full(n, SIZE_MEAN); q = np.full(n, 1 / max(d[:, :window].astype(bool).mean(), 0.01)); gap = np.ones(n)
    p = np.full(n, d[:, :window].astype(bool).mean()); zt = np.full(n, SIZE_MEAN)
    for t in range(T_):
        lo = max(0, t - window)
        f["移動平均（56日）"][:, t] = (c[:, t] - c[:, lo]) / max(t - lo, 1)
        f["指数平滑"][:, t] = ses
        f["クロストン法"][:, t] = z / q
        f["SBA（クロストン法の補正）"][:, t] = (1 - alpha / 2) * z / q
        f["TSB（売れる確率を毎日見直す）"][:, t] = p * zt
        x = d[:, t]; hit = x > 0
        ses = ses + alpha * (x - ses)
        z = np.where(hit, z + alpha * (x - z), z)              # 1回の量：売れた日だけ見直す
        q = np.where(hit, q + alpha * (gap - q), q)            # 売れる間隔：売れた日だけ見直す
        gap = np.where(hit, 1.0, gap + 1)
        p = p + beta * (hit - p)                               # 売れる確率：毎日見直す
        zt = np.where(hit, zt + alpha * (x - zt), zt)
    return f


def inventory(d, rate, cover=2.0):
    """毎日発注。目標の在庫＝予測×（納期＋1日）×cover（切り上げ、最低1個）。足りない分は売り逃す"""
    n, T_ = d.shape
    on_hand = np.ceil(rate[:, WARM] * (LEAD + 1) * cover).clip(1)
    pipeline = np.zeros((n, LEAD))
    stockouts = np.zeros(n); demand_days = np.zeros(n); served = np.zeros(n); total = np.zeros(n); inv = np.zeros(n)
    for t in range(WARM, T_):
        on_hand = on_hand + pipeline[:, 0]; pipeline = np.roll(pipeline, -1, axis=1); pipeline[:, -1] = 0
        S = np.ceil(rate[:, t] * (LEAD + 1) * cover).clip(1)
        order = (S - on_hand - pipeline.sum(axis=1)).clip(0); pipeline[:, -1] = order
        x = d[:, t]; sold = np.minimum(x, on_hand)
        stockouts += (x > on_hand); demand_days += (x > 0); served += sold; total += x
        on_hand = on_hand - sold; inv += on_hand
    return dict(stockout_per_100_demand_days=float(stockouts.sum() / demand_days.sum() * 100),
                fill_rate=float(served.sum() / total.sum() * 100), avg_inventory=float(inv.mean() / (T_ - WARM)),
                inventory_days=float(inv.sum() / (T_ - WARM) / (total.sum() / (T_ - WARM))))


def main():
    rng = np.random.default_rng(SEED)
    out = {"n_sku": N_SKU, "eval_days": T - WARM, "lead_time": LEAD}
    acc, invr, front = [], [], []
    ex = None
    for p0 in [0.05, 0.10, 0.20, 0.40]:
        d = make_demand(rng, np.full(T, p0)); true = p0 * SIZE_MEAN
        if p0 == 0.10: ex = d[0]
        f = rate_forecasts(d)
        occ_prev = np.concatenate([np.zeros((N_SKU, 1), bool), d[:, :-1] > 0], axis=1)[:, WARM:]
        for m in METHODS:
            r = f[m][:, WARM:]
            acc.append(dict(p=p0, method=m, bias_pct=round(float((r.mean() / true - 1) * 100), 2),
                            mae_pct=round(float(np.mean(np.abs(r - true)) / true * 100), 2),
                            bias_after_sale_pct=round(float((r[occ_prev].mean() / true - 1) * 100), 2),
                            bias_other_days_pct=round(float((r[~occ_prev].mean() / true - 1) * 100), 2)))
            res = inventory(d, f[m]); res.update(p=p0, method=m); invr.append(res)
            for cover in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
                rr = inventory(d, f[m], cover); front.append(dict(p=p0, method=m, cover=cover, fill_rate=round(rr["fill_rate"], 2), inventory_days=round(rr["inventory_days"], 2)))
        # 正解の率を知っている場合（比べるための基準）
        res = inventory(d, np.full((N_SKU, T), true)); res.update(p=p0, method="本当の需要を知っている場合"); invr.append(res)
    acc = pd.DataFrame(acc); acc.to_csv(RES / "forecast_accuracy.csv", index=False)
    invr = pd.DataFrame(invr).round(3); invr.to_csv(RES / "inventory_results.csv", index=False)
    front = pd.DataFrame(front); front.to_csv(RES / "fill_vs_inventory.csv", index=False)
    # 同じ在庫（クロストン法で2倍にしたときの在庫）にそろえたときの、需要に応えられた割合
    matched = []
    for p0 in [0.05, 0.10, 0.20, 0.40]:
        ref = float(front[(front.p == p0) & (front.method == "クロストン法") & (front.cover == 2.0)].inventory_days.iloc[0])
        for m in METHODS:
            g = front[(front.p == p0) & (front.method == m)].sort_values("inventory_days")
            matched.append(dict(p=p0, method=m, inventory_days=round(ref, 2),
                                fill_rate=round(float(np.interp(ref, g.inventory_days, g.fill_rate)), 1)))
    matched = pd.DataFrame(matched); matched.to_csv(RES / "fill_at_same_inventory.csv", index=False)
    pd.DataFrame({"day": np.arange(T), "demand": ex}).to_csv(DATA / "example_demand_p10.csv", index=False)

    # --- 途中で売れなくなる商品（500日目から、売れる確率が 0.20 → 0.02） ---
    path = np.where(np.arange(T) < 500, 0.20, 0.02)
    d = make_demand(rng, path); f = rate_forecasts(d); true_after = 0.02 * SIZE_MEAN
    obs = []
    for m in METHODS:
        row = dict(method=m)
        for k in [30, 60, 120, 229]:
            row[f"ratio_day{k}"] = round(float(f[m][:, 500 + k].mean() / true_after), 2)
        # 売れなくなってからの在庫（目標の在庫の平均、個）
        S = np.ceil(f[m][:, 500:] * (LEAD + 1) * 2.0).clip(1)
        row["target_stock_last_100_days"] = round(float(S[:, -100:].mean()), 2)
        obs.append(row)
    Strue = np.ceil(np.full((N_SKU, 100), true_after) * (LEAD + 1) * 2.0).clip(1)
    obs.append(dict(method="本当の需要を知っている場合", ratio_day30=1.0, ratio_day60=1.0, ratio_day120=1.0, ratio_day229=1.0,
                    target_stock_last_100_days=round(float(Strue.mean()), 2)))
    obs = pd.DataFrame(obs); obs.to_csv(RES / "obsolescence.csv", index=False)
    obs_path = {m: f[m][:, 440:].mean(axis=0) for m in METHODS}

    out["accuracy"] = acc.to_dict("records"); out["inventory"] = invr.to_dict("records"); out["obsolescence"] = obs.to_dict("records"); out["fill_at_same_inventory"] = matched.to_dict("records")
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：予測の偏り ---
    fig, ax = plt.subplots(figsize=(9, 4.3))
    ps = [0.05, 0.10, 0.20, 0.40]; x = np.arange(len(ps)); w = 0.16
    for j, (m, c) in enumerate(zip(METHODS, COLS)):
        v = [float(acc[(acc.p == p) & (acc.method == m)].bias_pct.iloc[0]) for p in ps]
        ax.bar(x + (j - 2) * w, v, w, color=c, label=m)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{int(p * 100)}%の日に売れる" for p in ps])
    ax.set_ylabel("予測の偏り（本当の需要に対する%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
    ax.set_title("クロストン法は高めに出て、補正した SBA はほぼ0になる")
    save(fig, "a363_bias.png", SRC + "。各400商品、後半365日の予測の平均を本当の1日あたり需要と比べた")

    # --- 図2：在庫と、需要に応えられた割合 ---
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    for ax, p0 in zip(axes, [0.05, 0.20]):
        for m, c in zip(METHODS, COLS):
            g = front[(front.p == p0) & (front.method == m)].sort_values("cover")
            ax.plot(g.inventory_days, g.fill_rate, "-o", color=c, ms=4, lw=1.6, label=m)
        ax.set_xlabel("平均の在庫（1日あたり需要の何日分か）"); ax.set_title(f"{int(p0 * 100)}%の日に売れる商品"); ax.set_xlim(0, 45 if p0 == 0.05 else 25)
    axes[0].set_ylabel("需要に応えられた割合（個数、%）"); axes[1].legend(frameon=False, fontsize=8.5)
    fig.suptitle("同じ在庫で、どれだけ需要に応えられたか（左上ほどよい）", y=1.02, fontsize=13)
    save(fig, "a363_fill_vs_inventory.png", SRC + "。点は、目標の在庫を予測×6日分の0.5〜6倍にした場合。納期5日、毎日発注")

    # --- 図3：売れなくなったあと ---
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    days = np.arange(440, T)
    for m, c in zip(METHODS, COLS): ax.plot(days, obs_path[m], color=c, lw=1.8, label=m)
    ax.plot(days, np.where(days < 500, 0.6, 0.06), color=INK, lw=1, ls="--", label="本当の需要")
    ax.axvline(500, color=GRAY, lw=0.8); ax.text(503, 0.50, "ここから\n売れなくなる", fontsize=9, color=GRAY)
    ax.set_xlabel("日"); ax.set_ylabel("1日あたり需要の予測（個、400商品の平均）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("売れなくなったあと、クロストン法の予測は下がらない")
    save(fig, "a363_obsolescence.png", SRC + "。500日目から、売れる確率が20%→2%に下がる")
    print(acc.to_string()); print(invr.to_string()); print(obs.to_string()); print(matched.pivot(index="method", columns="p", values="fill_rate")); print(matched.groupby("p").inventory_days.first())


if __name__ == "__main__":
    main()
