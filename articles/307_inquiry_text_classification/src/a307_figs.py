"""307 図3枚"""
import json
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

S = json.load(open(RES / "summary.json")); bk = pd.read_csv(RES / "accuracy_by_kind.csv"); cm = pd.read_csv(RES / "confusion_matrix.csv", index_col=0)
lc = pd.read_csv(RES / "learning_curve.csv"); th = pd.read_csv(RES / "confidence_threshold.csv")
NAME = {"plain": "ふつうの文", "cross": "ほかのカテゴリの\n言葉が混ざる文", "short": "短い文", "two": "用件が2つ", "vague": "文だけでは\n分からない"}
bk = bk.set_index("kind").loc[["plain", "cross", "short", "two", "vague"]]
fig, ax = plt.subplots(figsize=(9.5, 4.6)); x = np.arange(len(bk))
ax.bar(x - 0.2, bk.model_acc * 100, 0.4, color=BLUE, label=f"TF-IDF＋ロジスティック回帰（全体 {S['acc_model']*100:.1f}%）")
ax.bar(x + 0.2, bk.rule_acc * 100, 0.4, color=ORANGE, label=f"キーワードの決まり（全体 {S['acc_rule']*100:.1f}%）")
for i, (a, b, n) in enumerate(zip(bk.model_acc * 100, bk.rule_acc * 100, bk.n)):
    ax.text(i - 0.2, a + 1, f"{a:.0f}", ha="center", fontsize=9); ax.text(i + 0.2, b + 1, f"{b:.0f}", ha="center", fontsize=9, color=ORANGE)
ax.set_xticks(x); ax.set_xticklabels([f"{NAME[k]}\n（{n}件）" for k, n in zip(bk.index, bk.n)], fontsize=9); ax.set_ylabel("正解率（%）"); ax.set_ylim(0, 118)
ax.set_title("間違いは「用件が2つ」と「文だけでは分からない」に集まった（テスト600件）", loc="left"); ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=1)
save(fig, "a307_by_kind.png", y=-0.04)

fig, ax = plt.subplots(figsize=(7.6, 6)); v = cm.values
ax.imshow(v, cmap="Blues", vmax=v.max())
for i in range(6):
    for j in range(6):
        if v[i, j]: ax.text(j, i, str(v[i, j]), ha="center", va="center", fontsize=10, color="white" if v[i, j] > v.max() * 0.5 else INK)
ax.set_xticks(range(6)); ax.set_xticklabels(cm.columns, rotation=30, ha="right", fontsize=9); ax.set_yticks(range(6)); ax.set_yticklabels(cm.index, fontsize=9)
ax.set_xlabel("モデルが分けた先"); ax.set_ylabel("正しいカテゴリ"); ax.set_title(f"どこと取り違えたか（間違い {S['errors']}件）", loc="left")
for s in ax.spines.values(): s.set_visible(False)
save(fig, "a307_confusion.png", y=-0.02)

fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
ax = axs[0]; ax.plot(lc.n_train, lc.acc_mean * 100, "o-", color=BLUE); ax.fill_between(lc.n_train, lc.acc_min * 100, lc.acc_max * 100, color=LIGHT, alpha=.6)
for n, a in zip(lc.n_train, lc.acc_mean * 100): ax.text(n, a - 5, f"{a:.0f}", ha="center", fontsize=8.5)
ax.set_xscale("log"); ax.set_xticks(lc.n_train); ax.set_xticklabels(lc.n_train, fontsize=8); ax.set_xlabel("学習に使った件数（ラベルつき）"); ax.set_ylabel("正解率（%）")
ax.set_title("学習の件数と正解率（帯は10通りの最小〜最大）", loc="left", fontsize=11.5)
ax = axs[1]; ax.plot(th.auto_share * 100, th.auto_acc * 100, "o-", color=BLUE)
for t, a, b in zip(th.threshold, th.auto_share * 100, th.auto_acc * 100): ax.text(a, b - 0.9, f"自信{t:.1f}以上" if t else "全部", ha="center", fontsize=8.5)
ax.set_xlabel("自動で分ける割合（%）"); ax.set_ylabel("自動で分けた分の正解率（%）"); ax.set_ylim(90, 101)
ax.set_title("自信の高いものだけ自動にすると", loc="left", fontsize=11.5)
save(fig, "a307_curve_threshold.png", y=-0.03)
print("ok")
