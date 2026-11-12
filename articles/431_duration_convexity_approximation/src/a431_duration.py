"""431 金利が動いたとき、支払いの現在価値の変化は近似でどこまで出せるか（架空の支払いの流れ）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, save

R0 = 0.02                                   # もとの金利（年1回の複利、どの年限も同じ）
SHIFTS = np.array([-3, -2, -1, -0.5, 0.5, 1, 2, 3]) / 100
SRC = "架空の支払いの流れ（作成者が置いた数字）。金利は年1回の複利"


def streams():
    t = np.arange(1, 61)
    short = np.where(t <= 5, np.array([40, 25, 15, 12, 8] + [0] * 55), 0.0)          # 5年で払い終わる
    long_ = np.where(t <= 40, 100 * 0.97 ** (t - 1), 0.0)                             # 40年かけて少しずつ減る
    back = np.where((t >= 20) & (t <= 45), np.exp(-0.5 * ((t - 32) / 6.0) ** 2), 0.0)  # 30年前後に集まる
    out = {"短い（5年で払い終わる）": short, "長い（40年かけて減る）": long_, "後ろに偏る（30年前後に集まる）": back}
    return t, {k: v / v.sum() * 100 for k, v in out.items()}                           # 支払いの合計を100にそろえる


def pv(cf, t, r):
    return float((cf / (1 + r) ** t).sum())


def measures(cf, t, r):
    p = pv(cf, t, r)
    w = cf / (1 + r) ** t / p
    mac = float((w * t).sum())
    mod = mac / (1 + r)                                        # 修正デュレーション
    conv = float((w * t * (t + 1)).sum()) / (1 + r) ** 2       # 凸性（コンベクシティ）
    return p, mac, mod, conv


def approx(p, mod, conv, d):
    a1 = p * (1 - mod * d)                                     # デュレーションだけ
    a2 = p * (1 - mod * d + 0.5 * conv * d * d)                # 凸性を足す
    a3 = p * np.exp(-mod * d + 0.5 * (conv - mod * mod) * d * d)   # 対数で2次まで（割合の形で戻す）
    return a1, a2, a3


def main():
    t, S = streams()
    pd.DataFrame({"年": t, **S}).to_csv(DATA / "cashflows.csv", index=False)
    rows, meas = [], {}
    for name, cf in S.items():
        p, mac, mod, conv = measures(cf, t, R0)
        meas[name] = dict(pv=p, macaulay=mac, modified=mod, convexity=conv)
        for d in SHIFTS:
            ex = pv(cf, t, R0 + d)
            a1, a2, a3 = approx(p, mod, conv, d)
            rows.append(dict(流れ=name, 金利の動き_pt=d * 100, 正確な変化_pct=(ex / p - 1) * 100,
                             デュレーションだけ_pct=(a1 / p - 1) * 100, 凸性を足す_pct=(a2 / p - 1) * 100, 対数で2次_pct=(a3 / p - 1) * 100,
                             誤差_デュレーションだけ_pt=(a1 - ex) / p * 100, 誤差_凸性を足す_pt=(a2 - ex) / p * 100, 誤差_対数で2次_pt=(a3 - ex) / p * 100,
                             誤差_デュレーションだけ_変化比=(a1 - ex) / (ex - p) * 100, 誤差_凸性を足す_変化比=(a2 - ex) / (ex - p) * 100))
    T = pd.DataFrame(rows)
    T.round(4).to_csv(RES / "approximation_errors.csv", index=False)

    # 1回だけ払う流れで、年限を動かす（デュレーションと誤差の関係）
    sw = []
    for n in range(1, 51):
        cf = np.where(t == n, 100.0, 0.0)
        p, mac, mod, conv = measures(cf, t, R0)
        for d in (0.01, -0.01, 0.02, -0.02):
            ex = pv(cf, t, R0 + d); a1, a2, a3 = approx(p, mod, conv, d)
            sw.append(dict(年限=n, 金利の動き_pt=d * 100, 誤差_デュレーションだけ_pt=(a1 - ex) / p * 100,
                           誤差_凸性を足す_pt=(a2 - ex) / p * 100, 目安_half_C_d2_pt=-0.5 * conv * d * d * 100))
    SW = pd.DataFrame(sw); SW.round(4).to_csv(RES / "sweep_by_maturity.csv", index=False)

    # もとの金利を変える
    base = []
    for r0 in (0.005, 0.02, 0.05):
        for name, cf in S.items():
            p, mac, mod, conv = measures(cf, t, r0)
            for d in (0.01, -0.01):
                ex = pv(cf, t, r0 + d); a1, a2, _ = approx(p, mod, conv, d)
                base.append(dict(もとの金利_pct=r0 * 100, 流れ=name, 金利の動き_pt=d * 100, 修正デュレーション=mod, 凸性=conv,
                                 正確な変化_pct=(ex / p - 1) * 100, 誤差_デュレーションだけ_pt=(a1 - ex) / p * 100, 誤差_凸性を足す_pt=(a2 - ex) / p * 100))
    B = pd.DataFrame(base); B.round(4).to_csv(RES / "by_base_rate.csv", index=False)

    # 年限で動きが違う（平行でない）場合：短い年限は動かず、30年以上で+2ポイント
    twist = []
    for name, cf in S.items():
        p, mac, mod, conv = measures(cf, t, R0)
        bump = np.clip((t - 1) / 29.0, 0, 1) * 0.02
        ex = float((cf / (1 + R0 + bump) ** t).sum())
        for label, d in (("平均の動き（全年限の単純平均）", float(bump[:40].mean())), ("10年の所の動き", float(bump[9])), ("支払いで重みをつけた動き", float((cf * bump).sum() / cf.sum()))):
            a1, a2, _ = approx(p, mod, conv, d)
            twist.append(dict(流れ=name, 使った動き=label, 動き_pt=d * 100, 正確な変化_pct=(ex / p - 1) * 100,
                              凸性を足す_pct=(a2 / p - 1) * 100, 誤差_pt=(a2 - ex) / p * 100))
        # 年限ごとの感応度（年限ごとに現在価値の変化を足す）
        kr = float((cf / (1 + R0) ** t * (-(t / (1 + R0)) * bump + 0.5 * t * (t + 1) / (1 + R0) ** 2 * bump ** 2)).sum())
        twist.append(dict(流れ=name, 使った動き="年限ごとに計算して足す", 動き_pt=np.nan, 正確な変化_pct=(ex / p - 1) * 100,
                          凸性を足す_pct=kr / p * 100, 誤差_pt=(p + kr - ex) / p * 100))
    TW = pd.DataFrame(twist); TW.round(4).to_csv(RES / "non_parallel_shift.csv", index=False)

    main_ = {"もとの金利": R0, "流れごとの指標": meas,
             "誤差の最大_pt": {n: {"デュレーションだけ": float(T[T.流れ == n].誤差_デュレーションだけ_pt.abs().max()),
                                "凸性を足す": float(T[T.流れ == n].誤差_凸性を足す_pt.abs().max()),
                                "対数で2次": float(T[T.流れ == n].誤差_対数で2次_pt.abs().max())} for n in S}}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    cols = {list(S)[0]: GRAY, list(S)[1]: BLUE, list(S)[2]: ORANGE}
    # 図1
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=False)
    fine = np.linspace(-0.03, 0.03, 121)
    for a, (name, cf) in zip(ax, S.items()):
        p, mac, mod, conv = measures(cf, t, R0)
        ex = np.array([pv(cf, t, R0 + d) for d in fine]) / p * 100 - 100
        a1, a2, a3 = approx(p, mod, conv, fine)
        a.plot(fine * 100, ex, color=INK, lw=2.2, label="正確な値")
        a.plot(fine * 100, a1 / p * 100 - 100, color=GRAY, ls="--", lw=1.6, label="デュレーションだけ")
        a.plot(fine * 100, a2 / p * 100 - 100, color=ORANGE, ls=":", lw=2, label="凸性を足す")
        a.axhline(0, color=GRAY, lw=.6); a.axvline(0, color=GRAY, lw=.6)
        a.set_title(f"{name}\n修正デュレーション {mod:.1f}年", fontsize=11); a.set_xlabel("金利の動き（ポイント）")
    ax[0].set_ylabel("現在価値の変化（%）"); ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("金利が動いたときの現在価値の変化：正確な値と2つの近似", y=1.03)
    save(fig, "a431_pv_change_curves.png", SRC, y=-0.03)
    # 図2
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    for name in S:
        d = T[T.流れ == name]
        ax[0].plot(d.金利の動き_pt, d.誤差_デュレーションだけ_pt, "o-", color=cols[name], label=name)
        ax[1].plot(d.金利の動き_pt, d.誤差_凸性を足す_pt, "o-", color=cols[name], label=name)
    for a, ti in zip(ax, ("デュレーションだけ", "凸性を足す")):
        a.axhline(0, color=GRAY, lw=.6); a.set_title(f"{ti}：近似 − 正確な値"); a.set_xlabel("金利の動き（ポイント）"); a.set_ylabel("誤差（もとの現在価値に対する%ポイント）")
    ax[0].legend(frameon=False, fontsize=9)
    save(fig, "a431_error_by_shift.png", SRC, y=-0.03)
    # 図3
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    for d, c in ((1.0, BLUE), (2.0, ORANGE)):
        x = SW[SW.金利の動き_pt == d]
        ax[0].plot(x.年限, -x.誤差_デュレーションだけ_pt, color=c, lw=2, label=f"金利 +{d:.0f}ポイント：デュレーションだけ")
        ax[0].plot(x.年限, -x.目安_half_C_d2_pt, color=c, ls=":", lw=1.5, label="目安：凸性×動きの2乗÷2")
        ax[0].plot(x.年限, x.誤差_凸性を足す_pt, color=c, ls="--", lw=1.2, label="凸性を足す")
    ax[0].set_xlabel("支払いまでの年数（1回だけ払う流れ）"); ax[0].set_ylabel("誤差の大きさ（%ポイント）"); ax[0].set_title("年限が長いほど、誤差は年数の2乗で増える"); ax[0].legend(frameon=False, fontsize=8)
    names = list(S); w = 0.2; xs = np.arange(len(names))
    labs = ["平均の動き（全年限の単純平均）", "10年の所の動き", "支払いで重みをつけた動き", "年限ごとに計算して足す"]
    for i, (lab, c) in enumerate(zip(labs, (GRAY, BLUE, ORANGE, GREEN))):
        v = [float(TW[(TW.流れ == n) & (TW.使った動き == lab)].誤差_pt.iloc[0]) for n in names]
        ax[1].bar(xs + (i - 1.5) * w, v, w, color=c, label=lab)
    ax[1].axhline(0, color=GRAY, lw=.6); ax[1].set_xticks(xs); ax[1].set_xticklabels(["短い", "長い", "後ろに偏る"])
    ax[1].set_ylabel("誤差（%ポイント）"); ax[1].set_title("年限で動きが違うとき（30年以上だけ +2ポイント）"); ax[1].legend(frameon=False, fontsize=8)
    save(fig, "a431_maturity_and_twist.png", SRC, y=-0.03)
    print(json.dumps(main_, ensure_ascii=False, indent=1))
    print(T[["流れ", "金利の動き_pt", "正確な変化_pct", "誤差_デュレーションだけ_pt", "誤差_凸性を足す_pt", "誤差_対数で2次_pt", "誤差_デュレーションだけ_変化比"]].round(2).to_string())
    print(B.round(2).to_string()); print(TW.round(2).to_string())
    print(SW[SW.年限.isin([5, 10, 20, 30, 40])].round(2).to_string())


if __name__ == "__main__":
    main()
