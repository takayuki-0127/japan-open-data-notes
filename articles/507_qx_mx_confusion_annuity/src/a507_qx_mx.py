"""507 生命表の死亡率を「1年に死亡する確率 qx」と「年の途中の死亡の速さ mx」で取り違えると、年金の現価はどれだけずれるのか（保険数理・リスク）

令和6年簡易生命表（厚生労働省）の各歳の nqx・ndx・nLx を使う。
  qx：x歳ちょうどの人が1年以内に死亡する確率（表の「死亡率」）
  mx：中央死亡率 = ndx / nLx（1年に死亡した人数を、その1年に生きていた延べ人年で割ったもの）
mx は qx より必ず大きく、死亡率が高い高齢ほど差が開く。
終身年金（期始払い、105歳で打ち切り）の現価を、次の4通りの生存率で計算して比べる。
  正しい      ：p = 1 - qx
  m を q として：p = 1 - mx              （死亡の速さの表を、確率の表と思って使う）
  q を m として：p = 1 - qx/(1+qx/2)    （確率の表を、死亡の速さの表と思って「確率に直す」）
  m から直す  ：p = 1 - mx/(1+mx/2)    （死亡の速さの表を、年の途中で一様に死亡すると置いて正しく直す）
"""
import json, re
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "厚生労働省「令和6年簡易生命表」を加工して作成"
AGES = [20, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95]
RATES = [0.0, 0.005, 0.01, 0.02, 0.03]


def load():
    out = []
    for sheet, sex in [(0, "男"), (1, "女")]:
        t = pd.read_excel(DATA / "raw" / "mhlw_kani_2024.xlsx", sheet_name=sheet, header=None)
        for r in t.itertuples(index=False):
            m = re.fullmatch(r"(\d+)年", str(r[1]).strip())
            if m:
                out.append(dict(sex=sex, age=int(m.group(1)), qx=float(r[2]), lx=int(r[3]), dx=int(r[4]), Lx=int(r[5])))
    d = pd.DataFrame(out)
    d["mx"] = d.dx / d.Lx
    d["mx_udd"] = d.qx / (1 - d.qx / 2)          # qx から一様の死亡の置き方で作った mx（表の丸めの影響を見る）
    return d


def annuity(p, x, i):
    """x 歳からの期始払いの終身年金の現価（年1の支払い）。p は年齢 0〜105 の生存率"""
    s = np.cumprod(np.r_[1.0, p[x:-1]])           # x 歳から k 年生きる確率（k=0,1,...）
    v = (1 + i) ** -np.arange(len(s))
    return float((s * v).sum())


