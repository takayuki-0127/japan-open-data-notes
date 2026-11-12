"""489 5歳刻みの死亡率から各歳の死亡率を作ると、年金の現価はどれだけずれるのか（令和6年簡易生命表）"""
import json
import numpy as np
import pandas as pd
from scipy import interpolate
from common import plt, save, RES, DATA, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "厚生労働省「令和6年簡易生命表」を加工して作成"
RATES = [0.0, 0.01, 0.02]
STARTS = [40, 50, 60, 62, 65, 67, 70, 72, 75, 77, 80, 82, 85, 87, 90]
METH = [("step", "区間の中は同じ死亡率（階段）", GRAY), ("lin", "直線でつなぐ", BLUE),
        ("loglin", "対数で直線につなぐ", ORANGE), ("spline", "累積の死亡の力を曲線でつなぐ", GREEN)]


def load():
    d = pd.read_csv(DATA / "life_table_2024_qx.csv")
    out = {}
    for sex in ("男", "女"):
        q = d[d.sex == sex].set_index("age").qx.reindex(range(0, 106)).values.astype(float)
        out[sex] = q
    return out


def group(q, w):
    """各歳の死亡率から、w 歳ごとの区間の生存率（x 歳の人が x+w 歳まで生きる割合）を作る。最後の区間は w 歳に満たないことがある"""
    starts = list(range(0, 105, w))
    surv = []
    for s in starts:
        e = min(s + w, 105)
        surv.append((s, e, np.prod(1 - q[s:e])))
    return surv


def rebuild(surv, method):
    """区間の生存率から、各歳（0〜104歳）の死亡率を作る。105歳は1とする"""
    q = np.zeros(106)
    if method == "step":
        for s, e, p in surv:
            q[s:e] = 1 - p ** (1 / (e - s))
    else:
        # 区間の「平均の死亡の力」を区間の真ん中に置き、つなぐ
        mid = np.array([(s + e) / 2 for s, e, _ in surv])
        mu = np.array([-np.log(p) / (e - s) for s, e, p in surv])
        ages = np.arange(105) + 0.5
        if method == "lin":
            m = np.interp(ages, mid, mu)
        elif method == "loglin":
            m = np.exp(np.interp(ages, mid, np.log(mu)))
        if method in ("lin", "loglin"):
            # 区間の生存率が元と同じになるよう、区間ごとに比を掛けて合わせる
            for s, e, p in surv:
                tgt = -np.log(p)
                m[s:e] *= tgt / m[s:e].sum()
            q[:105] = 1 - np.exp(-m)
        else:
            # 累積の死亡の力 H(x) を区間の端で決め、単調な曲線（PCHIP）でつなぐ
            knots = [0] + [e for _, e, _ in surv]
            H = np.concatenate([[0], np.cumsum([-np.log(p) for _, _, p in surv])])
            f = interpolate.PchipInterpolator(knots, H)
            h = f(np.arange(106))
            q[:105] = 1 - np.exp(-np.diff(h))
    q[105] = 1.0
    return np.clip(q, 0, 1)


def annuity(q, x, i):
    """x 歳から、年1回・期始払いの終身年金の現価（1円あたり）"""
    v = 1 / (1 + i)
    p, tot = 1.0, 0.0
    for t, a in enumerate(range(x, 106)):
        tot += p * v ** t
        p *= 1 - q[a]
    return tot


def life_exp(q, x):
    p, tot = 1.0, 0.0
    for a in range(x, 106):
        p_next = p * (1 - q[a])
        tot += (p + p_next) / 2
        p = p_next
    return tot


