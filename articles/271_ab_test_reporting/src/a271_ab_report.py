"""271 A/B テストの結果を、意思決定する人にどう伝えるか
架空のテスト2,000本（正解＝本当の効果が分かる）で、「有意なら採用」と「区間で3つに分ける」伝え方・決め方を比べる"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

N_TEST, N_ARM, BASE, MWE = 2000, 100000, 0.05, 0.001   # 1群10万人、基準の購入率5%、採用に見合う最小の差 0.1ポイント
SCEN = {  # 本当の差（ポイントではなく割合の差）の分布：混合の重み、平均、標準偏差
    "S1": [(0.50, 0.0, 0.0), (0.30, 0.0, 0.0010), (0.15, 0.0025, 0.0005), (0.05, -0.0025, 0.0005)],
    "S2": [(0.30, 0.0, 0.0), (0.30, 0.0, 0.0010), (0.30, 0.0025, 0.0005), (0.10, -0.0025, 0.0005)],
}


def one_test(rng, delta, n):
    a = rng.binomial(n, BASE, size=delta.shape) / n
    b = rng.binomial(n, BASE + delta) / n
    return a, b


def estimate(a, b, n):
    d = b - a
    se = np.sqrt(a * (1 - a) / n + b * (1 - b) / n)
    return d, se, d - 1.96 * se, d + 1.96 * se, 2 * (1 - __import__("scipy").stats.norm.cdf(np.abs(d) / se))


def run(scen, seed):
    rng = np.random.default_rng(seed)
    comp = rng.choice(len(SCEN[scen]), size=N_TEST, p=[w for w, _, _ in SCEN[scen]])
    mu = np.array([m for _, m, _ in SCEN[scen]])[comp]; sd = np.array([s for _, _, s in SCEN[scen]])[comp]
    delta = mu + sd * rng.standard_normal(N_TEST)
    a, b = one_test(rng, delta, N_ARM)
    d, se, lo, hi, p = estimate(a, b, N_ARM)
    t = pd.DataFrame(dict(delta=delta, d=d, se=se, lo=lo, hi=hi, p=p))
    # ルールA：有意（両側5%）で差がプラスなら採用。それ以外は「効果なし」と報告
    t["A"] = np.where((t.p < 0.05) & (t.d > 0), "採用", "効果なし")
    # ルールB：区間で3つに分ける。下限>0→採用、上限<MWE→見送り、それ以外→保留して同じ人数を追加
    t["B0"] = np.where(t.lo > 0, "採用", np.where(t.hi < MWE, "見送り", "保留"))
    a2, b2 = one_test(rng, delta, N_ARM)
    d2, se2, lo2, hi2, _ = estimate((a * N_ARM + a2 * N_ARM) / (2 * N_ARM), (b * N_ARM + b2 * N_ARM) / (2 * N_ARM), 2 * N_ARM)
    t["d2"], t["lo2"], t["hi2"] = d2, lo2, hi2
    t["B"] = np.where(t.B0 != "保留", t.B0, np.where(lo2 > 0, "採用", "見送り"))
    # 比べるための A'：B と同じ人数の合計を、全部のテストに均等に配ってルールAで決める
    n_eq = int(round(N_ARM * (1 + (t.B0 == "保留").mean())))
    a3, b3 = one_test(rng, delta, n_eq)
    _, _, lo3, _, p3 = estimate(a3, b3, n_eq)
    t["Aeq"] = np.where(lo3 > 0, "採用", "効果なし")
    return t, n_eq


def score(t, col):
    ship = t[col] == "採用"
    return dict(ship_rate=float(ship.mean()),
                harm_among_ship=float((t.delta[ship] <= 0).mean()) if ship.any() else None,
                below_mwe_among_ship=float((t.delta[ship] < MWE).mean()) if ship.any() else None,
                gain_per_test_pt=float(t.delta[ship].sum() / len(t) * 100),          # 1本あたり、採用で増えた購入率（ポイント）
                missed_worthwhile=float(((~ship) & (t.delta >= MWE)).mean()),
                worthwhile_found=float((ship & (t.delta >= MWE)).sum() / max((t.delta >= MWE).sum(), 1)))


out = {}
for sc, seed in [("S1", 271), ("S2", 272)]:
    t, n_eq = run(sc, seed)
    ns = t[t.A == "効果なし"]
    out[sc] = dict(
        n=len(t), share_true_ge_mwe=float((t.delta >= MWE).mean()), share_true_le0=float((t.delta <= 0).mean()),
        A=score(t, "A"), B=score(t, "B"), Aeq=score(t, "Aeq"), n_eq=n_eq,
        B_split={k: dict(n=int((t.B0 == k).sum()), true_ge_mwe=float((t.delta[t.B0 == k] >= MWE).mean()),
                         true_le0=float((t.delta[t.B0 == k] <= 0).mean())) for k in ("採用", "見送り", "保留")},
        B_first_look=t.B0.value_counts().to_dict(), B_extra_sample=float((t.B0 == "保留").mean()),
        nonsig=dict(n=len(ns), true_ge_mwe=float((ns.delta >= MWE).mean()), hi_ge_mwe=float((ns.hi >= MWE).mean()),
                    true_ge_mwe_and_hi_ge=float(((ns.delta >= MWE) & (ns.hi >= MWE)).mean()),
                    hi_lt_mwe=float((ns.hi < MWE).mean()), true_ge_mwe_given_hi_lt=float((ns.delta[ns.hi < MWE] >= MWE).mean())),
        half_width_pt=float((1.96 * t.se).median() * 100))
    t.to_csv(RES / f"tests_{sc}.csv", index=False, float_format="%.6g")
    if sc == "S1":
        T = t
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# ---- 図1：伝え方の型（例の1本）
ex = T[(T.A == "効果なし") & (T.B0 == "保留") & (T.d > 0.0006)].iloc[0]
fig, ax = plt.subplots(figsize=(9.5, 3.4)); ax.axis("off"); ax.set_position([0.01, 0.04, 0.98, 0.8])
boxes = [("① 効果の大きさ", f"+{ex.d*100:.2f} ポイント", f"購入率 {BASE*100:.1f}% → {(BASE+ex.d)*100:.2f}%（推定）", BLUE),
         ("② 確からしさの幅", f"{ex.lo*100:+.2f} 〜 {ex.hi*100:+.2f}", "95%区間（ポイント）。\n0 も +0.1 も、この幅に入る", GRAY),
         ("③ 判断", "保留（人数を追加）", f"採用に見合う差（+{MWE*100:.1f}）に\n届くかどうか、まだ分からない", ORANGE)]
for i, (h, v, s, c) in enumerate(boxes):
    x = 0.01 + i * 0.335
    ax.add_patch(FancyBboxPatch((x, 0.08), 0.31, 0.8, boxstyle="round,pad=0.01", fc="white", ec=c, lw=2, transform=ax.transAxes))
    ax.text(x + 0.02, 0.78, h, fontsize=11, color=c, transform=ax.transAxes, weight="bold")
    ax.text(x + 0.02, 0.5, v, fontsize=15, color=INK, transform=ax.transAxes)
    ax.text(x + 0.02, 0.18, s, fontsize=9, color=INK, transform=ax.transAxes)
fig.suptitle(f"同じ1本でも「有意差なし（p={ex.p:.2f}）」の一言と、3点セットでは伝わる中身が違う", x=0.01, ha="left", fontsize=12)
save(fig, "a271_report.png")

# ---- 図2：「効果なし」と報告された中に、本当は採用に見合う差があったもの
rng = np.random.default_rng(1)
ns = T[T.A == "効果なし"].iloc[rng.choice((T.A == "効果なし").sum(), 60, replace=False)].sort_values("d").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 4.2))
for i, r in ns.iterrows():
    c = ORANGE if r.delta >= MWE else GRAY
    ax.plot([r.lo * 100, r.hi * 100], [i, i], color=c, lw=1.6); ax.plot(r.d * 100, i, "o", color=c, ms=3)
ax.axvline(0, color=INK, lw=0.8); ax.axvline(MWE * 100, color=ORANGE, lw=1, ls="--")
ax.text(MWE * 100, len(ns) + 0.5, " 採用に見合う差 +0.1", color=ORANGE, fontsize=9)
ax.set_yticks([]); ax.set_xlabel("差（ポイント）と95%区間")
ns_all = out["S1"]["nonsig"]
ax.set_title(f"「有意差なし」の{ns_all['n']:,}本から60本：橙は本当の差が +0.1 以上だったもの（全体の{ns_all['true_ge_mwe']:.0%}）", loc="left", fontsize=11)
save(fig, "a271_nonsig.png")

# ---- 図3：ルールAとBの比べ（S1・S2）
labs = [("ship_rate", "採用した割合"), ("harm_among_ship", "採用のうち\n本当は差0以下"), ("worthwhile_found", "見合う差のある施策を\n採用できた割合"), ("gain_per_test_pt", "1本あたりの\n上積み（ポイント）")]
fig, axs = plt.subplots(1, 4, figsize=(11, 3.8))
for ax, (k, l) in zip(axs, labs):
    xs = np.arange(2)
    for j, (rule, col, lb) in enumerate([("A", GRAY, "A：有意なら採用"), ("Aeq", LIGHT, "A'：Bと同じ人数を全部に配ってA"), ("B", BLUE, "B：3つに分け、保留は人数を足す")]):
        v = [out[s][rule][k] for s in ("S1", "S2")]
        ax.bar(xs + (j - 1) * 0.27, v, 0.25, color=col, label=lb)
        for x, vv in zip(xs + (j - 1) * 0.27, v): ax.text(x, vv, (f"{vv:.3f}" if k == "gain_per_test_pt" else f"{vv:.0%}"), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(xs); ax.set_xticklabels(["想定1", "想定2"]); ax.set_title(l, fontsize=10, loc="left"); ax.set_yticks([])
axs[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.15), ncol=3)
fig.suptitle("決め方で、採用の中身はどう変わるか（2,000本ずつ）", x=0.01, ha="left", fontsize=13)
fig.subplots_adjust(top=0.78, wspace=0.25, left=0.02, right=0.99)
save(fig, "a271_rules.png", y=-0.08)
