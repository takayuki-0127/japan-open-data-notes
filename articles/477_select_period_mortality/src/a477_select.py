"""477 加入のときの審査の効き目を考えずに死亡率を見積もると、どれだけずれるのか（架空の契約、seed 477）"""
import json
import numpy as np, pandas as pd
from common import *

SEED = 477
SRC = "架空の契約（作成者が乱数で作成、seed 477）。もとの死亡率は厚生労働省「令和6年簡易生命表」（男）"
qx = pd.read_csv(DATA / "standard_qx_2024_male.csv").set_index("age").qx      # 30〜89歳
SEL = np.array([0.50, 0.65, 0.78, 0.88, 0.95])     # 加入からの年数0〜4年の死亡率の倍率（架空）。5年目からは1.0
TMAX = 30
ISSUE = np.arange(30, 60)                            # 加入年齢30〜59歳（同じ人数ずつ）
PERSIST = 0.94                                       # 1年ごとに契約が続く割合（架空）
f = np.ones(TMAX); f[:5] = SEL


def exposure(growth=0.0, runoff=0):
    """加入年齢×加入からの年数ごとの契約の数（割合）。growth＝新しい契約の年ごとの増え方、runoff＝新しい契約を止めてからの年数"""
    t = np.arange(TMAX)
    w = PERSIST ** t / (1 + growth) ** t
    if runoff: w = np.where(t >= runoff, w, 0.0)
    E = np.tile(w, (len(ISSUE), 1))
    return E / E.sum()


AGE = ISSUE[:, None] + np.arange(TMAX)[None, :]
Q_ULT = qx.reindex(AGE.ravel()).values.reshape(AGE.shape)   # 審査の効き目が消えたあとの死亡率
Q_TRUE = Q_ULT * f[None, :]
DUR = np.tile(np.arange(TMAX), (len(ISSUE), 1))
GROUPS = {"分けない": [range(0, TMAX)],
          "2つに分ける（5年未満／5年以上）": [range(0, 5), range(5, TMAX)],
          "3つに分ける（2年未満／2〜4年／5年以上）": [range(0, 2), range(2, 5), range(5, TMAX)],
          "1年ごとに分ける（0〜4年と5年以上）": [range(0, 1), range(1, 2), range(2, 3), range(3, 4), range(4, 5), range(5, TMAX)]}
PORT = {"新しい契約が年20%ずつ増えている": dict(growth=0.20), "新しい契約が年5%ずつ増えている": dict(growth=0.05), "新しい契約の数が一定": dict(growth=0.0),
        "新しい契約が年10%ずつ減っている": dict(growth=-0.10), "新しい契約を止めて5年": dict(runoff=5), "新しい契約を止めて10年": dict(runoff=10)}
BASE = "新しい契約の数が一定"


def ratios(E, deaths, groups):
    """経過年数の組ごとに、実際の死亡数÷（審査の効き目なしの表での見込み）を出す"""
    r = np.ones(TMAX)
    for g in groups:
        m = np.isin(DUR, list(g)); exp = (E * Q_ULT)[m].sum()
        r[list(g)] = deaths[m].sum() / exp if exp > 0 else 1.0
    return r


# ---- 1. 揺れなし：見積もった集団と当てはめる集団の、新しい契約の割合が違うとき ----
E0 = exposure(**PORT[BASE])
rows, shares = [], []
for name, kw in PORT.items():
    E = exposure(**kw); true = (E * Q_TRUE).sum()
    shares.append(dict(集団=name, 加入5年未満の割合=round(E[:, :5].sum() * 100, 1), 加入2年未満の割合=round(E[:, :2].sum() * 100, 1),
                       実際の死亡数と効き目なしの表の比=round(true / (E * Q_ULT).sum() * 100, 1), 平均年齢=round((E * AGE).sum(), 1)))
    for gname, groups in GROUPS.items():
        r = ratios(E0, E0 * Q_TRUE, groups)                    # 揺れなしの見積もり（一定の集団から）
        pred = (E * Q_ULT * r[None, :]).sum()
        rows.append(dict(当てはめる集団=name, 分け方=gname, 見込みと実際のずれ=round((pred / true - 1) * 100, 2)))
bias = pd.DataFrame(rows); bias.to_csv(RES / "bias_by_portfolio.csv", index=False)
shares = pd.DataFrame(shares); shares.to_csv(RES / "portfolio_shares.csv", index=False)

