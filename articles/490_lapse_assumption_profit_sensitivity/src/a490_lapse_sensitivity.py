"""490 解約率の仮定が実際とずれると、将来の利益の見込みはどれだけ動くのか（架空の契約群）"""
import json
import numpy as np
import pandas as pd
from scipy import optimize
from common import plt, save, RES, DATA, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "架空の契約群（作成者が式で計算）。死亡率は厚生労働省「令和6年簡易生命表」（男）を加工"
DISC = 0.015          # 利益を割り引く率
MARGIN = 0.05         # 基準の解約率で、利益の現価が保険料の現価の5%になるよう保険料を決める
AGE0 = 45


def qx():
    d = pd.read_csv(DATA / "life_table_2024_qx.csv")
    return d[d.sex == "男"].set_index("age").qx.reindex(range(0, 106)).values.astype(float)


def base_lapse(t):
    """経過年数 t（1年目=1）の解約率：1年目10%、2年目7%、3年目5%、4年目以降4%"""
    return {1: 0.10, 2: 0.07, 3: 0.05}.get(t, 0.04)


# 3つの架空の商品（1件あたり、保険金1,000万円・45歳加入・男）
PRODUCTS = [
    dict(key="T", name="定期型（10年、解約返戻金なし）", term=10, sa=1000.0, acq=1.2, ren=0.05, cv=None, asset=False),
    dict(key="L", name="保険料が一定で死亡率が上がる型（30年、返戻金なし）", term=30, sa=1000.0, acq=0.6, ren=0.05, cv=None, asset=False),
    dict(key="S", name="貯蓄型（20年、返戻金あり）", term=20, sa=1000.0, acq=0.8, ren=0.03, cv="savings", asset=True),
]
SPREAD = 0.008      # 貯蓄型：責任準備金（返戻金のもと）に付く運用の上乗せ（利差）
SURR_CHARGE = 0.05  # 貯蓄型：解約のときに積立から差し引く割合（10年目以降は0）


def cashflows(pr, prem, lapse_fn, q, mort_mult=lambda t: 1.0):
    """年ごとの利益（期始に保険料・経費、期末に保険金・解約返戻金）。在籍数は1から始める"""
    infl, prof, acct = 1.0, [], 0.0
    for t in range(1, pr["term"] + 1):
        age = AGE0 + t - 1
        qt = min(q[age] * mort_mult(t), 1.0)
        lt = lapse_fn(t)
        exp_ = prem * (pr["acq"] if t == 1 else pr["ren"])
        if pr["asset"]:
            # 貯蓄型：保険料の一部（危険・経費の分を除く）が積立に入り、利率1.0%で増える。運用は1.8%（差0.8%が利益）
            dep = prem - exp_ - qt * pr["sa"] * 0.3
            acct_start = acct + dep
            invest_gain = acct_start * (0.010 + SPREAD)
            acct = acct_start * 1.010
            surr_val = acct * (1 - (SURR_CHARGE if t < 10 else 0))
            # 利益＝保険料−経費−積立へ入れた額＋利差−死亡保障（積立を超える300万円）の支払い＋解約控除。
            # 積立そのもの（死亡・解約・満期で払う分）は、責任準備金の取り崩しと打ち消し合うので入れない
            cf = prem - exp_ - dep + (invest_gain - acct_start * 0.010) \
                - qt * pr["sa"] * 0.3 + (1 - qt) * lt * (acct - surr_val)
            prof.append(infl * cf)
            infl *= (1 - qt) * (1 - lt)
        else:
            cf = (prem - exp_) * (1 + DISC) - qt * pr["sa"]
            prof.append(infl * cf / (1 + DISC))
            infl *= (1 - qt) * (1 - lt)
    return np.array(prof)


def pv(x):
    return float(sum(v / (1 + DISC) ** t for t, v in enumerate(x)))


def prem_pv(pr, prem, lapse_fn, q):
    infl, tot = 1.0, 0.0
    for t in range(1, pr["term"] + 1):
        tot += infl * prem / (1 + DISC) ** (t - 1)
        infl *= (1 - min(q[AGE0 + t - 1], 1)) * (1 - lapse_fn(t))
    return tot


