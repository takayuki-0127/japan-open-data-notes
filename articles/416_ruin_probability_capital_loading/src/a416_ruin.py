"""416 手元の資本と保険料の上乗せで、10年のうちに資本が尽きる確率はどう変わるか（架空の保険会社）
事故の件数：ポアソン（年100件）。損害額：平均1の4通り。保険料：年 (1+θ)×100 を連続に受け取る。
資本が尽きる＝事故の支払いの直後に、手元の資本がマイナスになる。"""
import json
import numpy as np, pandas as pd
from scipy import stats, optimize
from common import *

SEED, LAM, YEARS, M = 416, 100.0, 10.0, 1200          # M：1本の道で作る事故の数（10年分より多く）
NPATH, CHUNK = 200_000, 5_000
THETAS = [0.05, 0.10, 0.20]
US = [5, 10, 20, 30, 50, 75, 100]                      # 手元の資本（1年の損害の見込み100に対して 5〜100）
HORIZ = [1, 5, 10]

def sev(name, rng, size):
    if name == "指数（CV1）": return rng.exponential(1.0, size)
    if name == "ガンマ（CV2）": return rng.gamma(0.25, 4.0, size)
    if name == "対数正規（CV2）":
        s2 = np.log(5.0); return rng.lognormal(-s2 / 2, np.sqrt(s2), size)
    if name == "パレート（CV2）":
        a = 8 / 3; return (rng.pareto(a, size)) * (a - 1)     # ロマックス型。平均1
DISTS = ["指数（CV1）", "ガンマ（CV2）", "対数正規（CV2）", "パレート（CV2）"]
EX2 = {"指数（CV1）": 2.0, "ガンマ（CV2）": 5.0, "対数正規（CV2）": 5.0, "パレート（CV2）": 5.0}

def lundberg_R(name, th):
    """調整係数 R： λ(M_X(r)-1) = c r の正の解。損害額の積率母関数がある分布だけ"""
    if name == "指数（CV1）": return th / (1 + th)
    if name == "ガンマ（CV2）":                             # M(r) = (1-4r)^(-0.25), r<0.25
        f = lambda r: (1 - 4 * r) ** (-0.25) - 1 - (1 + th) * r
        return optimize.brentq(f, 1e-9, 0.25 - 1e-9)
    return np.nan

def diffusion(u, th, ex2, t):
    """ブラウン運動で置きかえた近似（平均と分散だけを使う）"""
    mu, s = th * LAM, np.sqrt(LAM * ex2)
    return stats.norm.cdf(-(u + mu * t) / (s * np.sqrt(t))) + np.exp(-2 * mu * u / s ** 2) * stats.norm.cdf(-(u - mu * t) / (s * np.sqrt(t)))