# ---- 1b. 見積もる集団と当てはめる集団の組み合わせ（分けない見積もり）----
rows = []
for sname, skw in PORT.items():
    Es = exposure(**skw); r = (Es * Q_TRUE).sum() / (Es * Q_ULT).sum()
    for tname, tkw in PORT.items():
        Et = exposure(**tkw)
        rows.append(dict(見積もった集団=sname, 当てはめる集団=tname, 分けない見込みのずれ=round(((Et * Q_ULT).sum() * r / (Et * Q_TRUE).sum() - 1) * 100, 1)))
cross = pd.DataFrame(rows); cross.to_csv(RES / "bias_cross_table.csv", index=False)

# ---- 2. 新しい契約を止めたあと、年ごとのずれ（分けない見積もり）----
rows = []
r_all = ratios(E0, E0 * Q_TRUE, GROUPS["分けない"])
for y in range(0, 16):
    E = exposure(runoff=y) if y else E0
    true = (E * Q_TRUE).sum(); pred = (E * Q_ULT * r_all[None, :]).sum()
    rows.append(dict(止めてからの年数=y, 加入5年未満の割合=round(E[:, :5].sum() * 100, 1), 分けない見込みのずれ=round((pred / true - 1) * 100, 2)))
runoff = pd.DataFrame(rows); runoff.to_csv(RES / "runoff_by_year.csv", index=False)

# ---- 3. 揺れあり：延べ人数ごとに、どの分け方が近いか ----
rng = np.random.default_rng(SEED)
REP = 2000
rows = []
targets = ["新しい契約が年20%ずつ増えている", "新しい契約の数が一定", "新しい契約を止めて5年"]
for n in [2_000, 10_000, 50_000, 200_000, 1_000_000, 5_000_000]:
    lam = n * E0 * Q_TRUE
    D = rng.poisson(lam, size=(REP,) + lam.shape)
    for gname, groups in GROUPS.items():
        R = np.array([ratios(n * E0, D[i], groups) for i in range(REP)])           # REP×TMAX
        for tname in targets:
            E = exposure(**PORT[tname]); true = (E * Q_TRUE).sum()
            pred = (E * Q_ULT)[None, :, :] * R[:, None, :]
            err = (pred.sum(axis=(1, 2)) / true - 1) * 100
            rows.append(dict(延べ人数=n, 一年の死亡数の見込み=round(lam.sum(), 1), 分け方=gname, 当てはめる集団=tname,
                             ずれの平均=round(err.mean(), 2), ずれの標準偏差=round(err.std(), 2), RMSE=round(np.sqrt((err ** 2).mean()), 2)))
    if n == 50_000:
        ex = pd.DataFrame({"加入からの年数": np.arange(TMAX), "延べ人数": (n * E0).sum(axis=0).round(1), "死亡数": D[0].sum(axis=0),
                           "効き目なしの表での見込み": (n * E0 * Q_ULT).sum(axis=0).round(2), "本当の倍率": f})
        ex.to_csv(DATA / "example_portfolio_50000.csv", index=False)
noise = pd.DataFrame(rows); noise.to_csv(RES / "rmse_by_size.csv", index=False)

# ---- 4. 審査の効き目の強さを変える ----
rows = []
for nm, sel in [("弱い（1年目0.8倍）", [0.80, 0.88, 0.94, 0.97, 0.99]), ("中くらい（1年目0.5倍）", list(SEL)), ("強い（1年目0.3倍）", [0.30, 0.50, 0.70, 0.85, 0.95]),
                ("長く続く（10年かけて戻る）", list(np.linspace(0.5, 0.95, 10)))]:
    ff = np.ones(TMAX); ff[:len(sel)] = sel; QT = Q_ULT * ff[None, :]
    r0 = (E0 * QT).sum() / (E0 * Q_ULT).sum()
    for name in ["新しい契約が年20%ずつ増えている", "新しい契約が年10%ずつ減っている", "新しい契約を止めて5年", "新しい契約を止めて10年"]:
        E = exposure(**PORT[name]); true = (E * QT).sum(); pred = (E * Q_ULT).sum() * r0
        rows.append(dict(効き目=nm, 当てはめる集団=name, 分けない見込みのずれ=round((pred / true - 1) * 100, 2)))
strength = pd.DataFrame(rows); strength.to_csv(RES / "bias_by_select_strength.csv", index=False)

