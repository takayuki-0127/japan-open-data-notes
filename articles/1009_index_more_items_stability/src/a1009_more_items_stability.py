"""1009 項目の数を増やすと、合計点は安定するのか？（架空のデータ）

架空の製品200点を、2か月続けて同じ項目で採点する。製品ごとに「本当の良さ」を置き、
項目の点＝本当の良さの分＋その項目だけの製品の癖（月が変わっても同じ）＋その月だけのぶれ。
はじめの3項目に、①別々の良い項目 ②はじめの項目に似た項目（写し）③本当の良さとの結びつきが弱い項目
のどれかを足して、項目の数を3→18に増やし、2か月の合計点のそろい方（安定）と、本当の良さとの近さを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1009
SRC = "架空の製品の採点（作成者が乱数で作成、seed 1009）"
rng = np.random.default_rng(SEED)

N_PROD, TOP = 200, 20
KS = [3, 6, 9, 12, 15, 18]
GOOD = {"a": 0.6, "b": 0.4}     # 良い項目：本当の良さ0.6、製品の癖0.4、月のぶれ √(1−0.36−0.16)
WEAK = {"a": 0.2, "b": 0.8}     # 弱い項目：本当の良さ0.2、製品の癖0.8
RHO = 0.8                       # 似た項目が、もとの項目の月のぶれを共有する度合い
SCEN = {"A": "①別々の良い項目を足す", "B": "②はじめの項目に似た項目を足す", "C": "③弱い項目を足す"}


def spec(scen, k, good=GOOD, weak=WEAK, rho=RHO):
    """項目ごとの (本当の良さの係数, [(癖の元, 係数)], [(月のぶれの元, 係数)])"""
    items, nu, ne = [], 0, 0

    def new_item(a, b):
        nonlocal nu, ne
        c = np.sqrt(max(1 - a * a - b * b, 0))
        it = (a, [(nu, b)], [(ne, c)])
        nu += 1; ne += 1
        return it
    for _ in range(3):
        items.append(new_item(good["a"], good["b"]))
    for j in range(k - 3):
        if scen == "A":
            items.append(new_item(good["a"], good["b"]))
        elif scen == "C":
            items.append(new_item(weak["a"], weak["b"]))
        else:  # B：親（はじめの3項目を順に）の癖をそのまま、月のぶれを rho だけ共有
            p = j % 3
            a, (u, b), (e, c) = items[p][0], items[p][1][0], items[p][2][0]
            items.append((a, [(u, b)], [(e, c * rho), (ne, c * np.sqrt(1 - rho ** 2))]))
            ne += 1
    return items, nu, ne


def formula(items):
    k = len(items)
    a = np.array([it[0] for it in items])
    S = np.outer(a, a)
    N = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            S[i, j] += sum(ci * cj for ui, ci in items[i][1] for uj, cj in items[j][1] if ui == uj)
            N[i, j] += sum(ci * cj for ei, ci in items[i][2] for ej, cj in items[j][2] if ei == ej)
    w = np.ones(k) / k
    var = w @ (S + N) @ w
    return {"retest": float(w @ S @ w / var), "validity": float(w @ a / np.sqrt(var))}


def simulate(items, nu, ne, rng, n=N_PROD):
    T = rng.standard_normal(n)
    U = rng.standard_normal((n, nu))
    idx = []
    for _ in range(2):
        E = rng.standard_normal((n, ne))
        x = np.zeros((n, len(items)))
        for i, (a, us, es) in enumerate(items):
            x[:, i] = a * T + sum(c * U[:, u] for u, c in us) + sum(c * E[:, e] for e, c in es)
        idx.append(x.mean(1))
    return T, idx[0], idx[1]


def topset(v, k=TOP):
    return set(np.argsort(-v, kind="stable")[:k])


def rank_corr(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def measure(T, m1, m2):
    return {"retest": float(np.corrcoef(m1, m2)[0, 1]), "retest_rank": rank_corr(m1, m2),
            "top20_same_next_month": len(topset(m1) & topset(m2)) / TOP,
            "validity": float(np.corrcoef(m1, T)[0, 1]), "top20_hit_true": len(topset(m1) & topset(T)) / TOP}


def run(scen, k, reps, seed0, **kw):
    items, nu, ne = spec(scen, k, **kw)
    rows = [measure(*simulate(items, nu, ne, np.random.default_rng(seed0 + r))) for r in range(reps)]
    d = pd.DataFrame(rows).mean().to_dict()
    f = formula(items)
    d.update({"formula_retest": f["retest"], "formula_validity": f["validity"]})
    return d


def main():
    # 1) 3つの足し方 × 項目の数（各300回）
    rows = []
    for si, s in enumerate(SCEN):
        for k in KS:
            d = run(s, k, 300, SEED * 10000 + si * 1000 + k * 37)
            rows.append({"scenario": SCEN[s], "k": k, **{kk: round(v, 4) for kk, v in d.items()}})
    main_tab = pd.DataFrame(rows)
    main_tab.to_csv(RES / "by_items.csv", index=False)
    # はじめの3項目は3つの足し方で同じなので、式の値は同じ
    check = {"max_abs_diff_retest_vs_formula": round(float((main_tab.retest - main_tab.formula_retest).abs().max()), 4),
             "max_abs_diff_validity_vs_formula": round(float((main_tab.validity - main_tab.formula_validity).abs().max()), 4)}
    r1 = GOOD["a"] ** 2 + GOOD["b"] ** 2
    single = {"item_retest_good": round(r1, 4), "item_retest_weak": round(WEAK["a"] ** 2 + WEAK["b"] ** 2, 4),
              "item_validity_good": GOOD["a"], "item_validity_weak": WEAK["a"]}

    # 2) 確かめ：似た項目の月のぶれの共有（rho）、弱い項目の係数（a・b）、良い項目の癖（b）を変えて（K=12、各100回）
    rob = []
    for rho in [0.0, 0.5, 0.8, 0.95, 1.0]:
        d = run("B", 12, 100, SEED * 7 + int(rho * 100) * 11, rho=rho)
        rob.append({"check": "②似た項目：月のぶれの共有", "value": rho, **{kk: round(v, 4) for kk, v in d.items()}})
    for aw in [0.1, 0.2, 0.3, 0.4]:
        for bw in [0.4, 0.6, 0.8]:
            d = run("C", 12, 100, SEED * 9 + int(aw * 100) * 1000 + int(bw * 100), weak={"a": aw, "b": bw})
            rob.append({"check": "③弱い項目：本当の良さの係数・製品の癖", "value": f"{aw}・{bw}",
                        **{kk: round(v, 4) for kk, v in d.items()}})
    for bg in [0.0, 0.4, 0.6]:
        g = {"a": 0.6, "b": bg}
        for s in "ABC":
            d = run(s, 12, 100, SEED * 13 + int(bg * 100) * 100 + ord(s), good=g)
            d3 = formula(spec(s, 3, good=g)[0])
            rob.append({"check": f"良い項目の製品の癖（{SCEN[s]}）", "value": bg,
                        "formula_retest_k3": round(d3["retest"], 4), "formula_validity_k3": round(d3["validity"], 4),
                        **{kk: round(v, 4) for kk, v in d.items()}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    base3 = formula(spec("A", 3)[0])
    rc = rob[rob.check == "③弱い項目：本当の良さの係数・製品の癖"]
    rb = rob[rob.check == "②似た項目：月のぶれの共有"]
    rg = rob[rob.check.str.startswith("良い項目の製品の癖")]
    robs = {"weak_12_validity_range": [float(rc.formula_validity.min()), float(rc.formula_validity.max())],
            "weak_12_retest_range": [float(rc.formula_retest.min()), float(rc.formula_retest.max())],
            "weak_n_validity_below_k3": int((rc.formula_validity < base3["validity"]).sum()),
            "weak_n_retest_above_k3": int((rc.formula_retest > base3["retest"]).sum()),
            "weak_n": int(len(rc)),
            "weak_n_retest_up_validity_down": int(((rc.formula_retest > base3["retest"]) &
                                                    (rc.formula_validity < base3["validity"])).sum()),
            "copy_12_retest_by_rho": dict(zip(rb.value.astype(str), rb.formula_retest)),
            "copy_12_validity_by_rho": dict(zip(rb.value.astype(str), rb.formula_validity)),
            "k3_formula": {"retest": round(base3["retest"], 4), "validity": round(base3["validity"], 4)},
            "good_b": rg[["check", "value", "formula_retest_k3", "formula_retest", "formula_validity_k3",
                          "formula_validity"]].to_dict("records")}

    # 例の1回分（K=3 と K=12）
    ex_rng = np.random.default_rng(SEED)
    T = ex_rng.standard_normal(N_PROD)
    df = pd.DataFrame({"product_id": np.arange(1, N_PROD + 1), "true": np.round(T, 4)})
    one = {}
    for s in "ABC":
        items, nu, ne = spec(s, 12)
        r = np.random.default_rng(SEED + ord(s))
        U = r.standard_normal((N_PROD, nu))
        for t in (1, 2):
            E = r.standard_normal((N_PROD, ne))
            x = np.column_stack([a * T + sum(c * U[:, u] for u, c in us) + sum(c * E[:, e] for e, c in es)
                                 for a, us, es in items])
            if s == "A":
                df[f"k3_m{t}"] = np.round(x[:, :3].mean(1), 4)
            df[f"k12_{s}_m{t}"] = np.round(x.mean(1), 4)
        one[SCEN[s]] = measure(T, df[f"k12_{s}_m1"].values, df[f"k12_{s}_m2"].values)
    one["はじめの3項目"] = measure(T, df["k3_m1"].values, df["k3_m2"].values)
    one = {k: {kk: round(v, 4) for kk, v in d.items()} for k, d in one.items()}
    df.to_csv(DATA / "products_example.csv", index=False)

    out = {"setting": {"n_products": N_PROD, "good": GOOD, "weak": WEAK, "rho_copy": RHO, "ks": KS},
           "single_item": single, "by_items_300reps": main_tab.to_dict("records"), "check_formula": check,
"robustness": robs, "one_draw_k12": one}
    json.dump(out, open(RES / "a1009_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cols = {SCEN["A"]: BLUE, SCEN["B"]: GRAY, SCEN["C"]: ORANGE}
    # 図1：2か月の合計点の相関（安定）
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9), sharex=True)
    for name, g in main_tab.groupby("scenario", sort=False):
        axes[0].plot(g.k, g.retest, "o-", color=cols[name], label=name)
        axes[1].plot(g.k, g.validity, "o-", color=cols[name], label=name)
    axes[0].set_ylabel("2か月の合計点の相関（安定）"); axes[1].set_ylabel("本当の良さとの相関")
    for a in axes:
        a.set_ylim(0.6, 1.0); a.set_xticks(KS); a.set_xlabel("項目の数（はじめの3項目＋足した項目）")
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("項目を足して安定が上がっても、本当の良さに近づくとは限らない（各300回の平均）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1009_retest_validity.png", SRC)

    # 図2：上位20点の当たりと翌月の重なり（K=3 と K=12）
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    labels, v1, v2 = [], [], []
    k3 = main_tab[(main_tab.k == 3)].iloc[0]
    labels.append("はじめの3項目"); v1.append(k3.top20_same_next_month * 100); v2.append(k3.top20_hit_true * 100)
    for s in "ABC":
        r = main_tab[(main_tab.scenario == SCEN[s]) & (main_tab.k == 12)].iloc[0]
        labels.append(SCEN[s].replace("を足す", "を足して12項目")); v1.append(r.top20_same_next_month * 100); v2.append(r.top20_hit_true * 100)
    y = np.arange(len(labels))[::-1]
    ax.barh(y + 0.2, v1, height=0.38, color=LIGHT, label="上位20点のうち、翌月も上位20点")
    ax.barh(y - 0.2, v2, height=0.38, color=BLUE, label="上位20点のうち、本当の上位20点")
    for yy, a, b in zip(y, v1, v2):
        ax.text(a + 1, yy + 0.2, f"{a:.1f}%", va="center", fontsize=8.5)
        ax.text(b + 1, yy - 0.2, f"{b:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlim(0, 100)
    ax.set_xlabel("%（製品200点、各300回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    ax.set_title("翌月も上位に残ることと、本当に上位であることは別", pad=28)
    save(fig, "a1009_top20.png", SRC)

    # 図3：弱い項目の置き方（12項目、式の値）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for bw, c in zip([0.4, 0.6, 0.8], [LIGHT, BLUE, INK]):
        g = rc[rc.value.str.endswith(f"・{bw}")]
        aws = [float(v.split("・")[0]) for v in g.value]
        ax.plot(g.formula_retest, g.formula_validity, "o-", color=c, label=f"弱い項目の製品の癖 {bw}")
        for x_, y_, aw in zip(g.formula_retest, g.formula_validity, aws):
            ax.annotate(f"{aw}", (x_, y_), textcoords="offset points", xytext=(5, -10), fontsize=7.5, color=c)
    ax.scatter([base3["retest"]], [base3["validity"]], s=60, color=ORANGE, zorder=5)
    ax.annotate("はじめの3項目", (base3["retest"], base3["validity"]), textcoords="offset points", xytext=(-78, 6),
                fontsize=9, color=ORANGE)
    ax.axhline(base3["validity"], color=ORANGE, lw=0.8, ls="--"); ax.axvline(base3["retest"], color=ORANGE, lw=0.8, ls="--")
    ax.set_xlabel("2か月の合計点の相関（安定、式の値）"); ax.set_ylabel("本当の良さとの相関（式の値）")
    ax.set_ylim(0.6, 0.9); ax.set_xlim(0.48, 0.95)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("弱い項目を9つ足したとき（点の横の数は本当の良さの係数）")
    save(fig, "a1009_weak_items.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