def run():
    Q = load()
    rows_q, rows_a, rows_e = [], [], []
    for sex, q in Q.items():
        for w in (5, 10):
            surv = group(q, w)
            for key, lab, _ in METH:
                qr = rebuild(surv, key)
                for age in range(0, 105):
                    rows_q.append(dict(sex=sex, width=w, method=key, age=age, q_true=q[age], q_rebuilt=qr[age],
                                       rel_err=(qr[age] / q[age] - 1) * 100))
                for i in RATES:
                    for x in STARTS:
                        t, r = annuity(q, x, i), annuity(qr, x, i)
                        rows_a.append(dict(sex=sex, width=w, method=key, rate=i, start=x, true=t, rebuilt=r, err=(r / t - 1) * 100))
                for x in (0, 65, 75):
                    t, r = life_exp(q, x), life_exp(qr, x)
                    rows_e.append(dict(sex=sex, width=w, method=key, start=x, true=t, rebuilt=r, diff_years=r - t))
    TQ, TA, TE = pd.DataFrame(rows_q), pd.DataFrame(rows_a), pd.DataFrame(rows_e)
    TQ.round(7).to_csv(RES / "qx_rebuilt.csv", index=False)
    TA.round(6).to_csv(RES / "annuity_errors.csv", index=False)
    TE.round(5).to_csv(RES / "life_expectancy.csv", index=False)
    band = TQ[(TQ.age >= 30) & (TQ.age <= 99)]
    qs = band.groupby(["sex", "width", "method"]).rel_err.agg(mean_abs=lambda v: np.abs(v).mean(), max_abs=lambda v: np.abs(v).max()).reset_index()
    qs.round(3).to_csv(RES / "qx_error_summary_30_99.csv", index=False)
    pd.DataFrame([dict(sex=s, width=w, start=a, end=e, survival=p) for s, q in Q.items() for w in (5, 10) for a, e, p in group(q, w)]).round(8).to_csv(DATA / "grouped_survival.csv", index=False)

    # 図1：男・5歳刻み、60〜100歳の死亡率
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    sub = TQ[(TQ.sex == "男") & (TQ.width == 5)]
    ax = axes[0]
    tr = sub[sub.method == "step"]
    ax.plot(tr.age, tr.q_true, color=INK, lw=2.5, label="元の各歳の死亡率")
    for key, lab, col in METH:
        s = sub[sub.method == key]
        ax.plot(s.age, s.q_rebuilt, color=col, lw=1.3, ls="--" if key != "step" else "-", label=lab, drawstyle="steps-mid" if key == "step" else "default")
    ax.set_yscale("log"); ax.set_xlim(60, 100); ax.set_ylim(0.005, 0.5)
    ax.set_xlabel("年齢"); ax.set_ylabel("死亡率（対数目盛り）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("男、60〜100歳（5歳刻みから作り直し）", fontsize=11.5)
    ax = axes[1]
    for key, lab, col in METH:
        s = sub[(sub.method == key) & (sub.age >= 30) & (sub.age <= 99)]
        ax.plot(s.age, s.rel_err, color=col, lw=1.4, label=lab)
    ax.axhline(0, color=INK, lw=.8); ax.set_xlabel("年齢"); ax.set_ylabel("死亡率の誤差（%）")
    ax.set_title("各歳の死亡率の誤差（男、30〜99歳）", fontsize=11.5); ax.grid(alpha=.3)
    save(fig, "a489_qx_rebuilt.png", SRC + "。5歳ごとの区間の生存率だけを残し、4つの方法で各歳に戻した")

    # 図2：年金現価の誤差（男、5歳刻み・10歳刻み、利率1%）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, w in zip(axes, (5, 10)):
        s0 = TA[(TA.sex == "男") & (TA.width == w) & (TA.rate == 0.01)]
        for key, lab, col in METH:
            s = s0[s0.method == key]
            ax.plot(s.start, s.err, "o-", color=col, label=lab)
        ax.axhline(0, color=INK, lw=.8); ax.grid(alpha=.3)
        ax.set_xlabel("年金を受け取りはじめる年齢"); ax.set_title(f"{w}歳刻みから作り直したとき", fontsize=11.5)
    axes[0].set_ylabel("終身年金の現価の誤差（%、利率1%）"); axes[0].legend(frameon=False, fontsize=8.5)
    save(fig, "a489_annuity_error.png", SRC + "。男。年1回・期始払いの終身年金。元の各歳の死亡率で計算した現価との差")

    # 図3：65歳の年金現価の誤差（男女×利率×刻み）
    fig, ax = plt.subplots(figsize=(11, 4.6))
    cats = [(s, w, i) for s in ("男", "女") for w in (5, 10) for i in RATES]
    xl = [f"{s}\n{w}歳刻み\n利率{int(i * 100)}%" for s, w, i in cats]
    wdt = 0.2
    for j, (key, lab, col) in enumerate(METH):
        v = [TA[(TA.sex == s) & (TA.width == w) & (TA.rate == i) & (TA.start == 65) & (TA.method == key)].err.iloc[0] for s, w, i in cats]
        ax.bar(np.arange(len(cats)) + (j - 1.5) * wdt, v, wdt, color=col, label=lab)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(range(len(cats))); ax.set_xticklabels(xl, fontsize=8)
    ax.set_ylabel("65歳からの終身年金の現価の誤差（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
    ax.set_title("65歳からの年金の現価：つなぎ方と刻みの幅での誤差")
    save(fig, "a489_annuity65.png", SRC)

    def a_err(sex, w, key, x, i):
        return round(float(TA[(TA.sex == sex) & (TA.width == w) & (TA.method == key) & (TA.start == x) & (TA.rate == i)].err.iloc[0]), 4)
    main = dict(qx_summary=qs.round(2).to_dict("records"),
                ann65={f"{s}_{w}_{k}_{i}": a_err(s, w, k, 65, i) for s in ("男", "女") for w in (5, 10) for k, _, _ in METH for i in RATES},
                ann_true65={f"{s}_{i}": round(annuity(Q[s], 65, i), 4) for s in ("男", "女") for i in RATES},
                max_abs_ann_err={f"{s}_{w}_{k}": round(float(TA[(TA.sex == s) & (TA.width == w) & (TA.method == k)].err.abs().max()), 4) for s in ("男", "女") for w in (5, 10) for k, _, _ in METH},
                life_exp=TE.round(3).to_dict("records"))
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(qs.round(2).to_string())
    print(TA[(TA.start == 65)].round(4).pivot_table(index=["sex", "width", "rate"], columns="method", values="err").to_string())
    print(TA[(TA.sex == "男") & (TA.rate == 0.01)].pivot_table(index=["width", "start"], columns="method", values="err").round(3).to_string())
    print(TE[TE.start == 65].round(3).to_string())


if __name__ == "__main__":
    run()
