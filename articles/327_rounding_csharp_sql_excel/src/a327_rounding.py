"""327 C# の Math.Round・SQL Server の ROUND・Excel の ROUND は同じ答えを返すか
3つの丸め方（四捨五入＝0から遠いほうへ／偶数丸め／切り捨て）を Python で再現し、架空の金額10万件で比べる。
C#・SQL Server・Excel の本体では動かしていない（公開されている仕様の再現）。"""
import json
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_DOWN, ROUND_FLOOR
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

SEED = 327; rng = np.random.default_rng(SEED); N = 100_000
# ---------- 架空の金額：単価（円）×数量×掛け率。返品は負 ----------
price = rng.choice([98, 120, 150, 198, 250, 298, 380, 450, 500, 598, 750, 980, 1250, 1500, 1980, 2500, 3300, 4980], N)
qty = rng.integers(1, 6, N)
rate = rng.choice(["1", "0.95", "0.9", "0.85", "0.7", "0.5", "1.08", "1.1"], N, p=[.2, .1, .15, .05, .1, .1, .1, .2])
sign = np.where(rng.random(N) < 0.05, -1, 1)                      # 5% は返品（負）
exact = [Decimal(int(p) * int(q) * int(s)) * Decimal(r) for p, q, s, r in zip(price, qty, sign, rate)]
df = pd.DataFrame({"price": price, "qty": qty, "rate": rate, "sign": sign, "exact": [str(x) for x in exact]})
df.to_csv(DATA / "amounts.csv", index=False)

def q(x, mode, nd=0): return x.quantize(Decimal(1).scaleb(-nd), rounding=mode)
half_away = [q(x, ROUND_HALF_UP) for x in exact]        # 0から遠いほうへ：SQL Server の ROUND(x,0)、Excel の ROUND(x,0)、C# の MidpointRounding.AwayFromZero
half_even = [q(x, ROUND_HALF_EVEN) for x in exact]      # 偶数丸め：C# の Math.Round(decimal) の既定（MidpointRounding.ToEven）
trunc = [q(x, ROUND_DOWN) for x in exact]               # 切り捨て（0のほうへ）：SQL Server の ROUND(x,0,1)、Excel の ROUNDDOWN / TRUNC
js_round = [(x + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR) for x in exact]   # 参考：0.5を足して切り下げ（JavaScript の Math.round の形）
E_ = np.array([float(x) for x in exact]); frac = np.array([x - x.to_integral_value(rounding=ROUND_FLOOR) for x in exact])
is_int = np.array([x == x.to_integral_value() for x in exact]); tie = np.array([abs(x - x.to_integral_value(rounding=ROUND_DOWN)) == Decimal("0.5") for x in exact])
M = {"四捨五入（0から遠いほうへ）": half_away, "偶数丸め": half_even, "切り捨て（0のほうへ）": trunc, "（参考）0.5を足して切り下げ": js_round}
tot_exact = sum(exact)
rows = [{"丸め方": k, "合計": int(sum(v)), "正確な合計との差（円）": float(sum(v) - tot_exact), "1件あたりの差（円）": float(sum(v) - tot_exact) / N} for k, v in M.items()]
bias = pd.DataFrame(rows); bias.to_csv(RES / "total_bias.csv", index=False)
names = list(M); pair = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        d = np.array([a != b for a, b in zip(M[names[i]], M[names[j]])])
        pair.append({"A": names[i], "B": names[j], "答えが違う件数": int(d.sum()), "割合": d.mean(), "うち負の金額": int((d & (sign < 0)).sum())})
pair = pd.DataFrame(pair); pair.to_csv(RES / "pair_diff.csv", index=False)
# 掛け率ごとの「ちょうど0.5」の割合
by_rate = pd.DataFrame({"rate": rate, "tie": tie, "nonint": ~is_int}).groupby("rate").agg(件数=("tie", "size"), ちょうど半分=("tie", "mean"), 端数あり=("nonint", "mean")).reset_index()
by_rate.to_csv(RES / "tie_by_rate.csv", index=False)

