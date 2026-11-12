"""320 無事故の年数は、次の年の事故をどこまで当てるのか
架空の契約者10万人（人ごとに事故の起こしやすさが違う）を11年分つくり、
10年目までの「続けて無事故だった年数」ごとに、11年目の事故率を数える。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK, save

SEED, NP, T, MU = 320, 100_000, 10, 0.08       # 10万人、10年見て11年目を当てる。平均の事故率は年8%
SOURCE = "架空のデータ（作成者が乱数で作成、seed 320）"


def simulate(rng, cv, n=NP):
    lam = np.full(n, MU) if cv == 0 else rng.gamma(1 / cv ** 2, MU * cv ** 2, n)   # 人ごとの事故の起こしやすさ（年あたりの平均件数）
    c = rng.poisson(lam[:, None], (n, T + 1))                                       # 年ごとの事故件数
    hist, nxt = c[:, :T], c[:, T]
    had = hist > 0
    last = np.where(had.any(1), T - 1 - np.argmax(had[:, ::-1], axis=1), -1)        # 最後に事故があった年（0〜9、なければ −1）
    streak = np.where(last < 0, T, T - 1 - last)                                    # 続けて無事故だった年数（0〜10）
    return lam, hist.sum(1), streak, nxt


def auc(score, y):
    """点数が高いほど事故あり、と当てたときの当たり方（0.5＝でたらめ、1＝完全）。同点は半分と数える"""
    order = np.argsort(score, kind="mergesort"); s = score[order]; yy = y[order]
    r = np.empty(len(s)); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]: j += 1
        r[i:j + 1] = (i + j) / 2 + 1; i = j + 1
    n1 = yy.sum(); n0 = len(yy) - n1
    return float((r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    rng = np.random.default_rng(SEED)
    out = {"設定": {"契約者の数": NP, "見る年数": T, "平均の事故率（年）": MU}, "人ごとの差": {}}
    rows = []
    for cv in (1.0, 0.0, 0.5, 1.5):
        lam, tot, streak, nxt = simulate(rng, cv)
        y = (nxt > 0).astype(int)
        a = np.inf if cv == 0 else 1 / cv ** 2; b = np.inf if cv == 0 else a / MU
        d = {"11年目に事故があった人の割合（%）": round(100 * float(y.mean()), 2), "11年目の事故件数の平均": round(float(nxt.mean()), 4)}
        for s in range(T + 1):
            m = streak == s
            rows.append({"人ごとの差（変動係数）": cv, "続けて無事故の年数": s, "人数": int(m.sum()), "人数の割合（%）": round(100 * float(m.mean()), 2),
                         "11年目の事故件数の平均": round(float(nxt[m].mean()), 4) if m.any() else None,
                         "全体の平均との比": round(float(nxt[m].mean() / nxt.mean()), 3) if m.any() else None,
                         "11年目の事故件数に占める割合（%）": round(100 * float(nxt[m].sum() / nxt.sum()), 2),
                         "本当の起こしやすさの平均": round(float(lam[m].mean()), 4) if m.any() else None})
        post = MU * np.ones(NP) if cv == 0 else (a + tot) / (b + T)                 # 10年の件数を全部使った見積もり
        d["10年無事故の人：11年目の事故件数の平均"] = rows[-1]["11年目の事故件数の平均"]
        d["10年無事故の人：式による値"] = round(MU if cv == 0 else float(a / (b + T)), 4)
        d["10年無事故の人：平均より何%低いか"] = round(100 * (1 - rows[-1]["全体の平均との比"]), 1)
        d["前の年に事故があった人：平均の何倍か"] = next(r["全体の平均との比"] for r in rows if r["人ごとの差（変動係数）"] == cv and r["続けて無事故の年数"] == 0)
        d["当たり方（AUC）"] = {"続けて無事故の年数": round(auc(-streak.astype(float), y), 3), "10年間の事故の回数": round(auc(tot.astype(float), y), 3),
                              "回数と年数の両方（式の見積もり）": round(auc(post + 1e-9 * (-streak), y), 3), "本当の起こしやすさ（知りえない上限）": round(auc(lam, y), 3)}
        # 割引を事故率の差に合わせたときの保険料の集まり方：全員同じ保険料のとき、無事故10年の人が払いすぎている割合
        m10 = streak == T
        d["10年無事故の人の割合（%）"] = round(100 * float(m10.mean()), 1)
        d["10年無事故の人が全体の事故件数に占める割合（%）"] = round(100 * float(nxt[m10].sum() / nxt.sum()), 1)
        out["人ごとの差"][f"変動係数{cv}"] = d
    by = pd.DataFrame(rows); by.to_csv(RES / "by_no_claim_years.csv", index=False)
    by[by["人ごとの差（変動係数）"] == 1.0].drop(columns=["人ごとの差（変動係数）"]).to_csv(DATA / "summary_base.csv", index=False)
    # 無事故の年数 t ごとの式の値（1回も事故がない人）
    th = [{"人ごとの差（変動係数）": cv, "無事故の年数": t, "平均より何%低いか（式）": round(100 * (1 - (1 / cv ** 2) / ((1 / cv ** 2) / MU + t) / MU), 1)}
          for cv in (0.5, 1.0, 1.5) for t in range(0, 21)]
    pd.DataFrame(th).to_csv(RES / "theory_discount.csv", index=False)
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(by, pd.DataFrame(th), out)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(by[by["人ごとの差（変動係数）"] == 1.0].to_string())


def figs(by, th, out):
    d = by[by["人ごとの差（変動係数）"] == 1.0]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(d["続けて無事故の年数"], 100 * d["11年目の事故件数の平均"], color=[ORANGE if s == 0 else BLUE for s in d["続けて無事故の年数"]])
    for s, v, p in zip(d["続けて無事故の年数"], 100 * d["11年目の事故件数の平均"], d["人数の割合（%）"]):
        ax.text(s, v + 0.3, f"{v:.1f}", ha="center", fontsize=9); ax.text(s, 0.4, f"{p:.0f}%", ha="center", fontsize=8, color="white")
    ax.axhline(100 * MU, color=GRAY, ls="--", lw=1); ax.text(10, 100 * MU + 0.25, "全体の平均 8件", ha="center", fontsize=9, color=GRAY)
    ax.set_xticks(range(T + 1)); ax.set_xticklabels([str(s) for s in range(T)] + ["10\n（10年ずっと）"])
    ax.set_xlabel("10年目の終わりの時点で、続けて無事故だった年数（棒の中の白字は人数の割合）"); ax.set_ylabel("11年目の事故件数（100人あたり）")
    ax.set_title("無事故の年数ごとの、次の年の事故（10万人、人ごとの差は変動係数1.0）")
    save(fig, "a320_by_years.png", SOURCE, y=-0.05)

    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    for cv, c in [(0.5, GREEN), (1.0, BLUE), (1.5, ORANGE)]:
        g = th[th["人ごとの差（変動係数）"] == cv]
        ax.plot(g["無事故の年数"], g["平均より何%低いか（式）"], color=c, lw=2, label=f"人ごとの差が変動係数{cv}")
        sim = out["人ごとの差"][f"変動係数{cv}"]["10年無事故の人：平均より何%低いか"]
        ax.plot([10], [sim], "o", color=c, ms=8)
    ax.plot([0, 20], [0, 0], color=GRAY, lw=2, label="人ごとの差がない（全員同じ）")
    ax.plot([10], [out["人ごとの差"]["変動係数0.0"]["10年無事故の人：平均より何%低いか"]], "o", color=GRAY, ms=8)
    ax.set_xlabel("1回も事故がなかった年数"); ax.set_ylabel("次の年の事故率が、平均より何%低いか"); ax.set_xticks(range(0, 21, 2))
    ax.set_title("無事故が続くほど、どれだけ低く見てよいか（線は式、点は10万人で数えた値）"); ax.legend(frameon=False, fontsize=9.5)
    save(fig, "a320_discount.png", SOURCE)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    keys = ["続けて無事故の年数", "10年間の事故の回数", "回数と年数の両方（式の見積もり）", "本当の起こしやすさ（知りえない上限）"]; cols = [BLUE, ORANGE, GREEN, GRAY]
    cvs = [0.0, 0.5, 1.0, 1.5]; x = np.arange(len(cvs))
    for k, (key, c) in enumerate(zip(keys, cols)):
        v = [out["人ごとの差"][f"変動係数{cv}"]["当たり方（AUC）"][key] for cv in cvs]
        ax.bar(x + (k - 1.5) * 0.2, v, 0.19, color=c, label=key)
        for xx, y in zip(x + (k - 1.5) * 0.2, v): ax.text(xx, y + 0.004, f"{y:.2f}", ha="center", fontsize=8)
    ax.axhline(0.5, color=GRAY, ls="--", lw=1); ax.set_ylim(0.45, 0.85)
    ax.set_xticks(x); ax.set_xticklabels(["差なし", "変動係数0.5", "変動係数1.0", "変動係数1.5"]); ax.set_xlabel("人ごとの事故の起こしやすさの差")
    ax.set_ylabel("当てる力（AUC、0.5がでたらめ）"); ax.set_title("無事故の年数は、次の年の事故をどこまで当てるか"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a320_auc.png", SOURCE)


if __name__ == "__main__":
    main()
