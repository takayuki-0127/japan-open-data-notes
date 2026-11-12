"""484 明細の「単価×数量」と「金額」が合わない行は、どの確かめ方で何件見つかるのか（架空の明細10万行）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の明細（作成者が乱数で作成、seed 484）"
rng = np.random.default_rng(484)
N = 100_000
NI = 800
master = pd.DataFrame({"item": np.arange(NI)})
dec = rng.random(NI) < 0.15                                     # 15%の品目は単価に小数（量り売りなど）
p = np.round(np.exp(rng.uniform(np.log(50), np.log(20000), NI)))
p = np.where(dec, np.round(p / 10 + rng.integers(0, 10, NI) / 10, 1), p)
master["price"] = p
master.to_csv(DATA / "fictional_price_master.csv", index=False)

item = rng.integers(0, NI, N)
qty = rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 6, 10, 12, 24], N)
ret = rng.random(N) < 0.05; qty = np.where(ret, -qty, qty)
price = master.price.values[item]
disc = np.where((rng.random(N) < 0.10) & ~ret, np.round(np.abs(price * qty) * rng.choice([0.05, 0.1, 0.2], N)), 0)
trunc = rng.random(N) < 0.03                                   # 3%の行は切り捨てで金額を出す仕組み（正しい行）
base = price * qty - disc
amount = np.where(trunc, np.trunc(base), np.floor(np.abs(base) + 0.5) * np.sign(base))
kind = np.array(["正しい"] * N, dtype=object)

# わざと入れる誤り（行は重ならないように選ぶ）
ERR = [("桁ずれ（×10・÷10）", 150), ("符号の誤り（返品が＋）", 150), ("数字の入れ替え", 150), ("1〜9円の打ち間違い", 150),
       ("ケースとバラの取り違え（×12）", 150), ("値引きの引き忘れ", 150), ("単価の誤り（金額は計算し直し）", 150), ("数量の誤り（金額は計算し直し）", 150)]
pool = rng.permutation(N); k0 = 0
uprice = price.copy(); uqty = qty.copy(); udisc = disc.copy()
for name, n in ERR:
    cand = []
    while len(cand) < n:
        i = pool[k0]; k0 += 1
        if name == "符号の誤り（返品が＋）" and qty[i] > 0: continue
        if name == "値引きの引き忘れ" and disc[i] == 0: continue
        if name == "数字の入れ替え" and abs(amount[i]) < 100: continue
        cand.append(i)
    for i in cand:
        kind[i] = name
        if name.startswith("桁ずれ"):
            amount[i] = amount[i] * 10 if rng.random() < .5 else np.round(amount[i] / 10)
        elif name.startswith("符号"):
            amount[i] = abs(amount[i])
        elif name.startswith("数字の入れ替え"):
            s = str(int(abs(amount[i]))); j = rng.integers(0, len(s) - 1)
            t = s[:j] + s[j + 1] + s[j] + s[j + 2:]
            if t == s: t = s[:-2] + str((int(s[-2]) + 1) % 10) + s[-1]
            amount[i] = np.sign(amount[i]) * int(t)
        elif name.startswith("1〜9円"):
            amount[i] = amount[i] + rng.choice([-1, 1]) * rng.integers(1, 10)
        elif name.startswith("ケース"):
            amount[i] = amount[i] * 12
        elif name.startswith("値引き"):
            amount[i] = np.floor(abs(price[i] * qty[i]) + 0.5) * np.sign(qty[i])
        elif name.startswith("単価"):
            uprice[i] = np.round(price[i] * rng.choice([0.9, 1.1, 0.5, 2.0]), 1); amount[i] = np.floor(abs(uprice[i] * qty[i] - disc[i]) + 0.5) * np.sign(qty[i])
        elif name.startswith("数量"):
            uqty[i] = qty[i] + rng.choice([-1, 1]) * rng.integers(1, 3)
            if uqty[i] == 0: uqty[i] = qty[i] + 1
            amount[i] = np.floor(abs(uprice[i] * uqty[i] - disc[i]) + 0.5) * np.sign(uqty[i])
L = pd.DataFrame({"line_id": np.arange(N), "item": item, "unit_price": uprice, "qty": uqty, "discount": udisc, "amount": amount, "kind": kind,
                  "legit_truncation": trunc & (kind == "正しい"), "legit_decimal": dec[item] & (kind == "正しい")})
L.drop(columns=["kind", "legit_truncation", "legit_decimal"]).to_csv(DATA / "fictional_lines.csv", index=False)
L[["line_id", "kind"]].to_csv(DATA / "answer_key.csv", index=False)

SQL = """
SELECT l.line_id,
  (l.amount <> l.unit_price * l.qty)                                            AS c1_exact,
  (abs(l.amount - l.unit_price * l.qty) > 1)                                    AS c2_tol1yen,
  (abs(l.amount - l.unit_price * l.qty) > 0.005 * abs(l.unit_price * l.qty))   AS c3_tol05pct,
  (abs(l.amount - (l.unit_price * l.qty - l.discount)) > 0.5)                   AS c4_disc_half,
  (abs(l.amount - (l.unit_price * l.qty - l.discount)) >= 1)                    AS c5_disc_1yen,
  (sign(l.amount) <> sign(l.qty) AND l.amount <> 0)                             AS c6_sign,
  (l.unit_price <> m.price)                                                     AS c7_master
