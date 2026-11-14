"""726 クリック率をクリック単位で数えて検定すると、ユーザー単位で割り付けた A/B テストで、効果が0でも何%で「差あり」になるのか

架空の A/B テスト。ユーザーを A・B に半分ずつ（各2,000人）割り付ける。
  1人あたりの表示回数：平均 m 回（1＋ポアソン、人によって違う）
  1人ごとのクリックのしやすさ：ベータ分布（平均5%、人による違いあり）
  クリック数：表示回数とクリックのしやすさから二項分布
A と B は同じ作り方（効果0）。クリック率＝クリック合計÷表示合計。
検定の3通り（両側5%）：
  表示単位の割合の検定：表示1回1回を別々のものとして2つの割合の z 検定
  デルタ法：ユーザー単位の（クリック, 表示）の組から、比の分散を出して z 検定
  ユーザーごとのクリック率の平均を t 検定（比べるものが少し違う）
1人あたりの表示 m＝1・3・10・30回で各2,000回くり返し、「差あり」の割合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の A/B テストの表示とクリック（作成者が乱数で作成、seed 726）"
rng = np.random.default_rng(726)
NU, P0, KAPPA = 2000, 0.05, 20.0           # ベータ分布の a+b（小さいほど人による違いが大きい）


def arm(m, lift=0.0):
    imp = 1 + rng.poisson(m - 1, NU) if m > 1 else np.ones(NU, int)
    p = rng.beta(P0 * KAPPA, (1 - P0) * KAPPA, NU) * (1 + lift)
    clk = rng.binomial(imp, np.clip(p, 0, 1))
    return clk, imp


def tests(a, b):
    (ca, ia), (cb, ib) = a, b
    ra, rb = ca.sum() / ia.sum(), cb.sum() / ib.sum()
    pp = (ca.sum() + cb.sum()) / (ia.sum() + ib.sum())
    z_naive = (rb - ra) / np.sqrt(pp * (1 - pp) * (1 / ia.sum() + 1 / ib.sum()))
    def dvar(c, i):
        n = len(c); mc, mi = c.mean(), i.mean(); r = mc / mi
        vc, vi, cv = c.var(ddof=1), i.var(ddof=1), np.cov(c, i, ddof=1)[0, 1]
        return (vc - 2 * r * cv + r * r * vi) / (mi * mi) / n
    z_delta = (rb - ra) / np.sqrt(dvar(ca, ia) + dvar(cb, ib))
    t_user = stats.ttest_ind(cb / ib, ca / ia).pvalue
    return z_naive, z_delta, t_user, dvar(ca, ia) / (pp * (1 - pp) / ia.sum())


MS, REPS = [1, 3, 10, 30], 2000
rows = []; zs = {}
for m in MS:
    zn, zd = [], []
    for r in range(REPS):
        a1, a2, pu, vr = tests(arm(m), arm(m))
        rows.append({"m": m, "naive": abs(a1) > 1.96, "delta": abs(a2) > 1.96, "user_mean": pu < 0.05, "var_ratio": vr})
        zn.append(a1); zd.append(a2)
    zs[m] = (np.array(zn), np.array(zd))
R = pd.DataFrame(rows)
S = R.groupby("m").agg(naive=("naive", "mean"), delta=("delta", "mean"), user_mean=("user_mean", "mean"), var_ratio=("var_ratio", "mean")).reset_index()
S[["naive", "delta", "user_mean"]] *= 100
S.round(3).to_csv(RES / "summary.csv", index=False)

# 効果あり（B のクリックのしやすさ +10%）のときの「差あり」（m＝10）
pw = []
for r in range(1000):
    a1, a2, pu, _ = tests(arm(10), arm(10, 0.10)); pw.append((abs(a1) > 1.96, abs(a2) > 1.96, pu < 0.05))
pw = np.array(pw).mean(0) * 100

out = {"users_per_arm": NU, "ctr": P0, "beta_kappa": KAPPA, "reps": REPS,
       "false_positive_pct": {str(int(r.m)): {"naive": round(r.naive, 1), "delta": round(r.delta, 1), "user_mean": round(r.user_mean, 1)} for r in S.itertuples()},
       "variance_ratio_delta_over_naive": {str(int(r.m)): round(r.var_ratio, 2) for r in S.itertuples()},
       "power_lift10_m10_pct": {"naive": round(float(pw[0]), 1), "delta": round(float(pw[1]), 1), "user_mean": round(float(pw[2]), 1)}, "power_reps": 1000}
json.dump(out, open(RES / "a726_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：効果0での「差あり」の割合
fig, ax = plt.subplots(figsize=(8, 3.8)); x = np.arange(len(MS)); wd = 0.27
for dx, c, col, lab in [(-wd, "naive", ORANGE, "表示単位の割合の検定"), (0, "delta", BLUE, "デルタ法（ユーザー単位）"), (wd, "user_mean", GRAY, "ユーザーごとの率の平均（t 検定）")]:
    ax.bar(x + dx, S[c], wd, color=col, label=lab)
    for i, v in enumerate(S[c]): ax.text(x[i] + dx, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
ax.axhline(5, color=INK, ls="--", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{m}回" for m in MS]); ax.set_xlabel("1人あたりの表示回数（平均）")
ax.set_ylabel("効果0で「差あり」の割合（%）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title(f"表示が多い人ほど、表示単位の検定は「差あり」を出しすぎる（各{REPS:,}回）")
save(fig, "a726_false_positive.png", SRC)

# 図2：分散の比
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot([str(m) for m in MS], S.var_ratio, marker="o", color=BLUE)
for i, v in enumerate(S.var_ratio): ax.text(i, v + 0.2, f"{v:.2f}倍", ha="center", fontsize=9)
ax.axhline(1, color=GRAY, ls="--", lw=0.8)
ax.set_xlabel("1人あたりの表示回数（平均）"); ax.set_ylabel("本当のばらつき÷表示単位の見積もり")
ax.set_title("表示単位の式は、クリック率のばらつきを小さく見積もる")
save(fig, "a726_variance_ratio.png", SRC)

# 図3：z の分布（m＝30）
fig, ax = plt.subplots(figsize=(8, 3.6)); zn, zd = zs[30]; bins = np.linspace(-6, 6, 49)
ax.hist(zn, bins=bins, color=ORANGE, alpha=0.6, density=True, label="表示単位の z")
ax.hist(zd, bins=bins, color=BLUE, alpha=0.6, density=True, label="デルタ法の z")
xx = np.linspace(-6, 6, 300); ax.plot(xx, stats.norm.pdf(xx), color=INK, lw=1, label="標準正規分布（本来の形）")
ax.axvline(-1.96, color=GRAY, ls=":"); ax.axvline(1.96, color=GRAY, ls=":")
ax.set_xlabel("検定の z（効果0、1人あたり30回）"); ax.set_ylabel("密度"); ax.legend(frameon=False, fontsize=8.5)
ax.set_title("表示単位の z は広がりすぎ、±1.96 を超えやすい")
save(fig, "a726_z_dist.png", SRC)
print(json.dumps(out, ensure_ascii=False))