def main():
    d = load()
    d.to_csv(DATA / "life_table_2024_qx_mx.csv", index=False)
    cases = {}
    for sex, g in d.groupby("sex"):
        g = g.sort_values("age"); q, m = g.qx.to_numpy(), g.mx.to_numpy()
        q = np.where(g.age.to_numpy() == 105, 1.0, q)
        cases[sex] = {"正しい": 1 - q, "m を q として": np.clip(1 - m, 0, 1), "q を m として": 1 - q / (1 + q / 2),
                      "m から直す": np.clip(1 - m / (1 + m / 2), 0, 1)}
        cases[sex]["m を q として"][-1] = cases[sex]["q を m として"][-1] = cases[sex]["m から直す"][-1] = 0.0
    rows = []
    for sex, cs in cases.items():
        for x in AGES:
            for i in RATES:
                base = annuity(cs["正しい"], x, i)
                for k, p in cs.items():
                    a = annuity(p, x, i)
                    rows.append(dict(sex=sex, age=x, rate=i, case=k, annuity=a, gap_pct=(a / base - 1) * 100))
    res = pd.DataFrame(rows)
    res.round(5).to_csv(RES / "annuity_gaps.csv", index=False)
    ratio = d.assign(m_over_q=d.mx / d.qx - 1)[["sex", "age", "qx", "mx", "mx_udd", "m_over_q"]]
    ratio.round(6).to_csv(RES / "qx_mx_by_age.csv", index=False)

    piv = res[(res.rate == 0.01)].pivot_table(index=["sex", "age"], columns="case", values="gap_pct").round(2)
    print(piv.to_string())
    pick = lambda s, x, i, c: round(float(res.query("sex==@s and age==@x and rate==@i and case==@c").gap_pct.iloc[0]), 2)
    pickA = lambda s, x, i, c: round(float(res.query("sex==@s and age==@x and rate==@i and case==@c").annuity.iloc[0]), 3)
    out = dict(source=SRC, rate_main=0.01,
               m_over_q_pct={s: {a: round(float(ratio.query("sex==@s and age==@a").m_over_q.iloc[0]) * 100, 1) for a in [20, 40, 65, 80, 90, 100]} for s in ["男", "女"]},
               mx_vs_udd_maxabs_upto100=round(float((d[d.age <= 100].mx / d[d.age <= 100].mx_udd - 1).abs().max()) * 100, 2),
               a65={s: {c: pickA(s, 65, 0.01, c) for c in cases[s]} for s in ["男", "女"]},
               gap65={s: {c: pick(s, 65, 0.01, c) for c in cases[s]} for s in ["男", "女"]},
               gap_by_age_m_as_q={s: {x: pick(s, x, 0.01, "m を q として") for x in AGES} for s in ["男", "女"]},
               gap_by_age_q_as_m={s: {x: pick(s, x, 0.01, "q を m として") for x in AGES} for s in ["男", "女"]},
               gap65_by_rate_m_as_q={s: {i: pick(s, 65, i, "m を q として") for i in RATES} for s in ["男", "女"]})
    json.dump(out, open(RES / "a507_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["m_over_q_pct", "mx_vs_udd_maxabs_upto100", "a65", "gap65", "gap65_by_rate_m_as_q"]}, ensure_ascii=False))

    # 図1：mx が qx より何%大きいか（年齢別）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for s, col in [("男", BLUE), ("女", ORANGE)]:
        r = ratio[(ratio.sex == s) & (ratio.age.between(50, 104))]
        ax.plot(r.age, r.m_over_q * 100, color=col, lw=2, label=s)
    ax.set_xlabel("年齢"); ax.set_ylabel("mx が qx より大きい割合（%）")
    ax.set_title("mx は qx より、65歳で0.3〜0.5%、90歳で5〜8%、100歳で21〜27%大きい")
    ax.legend(frameon=False)
    save(fig, "a507_m_over_q.png", SRC + "。mx = ndx ÷ nLx、50〜104歳（若い年齢は ndx が小さく、整数の丸めで揺れるので省いた）")

    # 図2：年齢別の現価のずれ（利率1%）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for (s, c), col, ls in [(("男", "m を q として"), BLUE, "-"), (("女", "m を q として"), ORANGE, "-"),
                            (("男", "q を m として"), BLUE, "--"), (("女", "q を m として"), ORANGE, "--")]:
        r = res[(res.sex == s) & (res.case == c) & (res.rate == 0.01)]
        ax.plot(r.age, r.gap_pct, "o" + ls, color=col, lw=2, ms=4, label=f"{s}：{c}")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xlabel("年金を始める年齢"); ax.set_ylabel("正しい現価とのずれ（%）")
    ax.set_title("取り違えると、高齢から始める年金ほど現価が大きくずれる（利率1%）")
    ax.legend(frameon=False, fontsize=9, ncol=2)
    save(fig, "a507_gap_by_age.png", SRC + "。期始払いの終身年金、105歳で打ち切り")

    # 図3：65歳からの年金、利率別
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    w = 0.2; xs = np.arange(len(RATES))
    for j, ((s, c), col) in enumerate([(("男", "m を q として"), BLUE), (("女", "m を q として"), ORANGE),
                                        (("男", "q を m として"), LIGHT), (("女", "q を m として"), "#f3b49a")]):
        r = res[(res.sex == s) & (res.case == c) & (res.age == 65)].sort_values("rate")
        ax.bar(xs + (j - 1.5) * w, r.gap_pct, w, color=col, label=f"{s}：{c}")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs, [f"{i*100:g}%" for i in RATES]); ax.set_xlabel("利率")
    ax.set_ylabel("正しい現価とのずれ（%）"); ax.set_title("65歳からの年金：利率が高いほどずれは少し小さい")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower right")
    save(fig, "a507_gap_by_rate.png", SRC + "。期始払いの終身年金、105歳で打ち切り")


if __name__ == "__main__":
    main()
