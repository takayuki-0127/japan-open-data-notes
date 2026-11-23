"""1018 キャンセル率は、何を分母にするかでどう変わるのか？（架空のデータ）

架空の宿3軒。1か月の宿泊日の予約を乱数で作り、組の人数ごとの取り消しの起きやすさと、
日付の変更（台帳では「元の予約の取り消し＋新しい予約」と記録される）の割合を作成者が置く。
同じ1か月を、5つの分母・分子の組み合わせでキャンセル率にし、値と宿の順位がどう変わるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1018
SRC = "架空の宿の予約台帳（作成者が乱数で作成、seed 1018）"
SIZES = np.arange(1, 9)
P_CANCEL_BASE = np.array([0.09, 0.09, 0.12, 0.12, 0.20, 0.20, 0.20, 0.20])   # 1〜8人の組の取り消しの起きやすさ（基本）


def size_probs(group_share):
    """1〜4人と5〜8人（団体）の割合"""
    small = np.array([0.20, 0.45, 0.12, 0.13]); small = small / small.sum() * (1 - group_share)
    big = np.full(4, group_share / 4)
    return np.concatenate([small, big])


INNS = {
    "宿A（団体が多い）": dict(scale=0.85, group_share=0.30, change=0.03),
    "宿B（日付の変更が多い）": dict(scale=0.90, group_share=0.10, change=0.20),
    "宿C（基本）": dict(scale=1.00, group_share=0.10, change=0.08),
}
DEFS = [("true_count", "①取り消し÷受けた予約（変更を除く）"),
        ("ledger", "②台帳のまま（変更も取り消し・予約に数える）"),
        ("per_stay", "③取り消し÷泊まった予約（変更を除く）"),
        ("ledger_per_stay", "④台帳の取り消し÷泊まった予約"),
        ("people", "⑤取り消した人数÷予約の人数（変更を除く）")]


def one_month(rng, n_mean, scale, group_share, change, p_cancel=P_CANCEL_BASE, keep=False):
    n = rng.poisson(n_mean)
    size = rng.choice(SIZES, size=n, p=size_probs(group_share))
    cancel = rng.random(n) < np.clip(p_cancel[size - 1] * scale, 0, 1)
    changed = (~cancel) & (rng.random(n) < change)       # 日付を変えて泊まった予約
    n_c, n_ch = int(cancel.sum()), int(changed.sum())
    stays = n - n_c
    r = {"bookings": n, "cancels": n_c, "changes": n_ch, "stays": stays,
         "true_count": n_c / n, "ledger": (n_c + n_ch) / (n + n_ch), "per_stay": n_c / stays,
         "ledger_per_stay": (n_c + n_ch) / stays, "people": size[cancel].sum() / size.sum()}
    if keep:
        return r, pd.DataFrame({"booking_id": np.arange(1, n + 1), "party_size": size,
                                "cancelled": cancel.astype(int), "date_changed": changed.astype(int)})
    return r


def months(seed, k, n_mean, **kw):
    rng = np.random.default_rng(seed)
    return pd.DataFrame([one_month(rng, n_mean, **kw) for _ in range(k)])


def pct(x):
    return round(float(x) * 100, 2)


def main():
    t0 = time.time()
    res = {"inns": {}, "setting": {"p_cancel_base_by_size_1to8": P_CANCEL_BASE.tolist(),
                                   "bookings_per_month_mean": 300, "months": 2000}}
    # 1) 3軒の宿、1か月300件前後を2,000か月（長い目で見た値と、1か月ごとの振れ）
    rows, monthly = [], {}
    for i, (name, kw) in enumerate(INNS.items()):
        m = months(SEED * 10 + i, 2000, 300, **kw)
        monthly[name] = m
        tot = m.sum(numeric_only=True)
        # 長い目で見た値（2,000か月を合わせた件数から）と、1か月ごとの10〜90%
        p = size_probs(kw["group_share"])
        pc = np.clip(P_CANCEL_BASE * kw["scale"], 0, 1)
        exp_true = float((p * pc).sum())
        exp_people = float((p * pc * SIZES).sum() / (p * SIZES).sum())
        exp_ledger = (exp_true + (1 - exp_true) * kw["change"]) / (1 + (1 - exp_true) * kw["change"])
        d = {"setting": kw, "formula": {"true_count": pct(exp_true), "per_stay": pct(exp_true / (1 - exp_true)),
                                        "ledger": pct(exp_ledger),
                                        "ledger_per_stay": pct((exp_true + (1 - exp_true) * kw["change"]) / (1 - exp_true)),
                                        "people": pct(exp_people)}}
        for key, lab in DEFS:
            d[key] = {"mean_month": pct(m[key].mean()), "p10": pct(m[key].quantile(0.1)), "p90": pct(m[key].quantile(0.9))}
            rows.append({"inn": name, "definition": lab, "mean_month": pct(m[key].mean()),
                         "p10_month": pct(m[key].quantile(0.1)), "p90_month": pct(m[key].quantile(0.9)),
                         "formula": d["formula"][key]})
        res["inns"][name] = d
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "inns_by_definition.csv", index=False)
    diff = (tab.mean_month - tab.formula).abs()
    res["max_abs_diff_mean_vs_formula_pt"] = round(float(diff.max()), 2)
    res["max_abs_diff_at"] = tab.loc[diff.idxmax(), ["inn", "definition"]].tolist()
    res["true_count_innA_minus_innC_pt"] = round(res["inns"]["宿A（団体が多い）"]["true_count"]["mean_month"]
                                                 - res["inns"]["宿C（基本）"]["true_count"]["mean_month"], 2)

    # 宿の順位（長い目で見た値）と、1か月ごとの順位の入れかわり
    names = list(INNS)
    order = {}
    for key, lab in DEFS:
        vals = {n: res["inns"][n][key]["mean_month"] for n in names}
        order[key] = sorted(names, key=lambda n: -vals[n])
    res["order_high_to_low"] = order
    top_share = {}
    for key, _ in DEFS:
        arr = np.vstack([monthly[n][key].values for n in names])     # 3×2000
        top = arr.argmax(0)
        top_share[key] = {n: pct((top == i).mean()) for i, n in enumerate(names)}
    res["monthly_top_share"] = top_share

    # 1か月の中で、①と⑤で1位の宿が違う月の割合
    a1 = np.vstack([monthly[n]["true_count"].values for n in names]).argmax(0)
    a2 = np.vstack([monthly[n]["ledger"].values for n in names]).argmax(0)
    a5 = np.vstack([monthly[n]["people"].values for n in names]).argmax(0)
    res["monthly_top_differs"] = {"true_vs_ledger": pct((a1 != a2).mean()), "true_vs_people": pct((a1 != a5).mean()),
                                  "ledger_vs_people": pct((a2 != a5).mean())}

    # 1か月分のデータ（宿C）
    _, one = one_month(np.random.default_rng(SEED), 300, keep=True, **INNS["宿C（基本）"])
    one.to_csv(DATA / "one_month_innC.csv", index=False)

    # 2) 確かめ：取り消しの起きやすさ×日付の変更×人数による差（36通り、各300か月）
    grid = []
    k = 0
    for scale in [0.5, 1.0, 2.0]:
        for ch in [0.0, 0.04, 0.08, 0.15]:
            for eff_name, pc in [("人数で差なし", np.full(8, 0.12)), ("基本", P_CANCEL_BASE),
                                 ("団体ほど大きい", np.array([0.07, 0.07, 0.12, 0.12, 0.30, 0.30, 0.30, 0.30]))]:
                m = months(SEED * 1000 + k, 300, 300, scale=scale, group_share=0.10, change=ch, p_cancel=pc); k += 1
                g = {"cancel_scale": scale, "change": ch, "size_effect": eff_name}
                for key, _ in DEFS:
                    g[key] = pct(m[key].mean())
                g["per_stay_minus_true"] = round(g["per_stay"] - g["true_count"], 2)
                g["ledger_minus_true"] = round(g["ledger"] - g["true_count"], 2)
                g["people_minus_true"] = round(g["people"] - g["true_count"], 2)
                g["max_over_min"] = round(max(g[x] for x, _ in DEFS) / min(g[x] for x, _ in DEFS), 3)
                grid.append(g)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    res["grid_range"] = {c: [float(grid[c].min()), float(grid[c].max())] for c in
                         ["true_count", "per_stay_minus_true", "ledger_minus_true", "people_minus_true", "max_over_min"]}
    res["grid_counts"] = {"change0": int((grid.change == 0).sum()), "no_size_effect": int((grid.size_effect == "人数で差なし").sum())}
    res["grid_range"]["ledger_minus_true_change0"] = [float(grid[grid.change == 0].ledger_minus_true.min()),
                                                      float(grid[grid.change == 0].ledger_minus_true.max())]
    res["grid_range"]["people_minus_true_no_effect"] = [float(grid[grid.size_effect == "人数で差なし"].people_minus_true.min()),
                                                        float(grid[grid.size_effect == "人数で差なし"].people_minus_true.max())]

    # 3) 1か月の件数を変えたときの、①の1か月ごとの振れ（宿C）
    vol = []
    for j, nm in enumerate([30, 100, 300, 1000]):
        m = months(SEED * 100 + j, 2000, nm, **INNS["宿C（基本）"])
        vol.append({"bookings_per_month": nm, "true_count_p10": pct(m.true_count.quantile(0.1)),
                    "true_count_p90": pct(m.true_count.quantile(0.9)), "true_count_mean": pct(m.true_count.mean())})
    vol = pd.DataFrame(vol)
    vol.to_csv(RES / "monthly_spread_by_volume.csv", index=False)

    with open(RES / "a1018_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：宿Cの同じ1か月を5つの数え方で
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    c = res["inns"]["宿C（基本）"]
    vals = [c[k]["mean_month"] for k, _ in DEFS]
    labs = [l for _, l in DEFS]
    y = np.arange(len(DEFS))
    ax.barh(y, vals, color=[BLUE, ORANGE, GREEN, "#c0392b", GRAY])
    for yi, v, k in zip(y, vals, DEFS):
        ax.text(v + 0.3, yi, f"{v:.2f}%（1か月ごとの10〜90%：{c[k[0]]['p10']:.1f}〜{c[k[0]]['p90']:.1f}%）", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=9.5); ax.invert_yaxis()
    ax.set_xlim(0, max(vals) * 1.75); ax.set_xlabel("キャンセル率（%、2,000か月の平均）")
    ax.set_title("宿C（基本）の同じ予約を、5つの数え方でキャンセル率にする")
    save(fig, "a1018_definitions.png", SRC)

    # 図2：3軒の宿の順位
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    cols = {names[0]: ORANGE, names[1]: GREEN, names[2]: BLUE}
    w = 0.26
    for i, n in enumerate(names):
        v = [res["inns"][n][k]["mean_month"] for k, _ in DEFS]
        ax.bar(np.arange(len(DEFS)) + (i - 1) * w, v, w, color=cols[n], label=n)
    ax.set_xticks(np.arange(len(DEFS))); ax.set_xticklabels(["①", "②台帳", "③泊まった\n予約で割る", "④台帳÷\n泊まった予約", "⑤人数"])
    ax.set_ylabel("キャンセル率（%、2,000か月の平均）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("3軒の宿のキャンセル率：数え方で1位が入れかわる")
    save(fig, "a1018_inns.png", SRC, y=-0.12)

    # 図3：36通りで、①との差
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for col, lab, cc in [("per_stay_minus_true", "③泊まった予約で割る", GREEN), ("ledger_minus_true", "②台帳のまま", ORANGE),
                         ("people_minus_true", "⑤人数", GRAY)]:
        ax.scatter(grid.true_count, grid[col], label=lab, color=cc, s=28, alpha=0.85)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("①取り消し÷受けた予約（%）"); ax.set_ylabel("①との差（ポイント）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("置き方を変えた36通りでの、①との差")
    save(fig, "a1018_grid.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print(vol); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
