"""1169 控えを何世代残すかで、控えの量は世代の数に比例して増えるのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル10万件。大きさは対数が正規の形（中央値1MB、対数の標準偏差1.2）。
毎日、ファイルの一部が書きかわる。書きかわる確率はファイルごとに違い、5%の「よく書きかわるファイル」に書きかわりの80%が集まる
（1日に書きかわる件数は平均で全体の1%）。控えは毎日の終わりにとり、変わっていないファイルは前の世代と共有し、
書きかわったファイルだけを丸ごと新しく持つと置いた。残す世代の控えの量＝残す世代のどれかが指している、ファイルの版の大きさの合計。
(1) 毎日の控えを1〜60世代残す、週1回・月1回の控えを1〜12世代残す、毎日7＋週4＋月12の23世代
(2) 共有しない（毎回まるごと）なら世代の数に比例（作りどおり）。「1世代＋（残す日数）×1日に書きかわる量」の目安と比べる
(3) 確かめ：1日に書きかわる割合（0.3・1・3%）×集まり方（集まらない・50%・80%）×よく書きかわるファイルの大きさ（同じ・10分の1）の15通り（各5万件）
観察は400日目の終わり。1MB＝100万バイト、1GB＝1,000MBで数えた。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1169
SRC = "架空のアプリの保存ファイルと控え（作成者が置いた大きさと書きかわり方からの乱数、seed 1169）"
N, GN = 100_000, 50_000
T = 400
MED_MB, SIG = 1.0, 1.2
HOT = 0.05
BASE = {"c": 0.01, "s": 0.8, "hot_size": 1.0}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def schedules():
    sc = {}
    for g in range(1, 61):
        sc[("毎日", g)] = list(range(g))
    for g in range(1, 13):
        sc[("週1回", g)] = [7 * k for k in range(g)]
        sc[("月1回", g)] = [30 * k for k in range(g)]
    sc[("毎日7＋週4＋月12", 23)] = list(range(7)) + [7, 14, 21, 28] + [30 * k for k in range(1, 13)]
    return sc


def make(rng, n, c, s, hot_size):
    size = rng.lognormal(np.log(MED_MB), SIG, n)
    hot = np.zeros(n, bool)
    hot[rng.choice(n, int(n * HOT), replace=False)] = True
    size = np.where(hot, size * hot_size, size)
    p = np.where(hot, s * c / HOT, (1 - s) * c / (1 - HOT))
    return size, hot, p


def history(rng, p):
    n = len(p)
    C = np.zeros((T + 1, n), np.int16)
    for t in range(1, T + 1):
        C[t] = C[t - 1] + (rng.random(n) < p)
    return C


def volume(C, size, ages):
    days = sorted({T - a for a in ages})
    V = C[days]
    distinct = 1 + (np.diff(V, axis=0) != 0).sum(axis=0)
    return float((size * distinct).sum())


def formula(size, p, ages):
    days = sorted({T - a for a in ages})
    gaps = np.diff(days)
    extra = sum((1 - (1 - p) ** g) for g in gaps) if len(gaps) else 0
    return float((size * (1 + extra)).sum())


def run(rng, n, c, s, hot_size, sc):
    size, hot, p = make(rng, n, c, s, hot_size)
    C = history(rng, p)
    full = size.sum()
    daily = (size * p).sum()
    rows = []
    for (kind, g), ages in sc.items():
        v = volume(C, size, ages)
        span = max(ages)
        rows.append({"schedule": kind, "generations": g, "span_days": span, "volume_gb": r(v / 1000, 3),
                     "over_one_gen": r(v / full), "no_share_over_one_gen": g,
                     "linear_rule_over_one_gen": r((full + span * daily) / full),
                     "linear_rule_over_actual": r((full + span * daily) / v),
                     "formula_over_actual": r(formula(size, p, ages) / v)})
    return pd.DataFrame(rows), size, hot, p, C


def main():
    rng = np.random.default_rng(SEED)
    sc = schedules()
    df, size, hot, p, C = run(rng, N, BASE["c"], BASE["s"], BASE["hot_size"], sc)
    df.to_csv(RES / "base_schedules.csv", index=False)
    full = size.sum()
    changed_bytes_per_day = (size * p).sum()
    real_daily = (np.diff(C[T - 100:].astype(np.int32), axis=0) != 0) * size[None, :]
    out = {"setting": {"files": N, "median_mb": MED_MB, "log_sigma": SIG, "hot_share": HOT, "hot_share_of_changes": BASE["s"],
                       "daily_changed_count_share": BASE["c"], "p_hot": r(BASE["s"] * BASE["c"] / HOT, 4),
                       "p_cold": r((1 - BASE["s"]) * BASE["c"] / (1 - HOT), 6), "observe_day": T},
           "base": {"one_gen_gb": r(full / 1000, 3), "changed_gb_per_day_formula": r(changed_bytes_per_day / 1000, 3),
                    "changed_gb_per_day_last100_mean": r(real_daily.sum(axis=1).mean() / 1000, 3),
                    "changed_share_of_bytes_pct": r(changed_bytes_per_day / full * 100, 3),
                    "hot_bytes_share_pct": r(size[hot].sum() / full * 100, 2)}}

    def pick(kind, g):
        return df[(df.schedule == kind) & (df.generations == g)].iloc[0].to_dict()
    key = []
    for kind, g in [("毎日", 7), ("毎日", 14), ("毎日", 23), ("毎日", 30), ("毎日", 60), ("週1回", 4), ("週1回", 12),
                    ("月1回", 6), ("月1回", 12), ("毎日7＋週4＋月12", 23)]:
        key.append(pick(kind, g))
    out["base_key"] = key
    out["base_check"] = {"formula_over_actual_range": [r(df.formula_over_actual.min()), r(df.formula_over_actual.max())],
                         "linear_rule_range": [r(df.linear_rule_over_actual.min()), r(df.linear_rule_over_actual.max())]}
    # 1世代ふえるごとの増え（毎日）
    d = df[df.schedule == "毎日"].sort_values("generations")
    inc = np.diff(d.over_one_gen.values)
    out["base_daily_increment"] = {"gen2": r(inc[0]), "gen10": r(inc[8]), "gen30": r(inc[28]), "gen60": r(inc[58])}
    m = df[df.schedule == "月1回"].sort_values("generations")
    minc = np.diff(m.over_one_gen.values)
    out["base_monthly_increment"] = {"gen2": r(minc[0]), "gen12": r(minc[10])}
    # 書きかわる件の重なり：よく書きかわるファイルの30日での書きかわり
    out["base"]["hot_changed_in_30days_pct"] = r((1 - (1 - p[hot][0]) ** 30) * 100, 2)
    out["base"]["cold_changed_in_30days_pct"] = r((1 - (1 - p[~hot][0]) ** 30) * 100, 2)
    pd.DataFrame({"file_id": np.arange(1, 5001), "size_mb": np.round(size[:5000], 4), "often_changed": hot[:5000].astype(int),
                  "change_prob_per_day": np.round(p[:5000], 6), "changes_in_400_days": C[T, :5000]}
                 ).to_csv(DATA / "files_example.csv", index=False)
    print("base", round(time.time() - T0, 1), flush=True)

    # (3) 15通り
    small = {k: sc[k] for k in [("毎日", 30), ("月1回", 12), ("毎日7＋週4＋月12", 23), ("週1回", 12)]}
    grows = []
    for c in [0.003, 0.01, 0.03]:
        for s, hs in [(0.0, 1.0), (0.5, 1.0), (0.5, 0.1), (0.8, 1.0), (0.8, 0.1)]:
            g, gsize, ghot, gp, _ = run(rng, GN, c, s, hs, small)
            rec = {"daily_changed_count_share": c, "hot_share_of_changes": s, "hot_size_factor": hs,
                   "changed_share_of_bytes_pct": r((gsize * gp).sum() / gsize.sum() * 100, 3)}
            for _, row in g.iterrows():
                tag = {"毎日": "daily30", "月1回": "monthly12", "毎日7＋週4＋月12": "mixed23", "週1回": "weekly12"}[row.schedule]
                rec[f"{tag}_over_one_gen"] = row.over_one_gen
                rec[f"{tag}_linear_rule_over_actual"] = row.linear_rule_over_actual
                rec[f"{tag}_linear_rule_over_one_gen"] = row.linear_rule_over_one_gen
                rec[f"{tag}_formula_over_actual"] = row.formula_over_actual
            grows.append(rec)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid)}
    for tag in ["daily30", "weekly12", "monthly12", "mixed23"]:
        out["grid"][tag] = {"over_one_gen_range": [r(grid[f"{tag}_over_one_gen"].min()), r(grid[f"{tag}_over_one_gen"].max())],
                            "linear_rule_range": [r(grid[f"{tag}_linear_rule_over_actual"].min()),
                                                  r(grid[f"{tag}_linear_rule_over_actual"].max())],
                            "formula_range": [r(grid[f"{tag}_formula_over_actual"].min()), r(grid[f"{tag}_formula_over_actual"].max())]}
    out["grid"]["monthly12_vs_daily30_lower_count"] = int((grid.monthly12_over_one_gen < grid.daily30_over_one_gen).sum())
    out["grid"]["mixed23_vs_daily30_higher_count"] = int((grid.mixed23_over_one_gen > grid.daily30_over_one_gen).sum())
    out["headline"] = {k: v for k, v in [("daily30", pick("毎日", 30)["over_one_gen"]), ("daily60", pick("毎日", 60)["over_one_gen"]),
                                         ("weekly12", pick("週1回", 12)["over_one_gen"]),
                                         ("monthly12", pick("月1回", 12)["over_one_gen"]),
                                         ("mixed23", pick("毎日7＋週4＋月12", 23)["over_one_gen"]),
                                         ("monthly12_linear_rule", pick("月1回", 12)["linear_rule_over_actual"])]}

    # 図1：世代の数と控えの量（基本）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for kind, c_, mk in [("毎日", BLUE, "-"), ("週1回", GREEN, "o-"), ("月1回", ORANGE, "s-")]:
        g = df[df.schedule == kind].sort_values("generations")
        ax.plot(g.generations, g.over_one_gen, mk, color=c_, ms=4, lw=2, label=f"{kind}の控え")
    mx = pick("毎日7＋週4＋月12", 23)
    ax.plot([23], [mx["over_one_gen"]], "D", color=INK, ms=7, label="毎日7＋週4＋月12（23世代）")
    ax.set_xlabel("残す世代の数")
    ax.set_ylabel("控えの量÷1世代の量（倍）")
    ax.set_ylim(0, 2.8)
    ax.set_xlim(0, 61)
    ax.set_title(f"毎日の控え60世代で{pick('毎日', 60)['over_one_gen']}倍、月1回12世代で{pick('月1回', 12)['over_one_gen']}倍（共有するとき）")
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.text(40, 0.3, "共有しない（毎回まるごと）なら\n世代の数と同じ倍数（作りどおり）", fontsize=8.5, color=GRAY)
    save(fig, "a1169_generations.png", SRC + "　400日目の終わり")

    # 図2：同じ世代数の比べ（12世代）と、残す日数の目安
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    items = [("毎日", 12), ("週1回", 12), ("月1回", 12), ("毎日7＋週4＋月12", 23)]
    labs = ["毎日\n12世代\n（11日分）", "週1回\n12世代\n（77日分）", "月1回\n12世代\n（330日分）", "毎日7＋週4＋月12\n23世代\n（360日分）"]
    act = [pick(k, g)["over_one_gen"] for k, g in items]
    lin = [pick(k, g)["linear_rule_over_one_gen"] for k, g in items]
    x = np.arange(len(items))
    ax.bar(x - 0.2, act, 0.4, color=BLUE, label="実際の控えの量")
    ax.bar(x + 0.2, lin, 0.4, color=LIGHT, label="目安：1世代＋残す日数×1日に書きかわる量")
    for xi, a, l in zip(x, act, lin):
        ax.text(xi - 0.2, a + 0.05, f"{a}", ha="center", fontsize=8, color=INK)
        ax.text(xi + 0.2, l + 0.05, f"{l}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x, labs, fontsize=8.5)
    ax.set_ylabel("1世代の量に対する倍数")
    ax.set_ylim(0, max(lin) * 1.15)
    ax.set_title("同じ12世代でも残す日数が長いほど多く、目安は月1回で出すぎた")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    save(fig, "a1169_same_count.png", SRC + "　400日目の終わり")

    # 図3：15通りで、月1回12世代の量と目安
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    lab = [f"{c*100:g}%・{int(s*100)}%{'・小' if hs < 1 else ''}" for c, s, hs in
           zip(grid.daily_changed_count_share, grid.hot_share_of_changes, grid.hot_size_factor)]
    x = np.arange(len(grid))
    ax.bar(x - 0.2, grid.monthly12_over_one_gen, 0.4, color=ORANGE, label="月1回12世代の実際の量")
    ax.bar(x + 0.2, grid.monthly12_linear_rule_over_one_gen, 0.4, color=LIGHT,
           label="目安：1世代＋330日×1日に書きかわる量")
    ax.set_xticks(x, lab, rotation=60, fontsize=7.5, ha="right")
    ax.set_xlabel("1日に書きかわる件数の割合・よく書きかわる5%のファイルに集まる割合\n（0%：集まらない、小：そのファイルが10分の1の大きさ）", fontsize=9.5)
    ax.set_ylabel("1世代の量に対する倍数")
    ax.set_ylim(0, None)
    ax.set_title("月1回12世代では、15通りすべてで実際の量が目安を下回った")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1169_grid_monthly.png", SRC + "　15通り（各5万件）", y=-0.2)

    with open(RES / "a1169_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(json.dumps(out["headline"], ensure_ascii=False), round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
