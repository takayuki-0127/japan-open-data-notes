"""468 一律に保険料を上げたとき、事故の少ない契約から先に抜けると、残った契約の損害率はどう動くか（架空の契約、seed 468）"""
import json
import numpy as np, pandas as pd
from common import *

SEED = 468
N = 200_000
SEV = 500_000              # 1事故の損害の平均（どの契約も同じ）
LR0 = 0.75                 # 値上げの前の損害率（見込み）
BASE_LAPSE = 0.10          # 値上げがない年に更新しない割合
SLOPE = 8.0                # 値上げ1（=100%）あたりの、抜けやすさ（ロジットの目盛り）の増え方
SRC = "架空の契約（作成者が乱数で作成、seed 468）"
logit = lambda p: np.log(p / (1 - p)); sig = lambda x: 1 / (1 + np.exp(-x))


def make(rng, cv=0.6):
    """契約ごとの本当の事故率。平均0.08、散らばり（変動係数）cv のガンマ分布"""
    k = 1 / cv ** 2
    lam = 0.08 * rng.gamma(k, 1 / k, N)
    z = (np.log(lam) - np.log(lam).mean()) / np.log(lam).std()      # 事故率の高さ（標準化）
    return lam, z


def lapse_prob(z, r, s):
    """値上げ r のときに更新しない確率。s は「事故の少ない契約ほど抜けやすい」強さ。値上げが0なら全員 BASE_LAPSE"""
    return sig(logit(BASE_LAPSE) + SLOPE * r - s * (r / 0.10) * z)


def after(lam, z, w, prem, r, s):
    """重み w（残っている確率）の集まりに値上げ r を当てたあとの、残る確率・損害率"""
    stay = w * (1 - lapse_prob(z, r, s))
    loss = (stay * lam * SEV).sum(); p = prem * (1 + r)
    return stay, loss / (stay.sum() * p), p


def one_year(lam, z):
    prem = lam.mean() * SEV / LR0; w = np.ones(N); rows = []
    for r in (0.05, 0.10, 0.20, 0.30):
        for s in (0.0, 0.25, 0.5, 1.0):
            stay, lr, _ = after(lam, z, w, prem, r, s)
            exp = LR0 / (1 + r)
            lam_stay = (stay * lam).sum() / stay.sum(); lam_gone = ((w - stay) * lam).sum() / (w - stay).sum()
            rows.append(dict(値上げ=int(r * 100), 抜け方の強さ=s, 残った割合=round(stay.sum() / N * 100, 1), 見込みの損害率=round(exp * 100, 1),
                             損害率=round(lr * 100, 1), 見込みとの差=round((lr - exp) * 100, 1),
                             下がらなかった分=round((lr - exp) / (LR0 - exp) * 100, 0),
                             残った契約の事故率=round(lam_stay * 100, 2), 抜けた契約の事故率=round(lam_gone * 100, 2),
                             保険料の合計の変化=round((stay.sum() * (1 + r) / N - 1) * 100, 1)))
    return pd.DataFrame(rows)


def spiral(lam, z, target=0.65, years=6):
    """毎年、損害率が目標を上回っていれば、目標に届くだけ値上げする（上限20%）"""
    rows = []
    for s in (0.0, 0.25, 0.5, 1.0):
        prem = lam.mean() * SEV / LR0; w = np.ones(N); lr = LR0
        rows.append(dict(抜け方の強さ=s, 年=0, 値上げ=0.0, 契約の数=100.0, 損害率=round(lr * 100, 1), 保険料の水準=100.0))
        p0 = prem
        for y in range(1, years + 1):
            r = float(np.clip(lr / target - 1, 0, 0.20))
            w, lr, prem = after(lam, z, w, prem, r, s)
            rows.append(dict(抜け方の強さ=s, 年=y, 値上げ=round(r * 100, 1), 契約の数=round(w.sum() / N * 100, 1), 損害率=round(lr * 100, 1), 保険料の水準=round(prem / p0 * 100, 1)))
    return pd.DataFrame(rows)


def by_cv(rng):
    rows = []
    for cv in (0.3, 0.6, 1.0):
        lam, z = make(rng, cv); prem = lam.mean() * SEV / LR0
        for s in (0.25, 0.5, 1.0):
            _, lr, _ = after(lam, z, np.ones(N), prem, 0.10, s)
            rows.append(dict(事故率の散らばり=cv, 抜け方の強さ=s, 損害率=round(lr * 100, 1), 見込みとの差=round((lr - LR0 / 1.1) * 100, 1)))
    return pd.DataFrame(rows)


