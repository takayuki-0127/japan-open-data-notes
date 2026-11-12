import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, GREEN
df = pd.read_csv(RES / "requests_outcomes.csv"); sm = json.load(open(RES / "summary.json"))
order = ["期間の逆転", "ありえない日付", "全角の店コード", "存在しない店コード", "引用符入りの文字", "空欄"]
cols = {"黙って0を返した": ORANGE, "黙って誤った数字を返した": "#c0392b", "止まった（エラー・はね返し）": BLUE}
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, impl in zip(axes, ["文字列をつなぐ", "プロシージャ"]):
    d = df[(df.impl == impl) & (df.kind != "正しい入力")]
    t = d.groupby(["kind", "outcome"]).size().unstack(fill_value=0).reindex(order).fillna(0)
    left = np.zeros(len(order))
    for o, c in cols.items():
        v = t[o].values if o in t else np.zeros(len(order))
        ax.barh(range(len(order)), v, left=left, color=c, label=o); left += v
    ax.set_title(f"{impl}：黙って返した {int(sm[impl]['silent_wrong'])}件／{sm[impl]['bad_inputs']}件", loc="left", fontsize=11)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.invert_yaxis(); ax.set_xlabel("件数")
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.07), ncol=3, frameon=False, fontsize=9.5)
fig.suptitle("入力の誤り153件の行き先：文字列をつなぐ形では54%が黙って数字を返し、プロシージャでは全部止まった", x=0.01, y=1.03, ha="left", fontsize=11.5)
save(fig, "a295_outcomes.png", y=-0.1)
# 図2 引用符入りの文字の例
ex = sm["example"]
fig, ax = plt.subplots(figsize=(7.5, 3.2))
ax.barh([1, 0], [ex["right"][1] / 1e6, ex["injected"][1] / 1e6], color=[BLUE, "#c0392b"])
ax.set_yticks([1, 0]); ax.set_yticklabels(["正しい入力 S017", "S017' OR '1'='1"]); ax.set_xlabel("2025年4月の売上（百万円、架空）")
for y, v in [(1, ex["right"][1]), (0, ex["injected"][1])]: ax.text(v / 1e6 + 0.5, y, f"{v/1e6:,.1f}", va="center")
ax.set_title(f"店コードに引用符が混ざると、1店の4月のつもりで「全店の4月＋その店の全期間」を返した（{ex['ratio']}倍）", loc="left", fontsize=10.5)
save(fig, "a295_injection.png", y=-0.13)
# 図3 プロシージャのどの検査で止まったか（表）
p = df[(df.impl == "プロシージャ") & (df.kind != "正しい入力")]
t = p.groupby(["reason"]).size().sort_values(ascending=False)
how = {"日付の形": "DATE 型で受け取る（'2025-02-31' は型の変換で止まる）", "期間の逆転": "IF @date_from > @date_to THROW", "店コードなし": "IF NOT EXISTS (店マスタ) THROW",
       "長さ": "IF LEN(@store_code) <> 4 THROW（VARCHAR(4) で受けるだけだと黙って切り詰められる）", "必須": "IF ... IS NULL THROW"}
rows = [[r, how.get(r, ""), int(v)] for r, v in t.items()]
fig, ax = plt.subplots(figsize=(9, 2.6)); ax.axis("off"); fig.subplots_adjust(left=0.01, right=0.99)
tb = ax.table(cellText=rows, colLabels=["止めた理由", "プロシージャの中の検査（T-SQL）", "件数"], loc="center", cellLoc="left", colWidths=[0.17, 0.7, 0.13])
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.8)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#dddddd")
    if r == 0: cell.set_facecolor("#eef3fb"); cell.set_text_props(weight="bold")
ax.set_title("5行ほどの検査で、入力の誤り153件はすべて集計の前に止まった", loc="left", fontsize=11)
save(fig, "a295_checks.png", y=0.04)
print(t)