FROM L l JOIN master m USING (item)"""
F = duckdb.sql(SQL).df().sort_values("line_id").reset_index(drop=True)
# pandas で同じ判定をして一致を確かめる
b = L.unit_price * L.qty
chk = {"c1_exact": L.amount != b, "c2_tol1yen": (L.amount - b).abs() > 1, "c3_tol05pct": (L.amount - b).abs() > 0.005 * b.abs(),
       "c4_disc_half": (L.amount - (b - L.discount)).abs() > 0.5, "c5_disc_1yen": (L.amount - (b - L.discount)).abs() >= 1,
       "c6_sign": (np.sign(L.amount) != np.sign(L.qty)) & (L.amount != 0), "c7_master": L.unit_price != master.price.values[L.item]}
for c, v in chk.items():
    assert (F[c].values == v.values).all(), c
F["c8_combo"] = F.c5_disc_1yen | F.c6_sign | F.c7_master
NAMES = {"c1_exact": "完全一致（値引き列を見ない）", "c2_tol1yen": "差1円まで許す", "c3_tol05pct": "差0.5%まで許す",
         "c4_disc_half": "値引きを引いて差0.5円まで", "c5_disc_1yen": "値引きを引いて差1円未満まで", "c6_sign": "符号だけ",
         "c7_master": "単価をマスタと照合", "c8_combo": "値引きを引いて1円未満＋符号＋マスタ"}
X = F.merge(L[["line_id", "kind", "legit_truncation", "legit_decimal"]], on="line_id")
rows = []
for c, nm in NAMES.items():
    r = {"check": c, "name": nm}
    for name, n in ERR:
        r[name] = int(X[X.kind == name][c].sum())
    r["found_total"] = int(X[X.kind != "正しい"][c].sum())
    r["false_alarm"] = int(X[X.kind == "正しい"][c].sum())
    ok = X.kind == "正しい"; hasd = L.discount > 0                      # 正しい行を重ならない4つに分ける
    r["fa_discount"] = int(X[ok & hasd][c].sum())
    r["fa_trunc"] = int(X[ok & ~hasd & X.legit_truncation][c].sum())
    r["fa_decimal"] = int(X[ok & ~hasd & ~X.legit_truncation & X.legit_decimal][c].sum())
    r["fa_other"] = int(X[ok & ~hasd & ~X.legit_truncation & ~X.legit_decimal][c].sum())
    rows.append(r)
T = pd.DataFrame(rows); T.to_csv(RES / "detection_by_check.csv", index=False)
res = {"lines": N, "errors": int((L.kind != "正しい").sum()), "error_types": dict(ERR),
       "legit": {"decimal_price_lines": int(L.legit_decimal.sum()), "truncation_lines": int(L.legit_truncation.sum()),
                 "discount_lines": int(((L.kind == "正しい") & (L.discount > 0)).sum()), "return_lines": int(((L.kind == "正しい") & (L.qty < 0)).sum())},
       "by_check": T.to_dict("records")}
# 照合で見つけた行の金額の影響
amt_err = (L.amount - (price * qty - disc).round()).where(L.kind != "正しい", 0)
res["error_amount_abs_total"] = float(amt_err.abs().sum())
json.dump(res, open(RES / "a484_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：確かめ方ごとの「見つけた数」と「空振り」
fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1]})
ys = np.arange(len(T))[::-1]
axs[0].barh(ys, T.found_total, color=BLUE); axs[0].set_yticks(ys); axs[0].set_yticklabels(T.name, fontsize=9)
axs[0].set_xlim(0, 1300); axs[0].axvline(1200, color=GRAY, ls="--", lw=1)
for y, v in zip(ys, T.found_total): axs[0].text(v + 15, y, f"{v:,}", va="center", fontsize=8)
axs[0].set_title("わざと入れた誤り1,200件のうち見つけた数", loc="left", fontsize=11)
axs[1].barh(ys, T.false_alarm, color=ORANGE); axs[1].set_yticks(ys); axs[1].set_yticklabels([])
for y, v in zip(ys, T.false_alarm): axs[1].text(v + 200, y, f"{v:,}", va="center", fontsize=8)
axs[1].set_xlim(0, max(T.false_alarm) * 1.2)
axs[1].set_title("正しい行98,800件のうち鳴った数（空振り）", loc="left", fontsize=11)
save(fig, "a484_found_and_false.png", SRC)
# 図2：誤りの種類×確かめ方（見つけた割合）
M = T.set_index("name")[[e for e, _ in ERR]] / 150 * 100
fig, ax = plt.subplots(figsize=(12, 5))
im = ax.imshow(M.values, cmap="Blues", vmin=0, vmax=100, aspect="auto")
ax.set_yticks(range(len(M))); ax.set_yticklabels(M.index, fontsize=9)
ax.set_xticks(range(M.shape[1])); ax.set_xticklabels([e.replace("（", "\n（") for e in M.columns], fontsize=8)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M.values[i, j]; ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 60 else INK)
ax.set_title("誤りの種類ごとに見つけた割合（%、各150件）", loc="left")
save(fig, "a484_by_error_type.png", SRC)
# 図3：空振りの中身
fig, ax = plt.subplots(figsize=(10, 4.2))
sub = T[["name", "fa_decimal", "fa_discount", "fa_trunc"]].set_index("name")
left = np.zeros(len(sub))
for c, colr, lab in [("fa_discount", ORANGE, "値引きがある行"), ("fa_decimal", LIGHT, "単価に小数がある行（四捨五入）"), ("fa_trunc", GRAY, "切り捨てで金額を出す行")]:
    ax.barh(ys, sub[c], left=left, color=colr, label=lab); left += sub[c].values
ax.set_yticks(ys); ax.set_yticklabels(sub.index, fontsize=9); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("空振りになった正しい行の中身（件）", loc="left")
save(fig, "a484_false_alarm_breakdown.png", SRC)
print(T.to_string()); print(res["legit"])