# ---------- 小数第2位への丸め：10進の型と、2進の小数（double）の違い ----------
# 小数第3位が5で終わる値（単価×税率など）を作り、3通りで小数第2位に丸める
K = 100_000
cents3 = rng.integers(1, 2_000_000, K) * 10 + 5                 # 0.015 〜 19999.995（小数第3位が5）
dec = [Decimal(int(c)) / Decimal(1000) for c in cents3]
dbl = np.array([float(d) for d in dec])
dec_away = [q(d, ROUND_HALF_UP, 2) for d in dec]                 # 10進の型で四捨五入：SQL Server の ROUND(DECIMAL,2)
dec_even = [q(d, ROUND_HALF_EVEN, 2) for d in dec]               # 10進の型で偶数丸め：C# の Math.Round(decimal,2)
def cs_round_double(x, nd=2):                                    # C# の Math.Round(double, 2) の形：10^2 を掛け、偶数丸めし、10^2 で割る
    p = 10.0 ** nd; return float(np.round(x * p)) / p            # np.round は偶数丸め（.5 ちょうどのとき偶数へ）
cs_dbl = [Decimal(repr(cs_round_double(x))) for x in dbl]
py_dbl = [Decimal(repr(round(float(x), 2))) for x in dbl]        # 参考：Python の round(float,2)（2進の値どおりに正しく丸める）
def excel_round(x, nd=2):                                        # Excel の ROUND の形：有効15桁の10進に直してから四捨五入（0から遠いほうへ）
    return q(Decimal(f"{x:.15g}"), ROUND_HALF_UP, nd)
xl = [excel_round(x) for x in dbl]
cmp2 = {"C# double（掛けて偶数丸めして割る）と C# decimal（偶数丸め）": np.mean([a != b for a, b in zip(cs_dbl, dec_even)]),
        "C# double と SQL Server DECIMAL（四捨五入）": np.mean([a != b for a, b in zip(cs_dbl, dec_away)]),
        "C# decimal（偶数丸め）と SQL Server DECIMAL（四捨五入）": np.mean([a != b for a, b in zip(dec_even, dec_away)]),
        "Excel（15桁に直して四捨五入）と SQL Server DECIMAL": np.mean([a != b for a, b in zip(xl, dec_away)]),
        "（参考）Python round(float,2) と SQL Server DECIMAL": np.mean([a != b for a, b in zip(py_dbl, dec_away)])}
tot2 = {"正確な合計": float(sum(dec)), "SQL Server DECIMAL 四捨五入": float(sum(dec_away) - sum(dec)), "C# decimal 偶数丸め": float(sum(dec_even) - sum(dec)),
        "C# double": float(sum(cs_dbl) - sum(dec)), "Excel": float(sum(xl) - sum(dec))}
# double で x*100 が .5 ちょうどにならなかった割合
prod = dbl * 100.0; exact_half = np.mean(prod == np.floor(prod) + 0.5); below = np.mean(prod < np.floor(prod + 0.25) + 0.5 - 0) 
side = {"ちょうど .5": float(exact_half), ".5 より小さい": float(np.mean(prod - np.floor(prod) < 0.5)), ".5 より大きい": float(np.mean(prod - np.floor(prod) > 0.5))}
ex = pd.DataFrame({"値": [str(d) for d in dec[:0]]})
examples = []
for v in ["2.675", "1.005", "0.125", "2.5", "3.5", "-2.5", "1.115", "0.285"]:
    d = Decimal(v); x = float(v); nd = 0 if v in ("2.5", "3.5", "-2.5") else 2
    examples.append({"値": v, "桁": nd, "SQL Server ROUND（DECIMAL）": str(q(d, ROUND_HALF_UP, nd)), "C# Math.Round（decimal）": str(q(d, ROUND_HALF_EVEN, nd)),
                     "C# Math.Round（double）": repr(cs_round_double(x, nd)) if nd else str(int(np.round(x))), "Excel ROUND": str(excel_round(x, nd))})