def run():
    q = qx()
    rows_sig, rows_mult, rows_sc = [], [], []
    prems = {}
    for pr in PRODUCTS:
        f = lambda P: pv(cashflows(pr, P, base_lapse, q)) - MARGIN * prem_pv(pr, P, base_lapse, q)
        P = optimize.brentq(f, 0.1, 500)
        prems[pr["key"]] = P
        sig = cashflows(pr, P, base_lapse, q)
        base = pv(sig)
        for t, v in enumerate(sig, 1):
            rows_sig.append(dict(product=pr["key"], year=t, profit=v))
        for m in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]:
            val = pv(cashflows(pr, P, lambda t, m=m: min(base_lapse(t) * m, 0.95), q))
            rows_mult.append(dict(product=pr["key"], mult=m, pv_profit=val, change=(val / base - 1) * 100))
        sc = [("解約率がすべて半分", lambda t: base_lapse(t) * 0.5, lambda t: 1.0),
              ("解約率がすべて1.5倍", lambda t: base_lapse(t) * 1.5, lambda t: 1.0),
              ("1〜3年目だけ2倍", lambda t: base_lapse(t) * (2 if t <= 3 else 1), lambda t: 1.0),
              ("4年目以降だけ2倍", lambda t: base_lapse(t) * (2 if t >= 4 else 1), lambda t: 1.0),
              ("5年目に一度だけ30%", lambda t: 0.30 if t == 5 else base_lapse(t), lambda t: 1.0),
              ("4年目以降は0%（解約しない）", lambda t: base_lapse(t) if t <= 3 else 0.0, lambda t: 1.0),
              ("1.5倍＋健康な人ほど解約（残った人の死亡率が上がる）", lambda t: base_lapse(t) * 1.5,
               lambda t: 1 + 0.03 * (t - 1) if t <= 11 else 1.30)]
        for name, lf, mm in sc:
            val = pv(cashflows(pr, P, lf, q, mm))
            rows_sc.append(dict(product=pr["key"], scenario=name, pv_profit=val, change=(val / base - 1) * 100))
    SIG, MUL, SC = pd.DataFrame(rows_sig), pd.DataFrame(rows_mult), pd.DataFrame(rows_sc)
    SIG.round(5).to_csv(RES / "profit_signature_base.csv", index=False)
    MUL.round(4).to_csv(RES / "change_by_lapse_multiplier.csv", index=False)
    SC.round(4).to_csv(RES / "change_by_scenario.csv", index=False)
    pd.DataFrame([dict(product=p["key"], name=p["name"], term=p["term"], annual_premium=round(prems[p["key"]], 4),
                       acq_ratio=p["acq"], renewal_ratio=p["ren"]) for p in PRODUCTS]).to_csv(DATA / "products.csv", index=False)
    pd.DataFrame([dict(year=t, base_lapse=base_lapse(t)) for t in range(1, 31)]).to_csv(DATA / "base_lapse.csv", index=False)

    names = {p["key"]: p["name"] for p in PRODUCTS}
    cols = dict(T=BLUE, L=ORANGE, S=GREEN)
    # 図1：年ごとの利益の出方（基準）
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    for ax, p in zip(axes, PRODUCTS):
        s = SIG[SIG["product"] == p["key"]]
        ax.bar(s.year, s.profit / prems[p["key"]] * 100, color=[cols[p["key"]] if v >= 0 else GRAY for v in s.profit])
        ax.axhline(0, color=INK, lw=.8)
        ax.set_title(p["name"], fontsize=10); ax.set_xlabel("経過年数")
    axes[0].set_ylabel("年ごとの利益（年払い保険料に対する%）")
    fig.suptitle("基準の解約率での、年ごとの利益の出方（加入時1件あたり、在籍の減りを含む）", fontsize=12.5, y=1.03)
    save(fig, "a490_profit_signature.png", SRC + "。灰色は赤字の年", y=-0.03)

    # 図2：解約率を一律に何倍かしたとき
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, keys, ttl in [(axes[0], ["T", "L", "S"], "3つの型"), (axes[1], ["T", "S"], "定期型と貯蓄型だけ（縦の目盛りを拡大）")]:
        for p in PRODUCTS:
            if p["key"] not in keys:
                continue
            s = MUL[MUL["product"] == p["key"]]
            ax.plot(s.mult, s.change, "o-", color=cols[p["key"]], label=p["name"])
        ax.axhline(0, color=INK, lw=.8); ax.axvline(1, color=GRAY, ls=":", lw=1)
        ax.set_xlabel("実際の解約率 ÷ 仮定の解約率"); ax.grid(alpha=.3); ax.set_title(ttl, fontsize=11.5)
    axes[0].set_ylabel("利益の現価の変化（%）"); axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("解約率の仮定が外れたときの、利益の見込みの動き", fontsize=13, y=1.02)
    save(fig, "a490_change_by_multiplier.png", SRC + "。どの商品も、基準の解約率で利益が保険料の現価の5%になるように保険料を合わせた")

    # 図3：場面ごと
    scen = list(dict.fromkeys(SC.scenario))
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    w = 0.27
    for j, p in enumerate(PRODUCTS):
        v = [SC[(SC["product"] == p["key"]) & (SC.scenario == s)].change.iloc[0] for s in scen]
        ax.barh(np.arange(len(scen)) + (j - 1) * w, v, w, color=cols[p["key"]], label=p["name"])
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(range(len(scen))); ax.set_yticklabels(scen, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("利益の現価の変化（%）"); ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
    ax.set_title("解約率のずれ方ごとの、利益の見込みの変化")
    save(fig, "a490_scenarios.png", SRC + "。最後の場面は、健康な人ほど解約し、残った人の死亡率が11年目までに30%上がると置いた", y=-0.1)

    main = dict(premium=prems,
                mult={p["key"]: {str(r.mult): round(float(r.change), 2) for _, r in MUL[MUL["product"] == p["key"]].iterrows()} for p in PRODUCTS},
                scen={p["key"]: {r.scenario: round(float(r.change), 2) for _, r in SC[SC["product"] == p["key"]].iterrows()} for p in PRODUCTS},
                base_pv={p["key"]: round(pv(cashflows(p, prems[p["key"]], base_lapse, q)), 4) for p in PRODUCTS},
                first_loss_year={p["key"]: int(SIG[(SIG["product"] == p["key"]) & (SIG.profit < 0)].year.min()) if (SIG[SIG["product"] == p["key"]].profit < 0).any() else None for p in PRODUCTS})
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(prems); print(MUL.pivot(index="mult", columns="product", values="change").round(2)); print(SC.pivot(index="scenario", columns="product", values="change").round(2)); print(main["first_loss_year"], main["base_pv"])


if __name__ == "__main__":
    run()
