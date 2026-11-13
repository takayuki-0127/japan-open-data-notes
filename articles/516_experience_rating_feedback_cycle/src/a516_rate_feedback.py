"""516 実績の損害率に合わせて毎年保険料を直すと、損害率は落ち着くのか、それとも波打つのか（保険数理・リスク）

架空の保険。1契約あたりの本当の損害の見込み c_t は毎年 g（平均2%）で伸び、少し揺れる（ランダムウォーク）。
実際の損害 L_t = c_t・exp(ε_t)（年ごとの偶然の揺れ）。損害率 LR_t = L_t / P_t。
毎年の保険料の直し方：
  P_{t+1} = P_t × (直近 k 年の実績の損害率の平均 / 目標)^z
  ただし実績が分かるのは d 年遅れ（t 年の保険料を決めるとき、使えるのは t−d 年までの実績）。
  z は直す強さ（1 なら実績どおり全部直す）。
  1年に動かせる幅は ±30% までと置く（これがないと強く直す設定では数字が無限に大きくなる）。
目標の損害率は 65%。200年×1,000回のシミュレーション（最初の50年は捨てる）。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 516
SRC = "架空の保険の損害率（作成者が乱数で作成、seed 516）"
TARGET, G, SD_TREND, SD_NOISE = 0.65, 0.02, 0.02, 0.06
YEARS, BURN, RUNS = 200, 50, 1000
CAP = 1.3


def run(k, d, z, rng, years=YEARS, runs=RUNS, trend_adj=False, return_path=False):
    eta = rng.normal(G, SD_TREND, (runs, years))
    c = np.exp(np.cumsum(eta, axis=1))
    L = c * np.exp(rng.normal(-SD_NOISE**2 / 2, SD_NOISE, (runs, years)))
    capped = np.zeros((runs, years), bool); P = np.zeros((runs, years)); LR = np.zeros((runs, years))
    P[:, : k + d] = c[:, : k + d] / TARGET          # 最初は正しい保険料から始める
    for t in range(years):
        if t >= k + d:
            ex = LR[:, t - d - k + 1: t - d + 1].mean(axis=1)
            adj = (ex / TARGET) ** z
            if trend_adj:                            # 遅れの分の伸びを足す
                adj = adj * np.exp(G * (d + (k - 1) / 2) * z)
            capped[:, t] = (adj < 1 / CAP) | (adj > CAP)
            P[:, t] = P[:, t - 1] * np.clip(adj, 1 / CAP, CAP)
        LR[:, t] = L[:, t] / P[:, t]
    x = LR[:, BURN:]
    out = dict(k=k, d=d, z=z, trend_adj=trend_adj, mean_lr=float(x.mean()), sd_lr=float(x.std(axis=1).mean()),
               mean_gap_pt=float((x.mean() - TARGET) * 100), ac1=float(np.mean([np.corrcoef(r[:-1], r[1:])[0, 1] for r in x[:200]])),
               period=period(x[:200]), capped=float(capped[:, BURN:].mean()))
    return (out, LR) if return_path else out


def period(x):
    """平均を引いた系列のスペクトルのいちばん高い山から、波の周期（年）を出す"""
    xs = x - x.mean(axis=1, keepdims=True)
    sp = (np.abs(np.fft.rfft(xs, axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(xs.shape[1]); i = 1 + np.argmax(sp[1:])
    return float(1 / f[i])


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for d in [1, 2, 3]:
        for k in [1, 3, 5]:
            for z in [0.25, 0.5, 0.75, 1.0, 1.25]:
                rows.append(run(k, d, z, rng))
    df = pd.DataFrame(rows)
    # 遅れの分の伸びを足す直し方
    adj = pd.DataFrame([run(k, 2, z, rng, trend_adj=True) for k in [1, 3] for z in [0.5, 1.0]])
    df.round(4).to_csv(RES / "sweep.csv", index=False); adj.round(4).to_csv(RES / "trend_adjusted.csv", index=False)
    b = lambda k, d, z: df[(df.k == k) & (df.d == d) & (df.z == z)].iloc[0]
    key = {f"k{k}_d{d}_z{z}": {c: round(float(b(k, d, z)[c]), 4) for c in ["mean_gap_pt", "sd_lr", "ac1", "period", "capped"]}
           for k, d, z in [(1, 1, 1.0), (1, 2, 1.0), (1, 2, 0.5), (3, 2, 0.5), (3, 2, 1.0), (5, 2, 1.0), (1, 3, 1.0), (1, 3, 1.25), (3, 2, 0.25)]}
    out = dict(seed=SEED, target=TARGET, trend=G, sd_trend=SD_TREND, sd_noise=SD_NOISE, years=YEARS, burn=BURN, runs=RUNS,
               cap=CAP, irreducible_sd_lr=round(TARGET * SD_NOISE, 4), key=key,
               trend_adjusted=adj[["k", "z", "mean_gap_pt", "sd_lr", "period"]].round(4).to_dict("records"))
    json.dump(out, open(RES / "a516_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(key, ensure_ascii=False, indent=0)); print(adj[["k", "z", "mean_gap_pt", "sd_lr", "period"]].round(3))

    # 図1：1本の道のり（d=2）
    r1 = np.random.default_rng(SEED + 1)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for (k, z, col, lab) in [(1, 1.0, ORANGE, "直近1年の実績で全部直す（z=1）"), (3, 0.5, BLUE, "直近3年の平均で半分だけ直す（z=0.5）")]:
        r1 = np.random.default_rng(SEED + 1)
        _, LR = run(k, 2, z, r1, runs=1, return_path=True)
        ax.plot(np.arange(60), LR[0, BURN:BURN + 60] * 100, color=col, lw=2, label=lab)
    ax.axhline(TARGET * 100, color=GRAY, ls="--", lw=1); ax.set_xlabel("年"); ax.set_ylabel("損害率（%）")
    ax.set_title("同じ損害でも、直し方しだいで損害率が波打つ（実績が分かるのは2年遅れ）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a516_path.png", SRC + "。同じ乱数の損害で直し方だけを変えた60年分")

    # 図2：直す強さと損害率の振れ（d=1,2,3、k=1）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for d, col in [(1, LIGHT), (2, BLUE), (3, INK)]:
        x = df[(df.k == 1) & (df.d == d)]
        ax.plot(x.z, x.sd_lr * 100, "o-", color=col, lw=2, label=f"実績が分かるのは{d}年遅れ")
    ax.axhline(TARGET * SD_NOISE * 100, color=GRAY, ls="--", lw=1)
    ax.text(0.26, TARGET * SD_NOISE * 100 + 0.3, "保険料が毎年ぴったりでも残る振れ", color=GRAY, fontsize=9)
    ax.set_xlabel("直す強さ z（1＝実績どおり全部直す）"); ax.set_ylabel("損害率の標準偏差（ポイント）")
    ax.set_title("遅れが長いほど、強く直すと損害率の振れが大きくなる（直近1年の実績で直す）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a516_strength_sd.png", SRC + "。各1,000回×150年の平均")

    # 図3：目標からの平均のずれ（伸びを足すかどうか）
    x = df[(df.d == 2) & (df.z.isin([0.5, 1.0]))]
    labs, v1, v2 = [], [], []
    for k in [1, 3]:
        for z in [0.5, 1.0]:
            labs.append(f"直近{k}年・z={z}")
            v1.append(float(df[(df.k == k) & (df.d == 2) & (df.z == z)].mean_gap_pt.iloc[0]))
            v2.append(float(adj[(adj.k == k) & (adj.z == z)].mean_gap_pt.iloc[0]))
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); xs = np.arange(len(labs)); w = 0.38
    ax.bar(xs - w / 2, v1, w, color=ORANGE, label="実績の損害率だけで直す")
    ax.bar(xs + w / 2, v2, w, color=BLUE, label="遅れの間の伸び（年2%）も足して直す")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs, labs); ax.set_ylabel("目標65%からの平均のずれ（ポイント）")
    ax.set_title("損害が伸び続けると、実績だけで直す方法は目標を上回り続ける（2年遅れ）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a516_mean_gap.png", SRC + "。損害の見込みは年平均2%で伸びると置いた")


if __name__ == "__main__":
    main()