examples = pd.DataFrame(examples); examples.to_csv(RES / "examples.csv", index=False)
main = {"N": N, "share_nonint": float((~is_int).mean()), "share_tie": float(tie.mean()), "share_negative": float((sign < 0).mean()),
        "tie_even_floor": float(np.mean([t and (int(abs(x).to_integral_value(rounding=ROUND_DOWN)) % 2 == 0) for t, x in zip(tie, exact)])),
        "total_exact": float(tot_exact), "bias": bias.set_index("丸め方")["正確な合計との差（円）"].to_dict(),
        "pair": {f"{a} × {b}": [int(n), float(s)] for a, b, n, s in zip(pair.A, pair.B, pair["答えが違う件数"], pair["割合"])},
        "two_decimals": {k: float(v) for k, v in cmp2.items()}, "two_decimals_total_diff": tot2, "double_x100_side": side}
json.dump(main, open(RES / "a327_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(by_rate.to_string()); print(examples.to_string())

SRC = "架空の金額（作成者が乱数で作成、seed 327）。C#・SQL Server・Excel の丸めは、仕様を Python で再現したもの（本体では未検証）"
# 図1：丸め方どうしで答えが違う割合
fig, ax = plt.subplots(figsize=(8.4, 3.6)); p3 = pair[~pair.A.str.contains("参考") & ~pair.B.str.contains("参考")]
lab = [f"{a.split('（')[0]} と {b.split('（')[0]}" for a, b in zip(p3.A, p3.B)]
ax.barh(lab[::-1], (p3["割合"] * 100).values[::-1], color=[GRAY, GRAY, BLUE][::-1])
for i, v in enumerate((p3["割合"] * 100).values[::-1]): ax.text(v + 0.15, i, f"{v:.1f}%（{int(p3['答えが違う件数'].values[::-1][i]):,}件）", va="center", fontsize=10)
ax.set_xlim(0, 16); ax.set_xlabel("10万件のうち、答えが違った割合（%）")
ax.set_title("円未満を丸めた答えが違う割合：四捨五入と偶数丸めは1.5%、切り捨てとは約1割", loc="left", fontsize=11.5)
save(fig, "a327_pair_diff.png", SRC, y=-0.08)
# 図2：合計の偏り
fig, ax = plt.subplots(figsize=(8.4, 3.4)); b3 = bias[~bias["丸め方"].str.contains("参考")]
ax.barh(b3["丸め方"][::-1], b3["正確な合計との差（円）"][::-1], color=[ORANGE, GREEN, BLUE])
for i, v in enumerate(b3["正確な合計との差（円）"].values[::-1]): ax.text(v + (150 if v >= 0 else -150), i, f"{v:+,.0f}円", va="center", ha="left" if v >= 0 else "right", fontsize=10)
ax.axvline(0, color=INK, lw=0.8); lim = abs(b3["正確な合計との差（円）"]).max() * 1.35; ax.set_xlim(-lim, lim)
ax.set_xlabel("丸める前の合計との差（円、10万件の合計）")
ax.set_title("合計の偏り：偶数丸めはほぼ0、四捨五入は少し多く、切り捨ては大きく少ない", loc="left", fontsize=11.5)
save(fig, "a327_total_bias.png", SRC, y=-0.08)
# 図3：例の表
fig, ax = plt.subplots(figsize=(9.0, 3.4)); ax.axis("off")
t = ax.table(cellText=examples.drop(columns="桁").values, colLabels=["値", "SQL Server ROUND\n（DECIMAL）", "C# Math.Round\n（decimal）", "C# Math.Round\n（double）", "Excel ROUND"], loc="center", cellLoc="center")
t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 1.55)
for (r_, c_), cell in t.get_celld().items():
    cell.set_edgecolor("#d0d0d0")
    if r_ == 0: cell.set_facecolor("#eef3fa"); cell.set_text_props(weight="bold"); cell.set_height(cell.get_height() * 1.5)
    elif c_ > 0:
        row = examples.iloc[r_ - 1]; base = row["SQL Server ROUND（DECIMAL）"]
        if float(cell.get_text().get_text()) != float(base): cell.set_facecolor("#fde3d6")
ax.set_title("同じ値を丸めた答え（色つきは SQL Server の ROUND と違うもの。上5つは小数第2位、下3つは整数に丸める）", loc="left", fontsize=10.5)
save(fig, "a327_examples.png", SRC, y=0.04)
