"""674 広告の成果を「最後の接点」に付けるか均等に分けるかで、広告ごとの成果はどれだけ違うのか

架空の利用者 5万人。広告の接点は4種類（ディスプレイ広告・SNS広告・メール・検索広告）。
ふつうの順番は「ディスプレイ → SNS → メール → 検索」で、検索広告は申し込む直前に使われやすい（最後に来やすい）。
申し込む確率：もともとの確率（ふつう2%、メールを受け取る常連は6%）に、接した広告ごとの本当の上乗せがかかる：
  1−(1−もともとの確率)×Π(1−上乗せ)。上乗せはディスプレイ2.0%・SNS1.5%・メール0.5%・検索0.8%（作成者が置いた値）。
本当の効き目：利用者ごとに「その広告を外したら申し込む確率がどれだけ下がるか」を足し合わせたもの（期待値）。
申し込んだ人について、成果の付け方を4通りで比べる：最後の接点・最初の接点・均等・位置で重み（最初40%・最後40%・間で20%）。
最後の接点と均等は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた確率と順番で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の広告の接点と申し込み（作成者が乱数で作成、seed 674）"
rng = np.random.default_rng(674)
N = 50_000
CH = ["ディスプレイ", "SNS", "メール", "検索"]
EXPO = np.array([.50, .40, .30, .35])
LIFT = np.array([.020, .015, .005, .008])
POS = np.array([0.0, 1.0, 2.0, 3.0])
loyal = rng.random(N) < .30
expo = rng.random((N, 4)) < EXPO
expo[:, 2] &= loyal | (rng.random(N) < .1)          # メールは主に常連へ
expo[:, 3] |= (rng.random(N) < .25) & loyal          # 常連は検索から来やすい
base = np.where(loyal, .06, .02)
keep = (1 - LIFT) ** expo
p = 1 - (1 - base) * keep.prod(1)
conv = rng.random(N) < p
# 本当の効き目（外したときに下がる申し込みの期待値）
true_inc = np.zeros(4)
for c in range(4):
    k2 = keep.copy(); k2[:, c] = 1
    true_inc[c] = (p - (1 - (1 - base) * k2.prod(1))).sum()
base_conv = base.sum(); total_conv_exp = p.sum()
# 接点の順番（ふつうの位置＋揺れ）
order_key = POS + rng.normal(0, .6, (N, 4))
rows = []
for u in np.nonzero(expo.any(1))[0]:
    cs = np.nonzero(expo[u])[0]
    cs = cs[np.argsort(order_key[u, cs])]
    for s, c in enumerate(cs):
        rows.append((u + 1, s + 1, CH[c]))
Tch = pd.DataFrame(rows, columns=["user_id", "seq", "channel"])
U = pd.DataFrame({"user_id": np.arange(1, N + 1), "converted": conv.astype(int)})
DATA.mkdir(exist_ok=True)
Tch.to_csv(DATA / "touches.csv", index=False); U.to_csv(DATA / "users.csv", index=False)

C = Tch.merge(U, on="user_id"); C = C[C.converted == 1].copy()
C["n"] = C.groupby("user_id").seq.transform("max")
C["last"] = (C.seq == C.n).astype(float); C["first"] = (C.seq == 1).astype(float); C["linear"] = 1 / C.n
C["position"] = np.where(C.n == 1, 1.0, np.where(C.n == 2, .5, np.where((C.seq == 1) | (C.seq == C.n), .4, .2 / (C.n - 2).clip(lower=1))))
M = C.groupby("channel")[["last", "first", "linear", "position"]].sum().reindex(CH)
assert np.allclose(M.sum(), M.sum().iloc[0])
conv_with_touch = int(C.user_id.nunique()); conv_total = int(conv.sum())
con = duckdb.connect(); con.execute("SET threads=1"); con.register("touches", Tch); con.register("users", U)
q = (SQL / "02_attribution_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().set_index("channel").reindex(CH)
assert np.allclose(sq.last_touch, M["last"]) and np.allclose(sq.linear, M["linear"])
M["true_incremental"] = true_inc * conv_total / total_conv_exp      # 実際の申し込み数に合わせて目盛りをそろえる
M.round(2).to_csv(RES / "by_channel.csv")
share = M.div(M[["last"]].sum().iloc[0])
out = {"users": N, "conversions": conv_total, "conversions_with_touch": conv_with_touch,
       "expected_conversions": round(float(total_conv_exp), 1), "expected_without_any_ad": round(float(base_conv), 1),
       "expected_incremental_all_ads": round(float(total_conv_exp - base_conv), 1),
       "incremental_share_of_conversions_pct": round(100 * float((total_conv_exp - base_conv) / total_conv_exp), 1),
       "by_channel": {c: {k: round(float(M.loc[c, k]), 1) for k in M.columns} for c in CH},
       "share_pct": {c: {k: round(100 * float(M.loc[c, k] / M[k].sum()), 1) for k in M.columns} for c in CH},
       "last_over_true": {c: round(float(M.loc[c, "last"] / M.loc[c, "true_incremental"]), 2) for c in CH},
       "linear_over_true": {c: round(float(M.loc[c, "linear"] / M.loc[c, "true_incremental"]), 2) for c in CH}}
json.dump(out, open(RES / "a674_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"last": "最後の接点", "first": "最初の接点", "linear": "均等", "position": "位置で重み", "true_incremental": "本当の効き目"}
COL = {"last": ORANGE, "first": LIGHT, "linear": BLUE, "position": GREEN, "true_incremental": INK}
# 図1：広告ごとの成果
fig, ax = plt.subplots(figsize=(8.5, 4.4))
x = np.arange(4); ks = ["last", "first", "linear", "position", "true_incremental"]; w = .16
for i, k in enumerate(ks):
    ax.bar(x + (i - 2) * w, M[k], w, color=COL[k], label=LAB[k])
ax.set_xticks(x); ax.set_xticklabels(CH); ax.set_ylabel("付けた申し込みの数")
ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
ax.set_title("最後の接点では検索広告が最大、本当の効き目ではディスプレイが最大")
save(fig, "a674_by_channel.png", SRC)
# 図2：取り分の割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ks2 = ["last", "first", "linear", "position", "true_incremental"]
left = np.zeros(len(ks2)); colc = [BLUE, GREEN, LIGHT, ORANGE]
for c, cc in zip(CH, colc):
    v = np.array([100 * M.loc[c, k] / M[k].sum() for k in ks2])
    ax.barh([LAB[k] for k in ks2][::-1], v[::-1], left=left[::-1], color=cc, label=c)
    for yy, (l, vv) in enumerate(zip(left[::-1], v[::-1])):
        if vv > 6: ax.text(l + vv / 2, yy, f"{vv:.0f}%", ha="center", va="center", fontsize=8.5, color="white" if cc in (BLUE, ORANGE, GREEN) else INK)
    left += v
ax.set_xlabel("広告ごとの取り分（%）"); ax.legend(frameon=False, fontsize=9, ncol=4, loc="lower center", bbox_to_anchor=(.5, 1.0))
save(fig, "a674_shares.png", SRC)
# 図3：申し込みの中身
fig, ax = plt.subplots(figsize=(8.5, 3.6))
inc = (total_conv_exp - base_conv) / total_conv_exp * conv_total
ax.barh(["本当の内訳（期待値）", "どの付け方でも"], [inc, conv_with_touch], color=[INK, ORANGE])
ax.barh(["本当の内訳（期待値）"], [conv_total - inc], left=[inc], color=LIGHT)
ax.text(inc / 2, 0, f"広告で増えた分 {inc:,.0f}", ha="center", va="center", color="white", fontsize=9)
ax.text(inc + (conv_total - inc) / 2, 0, f"広告がなくても申し込んだ分 {conv_total-inc:,.0f}", ha="center", va="center", fontsize=9)
ax.text(conv_with_touch / 2, 1, f"広告に付けた申し込み {conv_with_touch:,}（全体 {conv_total:,}）", ha="center", va="center", color="white", fontsize=9)
ax.set_xlabel("申し込みの数"); ax.set_title("付け方は、広告がなくても申し込んだ人の分まで広告に付ける")
save(fig, "a674_total.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