def realized(lam, z, rng, n_pol, s, reps=400):
    """契約 n_pol 件で、実際に抜ける・事故が起きるを乱数で引いたときの損害率（+10%）"""
    out = []
    prem = lam.mean() * SEV / LR0 * 1.1
    for _ in range(reps):
        i = rng.choice(N, n_pol, replace=False)
        stay = rng.random(n_pol) > lapse_prob(z[i], 0.10, s)
        cnt = rng.poisson(lam[i][stay]).sum()
        loss = rng.gamma(cnt * 1.0, SEV) if cnt > 0 else 0.0      # 1事故の損害は平均50万円の指数分布
        out.append(loss / (stay.sum() * prem) * 100)
    return np.array(out)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    lam, z = make(rng)
    pd.DataFrame({"本当の事故率": np.round(lam[:200], 4), "事故率の高さ_標準化": np.round(z[:200], 3),
                  "抜ける確率_10%値上げ_強さ0.5": np.round(lapse_prob(z[:200], 0.10, 0.5), 3)}).to_csv(DATA / "example_policies.csv", index=False)
    one = one_year(lam, z); one.to_csv(RES / "one_year.csv", index=False)
    sp = spiral(lam, z); sp.to_csv(RES / "multi_year.csv", index=False)
    cvt = by_cv(np.random.default_rng(SEED + 1)); cvt.to_csv(RES / "by_spread.csv", index=False)
    rz = []
    for n in (2_000, 20_000):
        for s in (0.0, 0.5):
            x = realized(lam, z, rng, n, s); rz.append(dict(契約数=n, 抜け方の強さ=s, 損害率の平均=round(x.mean(), 1), 標準偏差=round(x.std(), 1)))
    rz = pd.DataFrame(rz); rz.to_csv(RES / "realized_noise.csv", index=False)
    # 抜ける確率（事故率の10分位別）
    q = pd.qcut(lam, 10, labels=False); dec = []
    for s in (0.0, 0.25, 0.5, 1.0):
        pr = lapse_prob(z, 0.10, s)
        for k in range(10): dec.append(dict(抜け方の強さ=s, 事故率の順位_10分位=k + 1, 事故率の平均=round(lam[q == k].mean() * 100, 2), 抜ける割合=round(pr[q == k].mean() * 100, 1)))
    dec = pd.DataFrame(dec); dec.to_csv(RES / "lapse_by_decile.csv", index=False)

    cols = {0.0: GRAY, 0.25: LIGHT, 0.5: BLUE, 1.0: ORANGE}
    lab = {0.0: "事故率と無関係に抜ける", 0.25: "弱い（0.25）", 0.5: "中くらい（0.5）", 1.0: "強い（1.0）"}
    # 図1：抜ける割合
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    for s in cols:
        d = dec[dec.抜け方の強さ == s]; ax.plot(d.事故率の順位_10分位, d.抜ける割合, "o-", color=cols[s], label=lab[s])
    ax.set_xticks(range(1, 11)); ax.set_xlabel("本当の事故率の順位（1＝いちばん事故が少ない10%、10＝いちばん多い10%）"); ax.set_ylabel("更新しない割合（%）")
    ax.set_title("10%の値上げで抜ける割合（置いた前提）"); ax.legend(frameon=False, fontsize=9, title="事故の少ない契約ほど抜ける強さ", title_fontsize=9)
    save(fig, "a468_lapse_by_risk.png", SRC + "。値上げがなければ、どの契約も10%が抜ける")
    # 図2：値上げ後の損害率
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]; x = np.arange(4); w = 0.2
    for i, s in enumerate(cols):
        d = one[one.抜け方の強さ == s]; b = ax.bar(x + (i - 1.5) * w, d.損害率, w, color=cols[s], label=lab[s])
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.3, f"{r.get_height():.0f}", ha="center", fontsize=7.5)
    for k, r in enumerate((5, 10, 20, 30)): ax.plot([k - 0.45, k + 0.45], [75 / (1 + r / 100)] * 2, color=INK, lw=1.2, ls="--")
    ax.axhline(75, color=GRAY, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(["+5%", "+10%", "+20%", "+30%"]); ax.set_ylim(50, 94); ax.set_ylabel("値上げ後の損害率（%）"); ax.set_xlabel("値上げの幅（点線＝偏りなく抜けるときの見込み、灰色の横線＝値上げの前の75%）", fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left"); ax.set_title("残った契約の損害率", fontsize=11)
    ax = axes[1]
    for s in cols:
        d = one[one.抜け方の強さ == s]; ax.plot(d.値上げ, d.保険料の合計の変化, "o-", color=cols[s], label=lab[s])
    ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("値上げの幅（%）"); ax.set_ylabel("保険料の合計の変化（%）"); ax.set_title("保険料の合計（契約の数×保険料）", fontsize=11)
    save(fig, "a468_loss_ratio_after_increase.png", SRC + "。見込みの値（偶然の振れなし）")
    # 図3：数年くり返す
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, c, ttl in zip(axes, ["損害率", "契約の数", "保険料の水準"], ["損害率（%）", "契約の数（はじめ＝100）", "保険料の水準（はじめ＝100）"]):
        for s in cols:
            d = sp[sp.抜け方の強さ == s]; ax.plot(d.年, d[c], "o-", color=cols[s], label=lab[s])
        ax.set_title(ttl, fontsize=11); ax.set_xlabel("年")
    axes[0].axhline(65, color=INK, lw=1, ls="--"); axes[0].text(6, 65.4, "目標 65%", ha="right", fontsize=8.5); axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("目標の損害率に届くまで、毎年値上げをくり返すと（1回の上限は20%）", y=1.03)
    save(fig, "a468_multi_year.png", SRC + "。見込みの値")

    g = lambda r, s, c: float(one[(one.値上げ == r) & (one.抜け方の強さ == s)][c].iloc[0])
    main = {"one_year": one.to_dict("records"), "multi_year_last": sp[sp.年 == 6].to_dict("records"), "by_spread": cvt.to_dict("records"),
            "realized": rz.to_dict("records"), "years_to_target": {str(s): int(sp[(sp.抜け方の強さ == s) & (sp.損害率 <= 65.05)].年.min()) if (sp[(sp.抜け方の強さ == s)].損害率 <= 65.05).any() else None for s in cols}}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    for t in (one, sp, cvt, rz, dec[dec.抜け方の強さ.isin([0.5, 1.0])]): print(t.to_string(), "\n")
    print(main["years_to_target"])
