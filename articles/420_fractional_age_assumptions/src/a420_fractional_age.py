"""420 1年より短い期間の死亡率は、仮定の置き方でどれだけ違うか（公表の生命表と、正解の分かる死亡率）
3つの仮定：①1年の中で一様に亡くなる（UDD）②死亡の強さが1年の中で一定（CF）③バルドゥッチの仮定
年の死亡率 q から、月ごとの生きる割合を作り、月払いの年金・月ごとに払う死亡保険の現在価値を比べる。"""
import json
import numpy as np, pandas as pd
from common import *

I = 0.01; V12 = (1 + I) ** (-1 / 12)
LT = pd.read_csv(DATA / "life_table_2024_qx.csv")
QM = LT[LT.sex == "男"].set_index("age").qx.reindex(range(0, 106)).values
QF = LT[LT.sex == "女"].set_index("age").qx.reindex(range(0, 106)).values
def extend(q):
    """表の最後（105歳以上は死亡率1）をそのまま使うと、最後の1年の置き方だけで差が出る。
    105歳から先は、90〜104歳の死亡の強さの伸び方をそのまま延ばして120歳まで続ける（121歳で1にする）"""
    mu = -np.log(1 - q[90:105]); c = np.exp(np.polyfit(np.arange(90, 105), np.log(mu), 1)[0])
    ext = 1 - np.exp(-mu[-1] * c ** np.arange(1, 17))
    return np.concatenate([q[:105], ext, [1.0]])
QM, QF = extend(QM), extend(QF)
NAMES = ["一様に亡くなる", "死亡の強さが一定", "バルドゥッチ"]

def surv_within(q, s, name):
    """年のはじめに生きている人が、その年の s（0〜1）の時点まで生きている割合"""
    if name == "一様に亡くなる": return 1 - s * q
    if name == "死亡の強さが一定": return (1 - q) ** s
    return (1 - q) / (1 - (1 - s) * q)

def monthly_lx(q, x0, name):
    """x0 歳から、月ごとの生きている割合（0か月目=1）"""
    out = [1.0]; l = 1.0; s = np.arange(1, 13) / 12
    for x in range(x0, len(q)):
        out.extend(l * surv_within(q[x], s, name)); l *= 1 - q[x]
        if l <= 0: break
    return np.array(out)

def values(l):
    """月払いの終身年金（月のはじめに1/12ずつ）と、亡くなった月の終わりに1を払う終身保険の現在価値、平均余命"""
    k = np.arange(len(l)); d = l[:-1] - l[1:]
    return dict(年金=float((V12 ** k[:-1] * l[:-1]).sum() / 12), 保険=float((V12 ** k[1:] * d).sum()), 余命=float((l[:-1] + l[1:]).sum() / 24))

def term_ins(l, years):
    k = np.arange(len(l)); d = l[:-1] - l[1:]; m = min(years * 12, len(d))
    return float((V12 ** k[1:m + 1] * d[:m]).sum())

# ---- 1. 公表の生命表：月ごとの死亡率（その月のはじめに生きている人が、その月に亡くなる割合）
rows = []
for sex, Q in [("男", QM), ("女", QF)]:
    for x in [60, 70, 80, 90, 95, 100, 104]:
        for n in NAMES:
            s = np.arange(0, 13) / 12; l = surv_within(Q[x], s, n); mq = 1 - l[1:] / l[:-1]
            rows.append(dict(性別=sex, 年齢=x, 年の死亡率=Q[x], 仮定=n, **{f"{m}か月目": mq[m - 1] for m in range(1, 13)}, 半年の時点で生きている割合=surv_within(Q[x], 0.5, n), **{"最後の月÷最初の月": mq[-1] / mq[0]}))
MQ = pd.DataFrame(rows); MQ.to_csv(RES / "monthly_death_rates.csv", index=False)

# ---- 2. 公表の生命表：現在価値の差
rows = []
for sex, Q in [("男", QM), ("女", QF)]:
    for x in [40, 60, 65, 75, 85, 90, 95, 100]:
        base = None
        for n in NAMES:
            l = monthly_lx(Q, x, n); v = values(l); v["定期保険_1年"] = term_ins(l, 1); v["定期保険_10年"] = term_ins(l, 10)
            if base is None: base = v
            rows.append(dict(性別=sex, 年齢=x, 仮定=n, **v, **{f"{k}_一様との差_パーセント": 100 * (v[k] / base[k] - 1) for k in v}))
        # よく使う近似：年払い（年のはじめ）の年金 − 11/24
        la = np.concatenate([[1.0], np.cumprod(1 - Q[x:])]); ann = float(((1 + I) ** (-np.arange(len(la))) * la).sum())
        rows.append(dict(性別=sex, 年齢=x, 仮定="近似（年払い − 11/24）", 年金=ann - 11 / 24, 年金_一様との差_パーセント=100 * ((ann - 11 / 24) / base["年金"] - 1)))