# ---- 図 ----
fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.2), gridspec_kw=dict(width_ratios=[1, 1.25]))
axs[0].bar(np.arange(8), f[:8], color=[ORANGE] * 5 + [GRAY] * 3)
for i, v in enumerate(f[:8]): axs[0].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
axs[0].set_xticks(np.arange(8)); axs[0].set_xticklabels(["1年目", "2", "3", "4", "5", "6", "7", "8年目"]); axs[0].set_ylim(0, 1.15)
axs[0].set_ylabel("死亡率の倍率（審査なしの水準＝1）"); axs[0].set_title("置いた「審査の効き目」", loc="left")
s = shares.set_index("集団").加入5年未満の割合
axs[1].barh(np.arange(len(s))[::-1], s.values, color=BLUE)
for y, v in zip(np.arange(len(s))[::-1], s.values): axs[1].text(v + 1, y, f"{v:.0f}%", va="center", fontsize=9)
axs[1].set_yticks(np.arange(len(s))[::-1]); axs[1].set_yticklabels([x.replace("新しい契約", "新契約") for x in s.index], fontsize=9); axs[1].set_xlim(0, 75)
axs[1].set_xlabel("加入から5年未満の契約の割合（%）"); axs[1].set_title("集団ごとの、新しい契約の割合", loc="left")
fig.tight_layout(); save(fig, "a477_setup.png", f"出典：{SRC}。倍率と契約の続く割合は説明用に置いた値")

fig, ax = plt.subplots(figsize=(8, 4.6))
names = [n for n in PORT if n != BASE]; w = 0.2
for j, (gname, c) in enumerate(zip(GROUPS, [ORANGE, LIGHT, BLUE, "#14427a"])):
    v = [float(bias[(bias.当てはめる集団 == n) & (bias.分け方 == gname)].見込みと実際のずれ.iloc[0]) for n in names]
    ax.bar(np.arange(len(names)) + (j - 1.5) * w, v, w, color=c, label=gname)
    if j == 0:
        for i, x in enumerate(v): ax.text(i - 1.5 * w, x + (0.4 if x >= 0 else -1.3), f"{x:+.1f}", ha="center", fontsize=8.5)
ax.axhline(0, color=INK, lw=0.8); ax.set_ylim(-5, 17); ax.set_xticks(np.arange(len(names))); ax.set_xticklabels([n.replace("新しい契約", "新契約").replace("ずつ", "\nずつ").replace("を止めて", "を\n止めて") for n in names], fontsize=9)
ax.set_ylabel("見込みの死亡数のずれ（%、プラス＝多く見込みすぎ）"); ax.set_title("新しい契約の割合が違う集団に当てはめると、分けない見積もりはずれる", loc="left"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a477_bias.png", f"出典：{SRC}。見積もりは「新しい契約の数が一定」の集団から。揺れなしの計算")

fig, axs = plt.subplots(1, 2, figsize=(9.4, 4.3), sharey=True)
for ax, tname in zip(axs, ["新しい契約が年20%ずつ増えている", "新しい契約を止めて5年"]):
    for gname, c in zip(GROUPS, [ORANGE, LIGHT, BLUE, "#14427a"]):
        s = noise[(noise.当てはめる集団 == tname) & (noise.分け方 == gname)]
        ax.plot(s.延べ人数, s.RMSE, marker="o", ms=4, lw=2, color=c, label=gname)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks([2e3, 1e4, 5e4, 2e5, 1e6, 5e6]); ax.set_xticklabels(["2千", "1万", "5万", "20万", "100万", "500万"])
    ax.set_yticks([1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50"]); ax.set_xlabel("見積もりに使う延べ人数（人年）"); ax.set_title("当てはめ先：" + tname.replace("新しい契約", "新契約"), loc="left", fontsize=11)
axs[0].set_ylabel("見込みの死亡数のずれ（RMSE、%）"); axs[0].legend(fontsize=8, frameon=False)
fig.tight_layout(); save(fig, "a477_rmse_by_size.png", f"出典：{SRC}。延べ人数ごとに2,000回。死亡数はポアソン分布")

main = dict(seed=SEED, 倍率=list(map(float, SEL)), 契約の続く割合=PERSIST,
            一定の集団の比=float(shares.set_index("集団").loc[BASE, "実際の死亡数と効き目なしの表の比"]),
            分けない見込みのずれ={n: float(bias[(bias.当てはめる集団 == n) & (bias.分け方 == "分けない")].見込みと実際のずれ.iloc[0]) for n in PORT})
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(cross.pivot(index="見積もった集団", columns="当てはめる集団", values="分けない見込みのずれ").to_string()); print(shares.to_string()); print(bias.pivot(index="当てはめる集団", columns="分け方", values="見込みと実際のずれ").to_string()); print(runoff.to_string())
print(noise.pivot_table(index=["当てはめる集団", "延べ人数"], columns="分け方", values="RMSE").to_string()); print(noise[noise.当てはめる集団 == BASE][["延べ人数", "一年の死亡数の見込み"]].drop_duplicates().to_string()); print(strength.to_string())
