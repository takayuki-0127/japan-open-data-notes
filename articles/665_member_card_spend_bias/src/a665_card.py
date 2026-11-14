"""665 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか

架空の店の1年分のレシート6万枚。まとめ買いの客ほど会員カードを出す（ポイントが多くつくので）。
  C1 会員カードを出したレシートだけの平均
  C2 全レシートの平均（本当の客単価）
  C3 金額帯ごとの会員の平均を、全レシートの帯ごとの枚数で重みづけ（帯の数3・5・10）
カードを出す割合を全体で変えたとき、C1 のずれがどう変わるかも見る。DuckDB（1スレッド）と pandas の一致を確かめる。seed 665。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店のレシート（作成者が乱数で作成、seed 665）"
rng = np.random.default_rng(665)
N = 60000
amount = np.maximum(50, np.round(rng.lognormal(np.log(1500), 0.8, N) / 10) * 10).astype(int)
slope = 0.9
def p_card(a, icpt):
    return 1 / (1 + np.exp(-(icpt + slope * np.log(a / 1500))))
icpt0 = -0.35
card = (rng.random(N) < p_card(amount, icpt0)).astype(int)
E = {3: [0, 1000, 3000, np.inf], 5: [0, 500, 1000, 2000, 5000, np.inf], 10: [0, 300, 500, 750, 1000, 1500, 2000, 3000, 5000, 8000, np.inf]}
R = pd.DataFrame({"receipt_id": np.arange(1, N + 1), "amount": amount, "card": card})
for k, e in E.items():
    R[f"b{k}"] = pd.cut(R.amount, e, right=False, labels=False).astype(int) + 1
R.to_csv(DATA / "receipts.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("receipts", R)
qs = [x for x in (SQL / "02_card_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
d1 = con.execute(qs[0]).fetchone(); d2 = con.execute(qs[1]).fetchone()
member = R[R.card == 1].amount.mean(); allv = R.amount.mean()
def corr(df, k):
    m = df[df.card == 1].groupby(f"b{k}").amount.mean(); c = df.groupby(f"b{k}").size()
    return float((m * c).sum() / c[m.index].sum())
assert np.isclose(d1[0], member) and np.isclose(d1[1], allv) and np.isclose(d2[0], corr(R, 5))
pct = lambda v: round((v / allv - 1) * 100, 2)
# 帯ごと
bt = R.groupby("b10").agg(n=("amount", "size"), card_rate=("card", "mean"), lo=("amount", "min"), hi=("amount", "max")).reset_index()
bt.to_csv(RES / "by_band10.csv", index=False)
# 全体のカードの割合を変える（同じ金額のまま、カードを出すかだけ引き直す）
sweep = []
for icpt in np.linspace(-2.5, 2.0, 10):
    rr = np.random.default_rng(int(1000 + icpt * 100))
    c2 = (rr.random(N) < p_card(amount, icpt)).astype(int)
    df = R.assign(card=c2)
    sweep.append({"icpt": round(float(icpt), 2), "card_rate": round(float(c2.mean() * 100), 1), "member_bias_pct": pct(amount[c2 == 1].mean()),
                  "corr5_bias_pct": pct(corr(df, 5))})
SW = pd.DataFrame(sweep); SW.to_csv(RES / "sweep_card_rate.csv", index=False)
out = {"n_receipts": N, "card_rate_pct": round(card.mean() * 100, 1), "true_avg": round(allv, 1), "member_avg": round(member, 1),
       "member_bias_pct": pct(member), "noncard_avg": round(float(R[R.card == 0].amount.mean()), 1),
       "corrected": {f"{k}帯": {"avg": round(corr(R, k), 1), "bias_pct": pct(corr(R, k))} for k in E},
       "card_rate_by_band10": {f"{int(r.lo)}〜{int(r.hi)}円": round(r.card_rate * 100, 1) for r in bt.itertuples()},
       "sweep": sweep, "median_true": int(np.median(amount)), "median_member": int(np.median(amount[card == 1]))}
json.dump(out, open(RES / "a665_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：帯ごとのカードの割合
fig, ax = plt.subplots(figsize=(8.5, 3.6))
lab = [f"{int(e)}〜" if np.isfinite(e) else "" for e in E[10][:-1]]
ax.bar(range(10), bt.card_rate * 100, color=BLUE)
ax.set_xticks(range(10)); ax.set_xticklabels(["〜299", "300〜", "500〜", "750〜", "1000〜", "1500〜", "2000〜", "3000〜", "5000〜", "8000〜"], fontsize=9)
ax.set_xlabel("レシートの金額（円）"); ax.set_ylabel("会員カードを出した割合（%）"); ax.axhline(card.mean() * 100, color=GRAY, ls="--", lw=1)
ax.set_title(f"金額の大きいレシートほど、会員カードが出される（全体では{card.mean() * 100:.0f}%）")
save(fig, "a665_card_rate.png", SRC)
# 図2：方法ごとの客単価
fig, ax = plt.subplots(figsize=(8.5, 3.4))
lab = ["会員カードを出したレシートだけ", "金額帯3つで補正", "金額帯5つで補正", "金額帯10で補正", "全レシート（本当の客単価）"]
v = [member, corr(R, 3), corr(R, 5), corr(R, 10), allv]
ax.barh(lab[::-1], v[::-1], color=[ORANGE, LIGHT, LIGHT, BLUE, GRAY][::-1])
for i, x in enumerate(v[::-1]):
    ax.text(x, i, f" {x:,.0f}円（{pct(x):+.1f}%）", va="center", fontsize=9)
ax.set_xlim(0, max(v) * 1.3); ax.set_xlabel("客単価（円）")
ax.set_title("会員だけの客単価は高く出て、金額帯で重みづけると戻る")
save(fig, "a665_methods.png", SRC, y=-0.05)
# 図3：カードの割合とずれ
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(SW.card_rate, SW.member_bias_pct, marker="o", color=ORANGE, label="会員カードを出したレシートだけ")
ax.plot(SW.card_rate, SW.corr5_bias_pct, marker="s", color=BLUE, label="金額帯5つで補正")
ax.axhline(0, color="black", lw=0.8); ax.set_xlabel("会員カードを出したレシートの割合（%）"); ax.set_ylabel("本当の客単価とのずれ（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("カードを出す人が少ないほど、会員だけの客単価は高く出る")
save(fig, "a665_by_card_rate.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