PV = pd.DataFrame(rows); PV.to_csv(RES / "present_values_life_table.csv", index=False)

# ---- 3. 正解の分かる死亡率：ゴンペルツ μ(x)=B c^x を公表の生命表（男、60〜100歳）に当てる
ages = np.arange(60, 101); mu = -np.log(1 - QM[60:101]); b1, b0 = np.polyfit(ages + 0.5, np.log(mu), 1); B, C = np.exp(b0), np.exp(b1)
def true_lx_monthly(x0, xmax=121):
    t = np.arange(0, (xmax - x0) * 12 + 1) / 12
    return np.exp(-B * C ** x0 * (C ** t - 1) / np.log(C))
def q_from_true(xmax=121):
    x = np.arange(0, xmax); return 1 - np.exp(-B * C ** x * (C - 1) / np.log(C))
QT = q_from_true()
rows = []
for x in [60, 65, 75, 85, 90, 95, 100, 105]:
    lt = true_lx_monthly(x); tv = values(lt); tv["定期保険_1年"] = term_ins(lt, 1); tv["定期保険_10年"] = term_ins(lt, 10)
    rows.append(dict(年齢=x, 仮定="正解", 年の死亡率=QT[x], **tv))
    for n in NAMES:
        l = monthly_lx(QT, x, n); v = values(l); v["定期保険_1年"] = term_ins(l, 1); v["定期保険_10年"] = term_ins(l, 10)
        rows.append(dict(年齢=x, 仮定=n, 年の死亡率=QT[x], **v, **{f"{k}_正解との差_パーセント": 100 * (v[k] / tv[k] - 1) for k in v}))
TR = pd.DataFrame(rows); TR.to_csv(RES / "against_known_truth.csv", index=False)
# 月ごとの死亡率（正解と3つの仮定、90歳と100歳）
rows = []
for x in [80, 90, 100]:
    lt = true_lx_monthly(x)[:13]; rows.append(dict(年齢=x, 仮定="正解", **{f"{m}か月目": 1 - lt[m] / lt[m - 1] for m in range(1, 13)}))
    for n in NAMES:
        l = surv_within(QT[x], np.arange(0, 13) / 12, n); rows.append(dict(年齢=x, 仮定=n, **{f"{m}か月目": 1 - l[m] / l[m - 1] for m in range(1, 13)}))
TM = pd.DataFrame(rows); TM.to_csv(RES / "monthly_rates_against_truth.csv", index=False)
pd.DataFrame(dict(年齢=np.arange(60, 106), 公表の死亡率_男=QM[60:106], ゴンペルツの死亡率=QT[60:106])).round(5).to_csv(DATA / "gompertz_fit_vs_life_table.csv", index=False)

g = lambda df, c, **kw: float(df.loc[np.logical_and.reduce([df[k] == v for k, v in kw.items()]), c].iloc[0])
main = dict(条件=dict(金利=I, 生命表="令和6年簡易生命表（男・女）", ゴンペルツ=dict(B=float(B), c=float(C))),
            月の死亡率_男={str(x): {n: dict(最初=g(MQ, "1か月目", 性別="男", 年齢=x, 仮定=n), 最後=g(MQ, "12か月目", 性別="男", 年齢=x, 仮定=n), 比=g(MQ, "最後の月÷最初の月", 性別="男", 年齢=x, 仮定=n)) for n in NAMES} for x in (60, 80, 90, 100, 104)},
            現在価値の差_男={str(x): {n: {k: g(PV, f"{k}_一様との差_パーセント", 性別="男", 年齢=x, 仮定=n) for k in ("年金", "保険", "定期保険_1年", "余命")} for n in NAMES[1:]} for x in (65, 75, 85, 95, 100)},
            現在価値の差_女={str(x): {n: {k: g(PV, f"{k}_一様との差_パーセント", 性別="女", 年齢=x, 仮定=n) for k in ("年金", "保険", "定期保険_1年")} for n in NAMES[1:]} for x in (65, 85, 100)},
            近似_年金の差_男={str(x): g(PV, "年金_一様との差_パーセント", 性別="男", 年齢=x, 仮定="近似（年払い − 11/24）") for x in (65, 75, 85, 95, 100)},
            正解との差={str(x): {n: {k: g(TR, f"{k}_正解との差_パーセント", 年齢=x, 仮定=n) for k in ("年金", "保険", "定期保険_1年", "余命")} for n in NAMES} for x in (65, 85, 95, 100, 105)},
            年金の値_男={str(x): g(PV, "年金", 性別="男", 年齢=x, 仮定="一様に亡くなる") for x in (65, 85, 100)})
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