rows, need, when = [], [], []
for di, name in enumerate(DISTS):
    for ti, th in enumerate(THETAS):
        rng = np.random.default_rng([SEED, di, ti])
        c = (1 + th) * LAM
        D = {h: [] for h in HORIZ}                          # 各期間での「いちばん深い落ちこみ」
        for _ in range(NPATH // CHUNK):
            T = np.cumsum(rng.exponential(1 / LAM, (CHUNK, M)), axis=1)
            assert T[:, -1].min() > YEARS
            Sx = np.cumsum(sev(name, rng, (CHUNK, M)), axis=1)
            dip = Sx - c * T                                 # 支払いの累計 − 保険料の累計
            for h in HORIZ:
                D[h].append(np.where(T <= h, dip, -np.inf).max(axis=1))
        D = {h: np.concatenate(v) for h, v in D.items()}
        R = lundberg_R(name, th)
        for u in US:
            p10 = (D[10] > u).mean()
            rows.append(dict(分布=name, 上乗せ=th, 資本=u, 尽きた割合_1年=(D[1] > u).mean(), 尽きた割合_5年=(D[5] > u).mean(),
                             尽きた割合_10年=p10, 標準誤差_10年=np.sqrt(p10 * (1 - p10) / NPATH),
                             近似_拡散_10年=diffusion(u, th, EX2[name], 10.0),
                             ルンドベリの上限_無限=np.exp(-R * u) if R == R else np.nan,
                             厳密_指数_無限=np.exp(-th * u / (1 + th)) / (1 + th) if name == "指数（CV1）" else np.nan))
        for q in (0.95, 0.99, 0.995):
            need.append(dict(分布=name, 上乗せ=th, 尽きる割合の上限=round(1 - q, 3), 要る資本=np.quantile(D[10], q)))
        when.append(dict(分布=name, 上乗せ=th, 資本=20, **{f"{h}年までに尽きた割合": (D[h] > 20).mean() for h in HORIZ}))
        print(name, th, "done", flush=True)

T1 = pd.DataFrame(rows); T1["近似÷実際"] = T1["近似_拡散_10年"] / T1["尽きた割合_10年"].replace(0, np.nan)
T1["上限÷実際"] = T1["ルンドベリの上限_無限"] / T1["尽きた割合_10年"].replace(0, np.nan)
T1.to_csv(RES / "ruin_table.csv", index=False)
N1 = pd.DataFrame(need); N1.to_csv(RES / "capital_needed.csv", index=False)
W1 = pd.DataFrame(when); W1.to_csv(RES / "ruin_by_horizon.csv", index=False)

# 例：1本の道（指数・上乗せ10%・資本20）
rng = np.random.default_rng([SEED, 99])
ex = []
for k in range(40):
    T = np.cumsum(rng.exponential(1 / LAM, M)); X = rng.exponential(1.0, M); m = T <= 10
    ex.append(pd.DataFrame(dict(道=k, 年=T[m], 資本=20 + 110 * T[m] - np.cumsum(X)[m])))
EX = pd.concat(ex); EX.iloc[::5].round(3).to_csv(DATA / "example_paths_exp_theta10_u20.csv", index=False)

g = lambda n, th, u, col: float(T1[(T1.分布 == n) & (T1.上乗せ == th) & (T1.資本 == u)][col].iloc[0])
main = dict(
    条件=dict(年の事故件数=LAM, 損害額の平均=1, 期間_年=YEARS, 道の数=NPATH, 乱数の種=SEED),
    指数_資本20=dict(上乗せ5=g(DISTS[0], .05, 20, "尽きた割合_10年"), 上乗せ10=g(DISTS[0], .10, 20, "尽きた割合_10年"), 上乗せ20=g(DISTS[0], .20, 20, "尽きた割合_10年")),
    上乗せ10_資本50=dict(**{n: g(n, .10, 50, "尽きた割合_10年") for n in DISTS}, 拡散の近似_CV2=g(DISTS[1], .10, 50, "近似_拡散_10年"), 拡散の近似_CV1=g(DISTS[0], .10, 50, "近似_拡散_10年")),
    上乗せ10_資本100=dict(**{n: g(n, .10, 100, "尽きた割合_10年") for n in DISTS}, 拡散の近似_CV2=g(DISTS[1], .10, 100, "近似_拡散_10年")),
    要る資本_1パーセント=N1[N1.尽きる割合の上限 == 0.01].pivot(index="分布", columns="上乗せ", values="要る資本").round(1).to_dict(),
    近似と実際の比_範囲={n: [float(T1[(T1.分布 == n) & (T1.尽きた割合_10年 > 0.002)]["近似÷実際"].min()), float(T1[(T1.分布 == n) & (T1.尽きた割合_10年 > 0.002)]["近似÷実際"].max())] for n in DISTS},
    上限と実際の比_範囲={n: [float(T1[(T1.分布 == n) & (T1.尽きた割合_10年 > 0.002)]["上限÷実際"].min()), float(T1[(T1.分布 == n) & (T1.尽きた割合_10年 > 0.002)]["上限÷実際"].max())] for n in DISTS[:2]},
)
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# 図1：指数の場合。資本と上乗せで、10年のうちに尽きる割合
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
for th, col in zip(THETAS, [ORANGE, BLUE, GREEN]):
    d = T1[(T1.分布 == DISTS[0]) & (T1.上乗せ == th) & (T1.尽きた割合_10年 > 0)]
    ax[0].plot(d.資本, d.尽きた割合_10年 * 100, "o-", color=col, label=f"上乗せ{int(th*100)}%（試した結果）")
    ax[0].plot(d.資本, d.近似_拡散_10年 * 100, "--", color=col, lw=1, label="　近似の式（10年）")
ax[0].set_yscale("log"); ax[0].set_ylim(0.005, 100); ax[0].set_xlabel("はじめの資本（1年の損害の見込み＝100）"); ax[0].set_ylabel("10年のうちに資本が尽きた割合（%、対数）")
ax[0].set_title("損害額が指数分布のとき"); ax[0].legend(fontsize=7.5, frameon=False)
for k in range(40):
    d = EX[EX.道 == k]; ax[1].plot(d.年, d.資本, color=ORANGE if d.資本.min() < 0 else LIGHT, lw=0.7, zorder=3 if d.資本.min() < 0 else 1)
ax[1].axhline(0, color=INK, lw=0.8); ax[1].set_xlabel("年"); ax[1].set_ylabel("手元の資本"); ax[1].set_title("40本の例（上乗せ10%・はじめの資本20）\nオレンジ＝途中で0を下回った道")
save(fig, "a416_ruin_by_capital_loading.png", "架空の保険会社（年100件・損害額の平均1）。20万本の道で数えた。作成者が計算")

# 図2：同じ平均・同じ散らばりでも、裾で違う（上乗せ10%）
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
cols = {DISTS[0]: GRAY, DISTS[1]: BLUE, DISTS[2]: GREEN, DISTS[3]: ORANGE}
for n in DISTS:
    d = T1[(T1.分布 == n) & (T1.上乗せ == 0.10)]
    ax[0].plot(d.資本, d.尽きた割合_10年 * 100, "o-", color=cols[n], label=n)
d = T1[(T1.分布 == DISTS[1]) & (T1.上乗せ == 0.10)]
ax[0].plot(d.資本, d.近似_拡散_10年 * 100, "k--", lw=1, label="近似の式（CV2 の3つに共通）")
ax[0].plot(d.資本, d.ルンドベリの上限_無限 * 100, "k:", lw=1, label="ルンドベリの上限（ガンマ）")
ax[0].set_yscale("log"); ax[0].set_ylim(0.05, 100); ax[0].set_xlabel("はじめの資本"); ax[0].set_ylabel("10年のうちに資本が尽きた割合（%、対数）")
ax[0].set_title("上乗せ10%：損害額の分布ごと"); ax[0].legend(fontsize=7.5, frameon=False)
P = N1[N1.尽きる割合の上限 == 0.01].pivot(index="分布", columns="上乗せ", values="要る資本").loc[DISTS]
x = np.arange(4); w = 0.26
for j, (th, col) in enumerate(zip(THETAS, [ORANGE, BLUE, GREEN])):
    b = ax[1].bar(x + (j - 1) * w, P[th], w, color=col, label=f"上乗せ{int(th*100)}%")
    for xi, v in zip(x + (j - 1) * w, P[th]): ax[1].text(xi, v + 2, f"{v:.0f}", ha="center", fontsize=8)
ax[1].set_xticks(x); ax[1].set_xticklabels([n.replace("（", "\n（") for n in DISTS], fontsize=9); ax[1].set_ylabel("要る資本（1年の損害の見込み＝100）")
ax[1].set_title("10年で尽きる割合を1%までにする資本"); ax[1].legend(fontsize=8, frameon=False)
save(fig, "a416_tail_and_capital_needed.png", "架空の保険会社（年100件・損害額の平均1）。CV2 の3つは平均と分散が同じ。作成者が計算")

# 図3：近似の式÷試した結果
fig, ax = plt.subplots(figsize=(8.5, 4.3))
for n in DISTS:
    d = T1[(T1.分布 == n) & (T1.上乗せ == 0.10) & (T1.尽きた割合_10年 > 0.0005)]
    ax.plot(d.資本, d["近似÷実際"], "o-", color=cols[n], label=n)
ax.axhline(1, color=INK, lw=0.8); ax.set_yscale("log"); ax.set_xlabel("はじめの資本"); ax.set_ylabel("近似の式 ÷ 試した結果（対数）")
ax.set_title("近似の式は、裾が重いほど、資本が大きいほど小さく出る（上乗せ10%）"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a416_approximation_ratio.png", "1より下＝近似の式が、尽きる割合を小さく見積もっている。作成者が計算")
print(json.dumps(main, ensure_ascii=False, indent=1))
