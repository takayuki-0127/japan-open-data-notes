"""542 問い合わせの分類を2人が別々に付けると、何%が食い違い、カッパ係数はいくつになるのか

架空の問い合わせ（本当のカテゴリ6つ）に、2人の担当者 A・B が別々にカテゴリを付ける。
付け間違いの傾向（人ごとの取り違えやすさ、どちらとも取れる問い合わせ）を置き、
(1) 2,000件での一致率・コーエンのカッパ・混同行列、(2) 件数を変えたときのカッパの幅、
(3) カテゴリの偏りを変えたときに一致率とカッパがどう動くか を見る。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import cohen_kappa_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の問い合わせと分類（作成者が乱数で作成、seed 542）"
CATS = ["請求・支払い", "配送", "返品・交換", "使い方", "アカウント", "その他"]
K = len(CATS)
BASE_P = np.array([0.22, 0.26, 0.16, 0.18, 0.12, 0.06])  # 本当のカテゴリの割合（仮定）
ACC = {"A": 0.92, "B": 0.88}                            # ふつうの問い合わせで正しく付ける確率（仮定）
AMBIG = 0.15                                            # どちらとも取れる問い合わせの割合（仮定）
AMBIG_ACC = 0.55                                        # どちらとも取れる問い合わせで本当のカテゴリを付ける確率
# 間違えるときにどこへ付けやすいか（行：本当、列：付けたカテゴリ）。人ごとに少し違う傾向を置く
CONF = {"A": np.array([[0, 2, 1, 1, 3, 3], [1, 0, 4, 1, 1, 3], [1, 4, 0, 1, 1, 3], [1, 1, 1, 0, 3, 3], [3, 1, 1, 3, 0, 3], [2, 2, 2, 2, 2, 0]], float),
        "B": np.array([[0, 1, 1, 1, 4, 1], [1, 0, 6, 1, 1, 1], [1, 6, 0, 1, 1, 1], [1, 1, 1, 0, 4, 1], [4, 1, 1, 4, 0, 1], [2, 2, 2, 2, 2, 0]], float)}
for v in CONF.values():
    v /= v.sum(1, keepdims=True)


def simulate(n, p, rng):
    true = rng.choice(K, size=n, p=p)
    amb = rng.random(n) < AMBIG
    alt = np.array([rng.choice(K, p=(CONF["A"][t] + CONF["B"][t]) / 2) for t in true])  # どちらとも取れる相手のカテゴリ
    lab = {}
    for who in ["A", "B"]:
        acc = np.where(amb, AMBIG_ACC, ACC[who])
        ok = rng.random(n) < acc
        wrong_free = np.array([rng.choice(K, p=CONF[who][t]) for t in true])
        wrong = np.where(amb, alt, wrong_free)  # どちらとも取れる問い合わせでは、2人とも同じ相手に寄りやすい
        lab[who] = np.where(ok, true, wrong)
    return true, amb, lab["A"], lab["B"]


def kappa(a, b, k=K):
    m = np.zeros((k, k))
    np.add.at(m, (a, b), 1)
    n = m.sum()
    po = np.trace(m) / n
    pe = (m.sum(1) @ m.sum(0)) / n ** 2
    return po, pe, (po - pe) / (1 - pe), m


out = {"assume": {"cats": CATS, "base_p": BASE_P.tolist(), "acc": ACC, "ambig": AMBIG, "ambig_acc": AMBIG_ACC}}
rng = np.random.default_rng(542)
N = 2000
true, amb, a, b = simulate(N, BASE_P, rng)
po, pe, k, m = kappa(a, b)
assert abs(k - cohen_kappa_score(a, b)) < 1e-12
out["main"] = {"n": N, "agree": po, "disagree_n": int(N - np.trace(m)), "pe": pe, "kappa": k,
               "acc_A": float((a == true).mean()), "acc_B": float((b == true).mean()),
               "kappa_A_true": cohen_kappa_score(a, true), "kappa_B_true": cohen_kappa_score(b, true),
               "agree_ambig": float((a == b)[amb].mean()), "agree_clear": float((a == b)[~amb].mean()),
               "both_wrong_same": int(((a == b) & (a != true)).sum())}
cm = pd.DataFrame(m.astype(int), index=CATS, columns=CATS)
cm.to_csv(RES / "confusion_AB.csv")
off = [(CATS[i], CATS[j], int(m[i, j] + m[j, i])) for i in range(K) for j in range(i + 1, K)]
out["top_pairs"] = sorted(off, key=lambda x: -x[2])[:5]
pd.DataFrame({"true": [CATS[i] for i in true], "A": [CATS[i] for i in a], "B": [CATS[i] for i in b], "ambiguous": amb}).to_csv(RES / "labels_2000.csv", index=False)

# (2) 件数を変えたときのカッパの幅（同じ仕組みから 1,000回つくる）
rows = []
for n in [50, 100, 200, 500, 2000]:
    r2 = np.random.default_rng(542 + n)
    ks, ps = [], []
    for _ in range(1000):
        _, _, aa, bb = simulate(n, BASE_P, r2)
        p_, _, k_, _ = kappa(aa, bb)
        ks.append(k_); ps.append(p_)
    ks, ps = np.array(ks), np.array(ps)
    rows.append({"n": n, "kappa_mean": ks.mean(), "kappa_lo": np.quantile(ks, 0.025), "kappa_hi": np.quantile(ks, 0.975),
                 "agree_mean": ps.mean(), "agree_lo": np.quantile(ps, 0.025), "agree_hi": np.quantile(ps, 0.975),
                 "share_kappa_below_0.6": float((ks < 0.6).mean())})
sz = pd.DataFrame(rows)
sz.to_csv(RES / "kappa_by_n.csv", index=False)
out["by_n"] = sz.round(4).to_dict(orient="records")

# (3) カテゴリの偏り：いちばん多いカテゴリ（配送）の割合を変える。付け方の仕組みは同じ
rows = []
for top in [0.17, 0.3, 0.5, 0.7, 0.8, 0.9]:
    p = BASE_P.copy(); p[1] = 0
    p = p / p.sum() * (1 - top); p[1] = top
    r3 = np.random.default_rng(int(542 + top * 1000))
    res = [kappa(*simulate(N, p, r3)[2:]) for _ in range(200)]
    rows.append({"top_share": top, "agree": np.mean([x[0] for x in res]), "pe": np.mean([x[1] for x in res]),
                 "kappa": np.mean([x[2] for x in res])})
im = pd.DataFrame(rows)
im.to_csv(RES / "kappa_by_imbalance.csv", index=False)
out["by_imbalance"] = im.round(4).to_dict(orient="records")
(RES / "a542_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))

# 図1 混同行列
fig, ax = plt.subplots(figsize=(7.4, 6.0))
mm = m.copy()
ax.imshow(np.log1p(mm), cmap="Blues")
for i in range(K):
    for j in range(K):
        ax.text(j, i, int(mm[i, j]), ha="center", va="center", fontsize=10, color="white" if mm[i, j] > 150 else INK)
ax.set_xticks(range(K), CATS, rotation=30, ha="right"); ax.set_yticks(range(K), CATS)
ax.set_xlabel("担当者 B が付けたカテゴリ"); ax.set_ylabel("担当者 A が付けたカテゴリ")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title(f"2人の付け方の突き合わせ（{N:,}件）：一致 {po*100:.1f}%、カッパ {k:.2f}")
save(fig, "a542_confusion.png", SRC, y=-0.05)

# 図2 件数とカッパの幅
fig, ax = plt.subplots(figsize=(8.0, 4.2))
x = np.arange(len(sz))
ax.vlines(x, sz.kappa_lo, sz.kappa_hi, color=BLUE, lw=6, alpha=0.5)
ax.plot(x, sz.kappa_mean, "o", color=BLUE)
for xi, r in zip(x, sz.itertuples()):
    ax.text(xi + 0.12, r.kappa_lo, f"{r.kappa_lo:.2f}〜{r.kappa_hi:.2f}", va="bottom", fontsize=9.5)
ax.set_xticks(x, [f"{n:,}件" for n in sz.n]); ax.set_ylabel("カッパ係数（1,000回の95%の範囲）")
ax.axhline(0.6, color=GRAY, ls=":", lw=1)
ax.set_title("同じ2人・同じ付け方でも、件数が少ないとカッパは大きく揺れる")
save(fig, "a542_kappa_by_n.png", SRC)

# 図3 偏りと一致率・カッパ
fig, ax = plt.subplots(figsize=(8.0, 4.2))
ax.plot(im.top_share * 100, im.agree * 100, "o-", color=GREEN, label="一致率（%）")
ax.plot(im.top_share * 100, im.kappa * 100, "s-", color=ORANGE, label="カッパ係数（×100）")
ax.plot(im.top_share * 100, im.pe * 100, "^--", color=GRAY, label="偶然に一致する見込み（%）")
for r in im.itertuples():
    ax.text(r.top_share * 100, r.kappa * 100 - 5, f"{r.kappa:.2f}", ha="center", fontsize=9, color=ORANGE)
    ax.text(r.top_share * 100, r.agree * 100 + 2.5, f"{r.agree*100:.1f}", ha="center", fontsize=9, color=GREEN)
ax.set_xlabel("いちばん多いカテゴリ（配送）の割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("カテゴリが偏るほど、一致率は変わらなくてもカッパは下がる")
save(fig, "a542_kappa_by_imbalance.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