NC = {NAMES[0]: BLUE, NAMES[1]: GRAY, NAMES[2]: ORANGE}
fig, ax = plt.subplots(1, 3, figsize=(13, 4.1))
for a, x in zip(ax, [60, 90, 100]):
    for n in NAMES:
        r = MQ[(MQ.性別 == "男") & (MQ.年齢 == x) & (MQ.仮定 == n)].iloc[0]
        a.plot(range(1, 13), [r[f"{m}か月目"] * 100 for m in range(1, 13)], "o-", ms=3, color=NC[n], label=n)
    a.set_title(f"{x}歳（年の死亡率 {QM[x]*100:.1f}%）"); a.set_xlabel("年の中の月"); a.set_xticks([1, 3, 6, 9, 12])
ax[0].set_ylabel("その月に亡くなる割合（%）"); ax[0].legend(fontsize=8, frameon=False)
save(fig, "a420_monthly_rates_by_assumption.png", "厚生労働省「令和6年簡易生命表」（男）の年の死亡率から、3つの仮定で月ごとに分けた。作成者が計算")

fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3))
xs = [40, 60, 65, 75, 85, 90, 95, 100]
for a, (k, ttl) in zip(ax, [("年金", "月払いの終身年金の現在価値"), ("定期保険_1年", "1年の定期保険（亡くなった月の終わりに払う）の現在価値")]):
    for n in NAMES[1:]:
        d = PV[(PV.性別 == "男") & (PV.仮定 == n)].set_index("年齢").loc[xs]
        a.plot(xs, d[f"{k}_一様との差_パーセント"], "o-", color=NC[n], label=n)
    if k == "年金":
        d = PV[(PV.性別 == "男") & (PV.仮定 == "近似（年払い − 11/24）")].set_index("年齢").loc[xs]; a.plot(xs, d["年金_一様との差_パーセント"], "s--", color=GREEN, label="近似（年払い − 11/24）")
    a.axhline(0, color=BLUE, lw=0.8); a.set_xlabel("年齢"); a.set_ylabel("「一様に亡くなる」との差（%）"); a.set_title(ttl, fontsize=11); a.legend(fontsize=8, frameon=False)
save(fig, "a420_present_value_differences.png", "令和6年簡易生命表（男）、金利1%。0の線＝「一様に亡くなる」仮定。作成者が計算")

fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3))
xs = [60, 65, 75, 85, 90, 95, 100, 105]
for n in NAMES:
    d = TR[TR.仮定 == n].set_index("年齢").loc[xs]; ax[0].plot(xs, d["年金_正解との差_パーセント"], "o-", color=NC[n], label=n)
ax[0].axhline(0, color=INK, lw=0.8); ax[0].set_xlabel("年齢"); ax[0].set_ylabel("正解との差（%）"); ax[0].set_title("正解の分かる死亡率で：月払いの終身年金"); ax[0].legend(fontsize=8, frameon=False)
r0 = TM[(TM.年齢 == 100) & (TM.仮定 == "正解")].iloc[0]; ax[1].plot(range(1, 13), [r0[f"{m}か月目"] * 100 for m in range(1, 13)], "k-", lw=2, label="正解（強さが年齢とともに上がる）")
for n in NAMES:
    r = TM[(TM.年齢 == 100) & (TM.仮定 == n)].iloc[0]; ax[1].plot(range(1, 13), [r[f"{m}か月目"] * 100 for m in range(1, 13)], "o-", ms=3, color=NC[n], label=n)
ax[1].set_xlabel("年の中の月"); ax[1].set_ylabel("その月に亡くなる割合（%）"); ax[1].set_title("100歳の1年：月ごとの死亡率"); ax[1].legend(fontsize=8, frameon=False)
save(fig, "a420_against_known_truth.png", "正解＝死亡の強さが B×c^年齢 で上がる死亡率（令和6年簡易生命表（男）の60〜100歳に当てた）。作成者が計算")
print(json.dumps(main, ensure_ascii=False, indent=1))
