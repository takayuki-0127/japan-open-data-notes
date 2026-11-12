"""312 図3枚"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

base = pd.read_csv(RES / "ten_queries.csv"); sw = pd.read_csv(RES / "null_rate_sweep.csv")
lab = [n.split("_", 1)[0] + " " + n.split("_", 1)[1] for n in base["書き方"]]

# 図1：14本の差
fig, ax = plt.subplots(figsize=(9.2, 6.2))
v = base["差(%)"].values
ax.barh(range(14), v, color=[ORANGE if x > 0 else (BLUE if x < 0 else GRAY) for x in v]); ax.set_yticks(range(14)); ax.set_yticklabels(lab, fontsize=8.8); ax.invert_yaxis()
ax.axvline(0, color=INK, lw=0.8); ax.axhline(9.5, color=GRAY, lw=0.8, ls=":")
for i, x in enumerate(v):
    ax.text(x + (2 if x >= 0 else -2), i, "差なし" if x == 0 else f"{x:+.1f}%", va="center", ha="left" if x >= 0 else "right", fontsize=9, color=INK)
ax.set_xlim(-125, 75); ax.set_xlabel("NULL を気にしない書き方と、扱いを書いた書き方の差（%）")
ax.set_title("14本のうち10本がずれ、エラーは1本も出なかった\n（点線より下の4本は、NULL を気にしなくても意図どおりになる書き方）", loc="left")
save(fig, "a312_ten.png")

# 図2：NULL の割合を変える
fig, ax = plt.subplots(figsize=(9, 4.8))
show = {"Q04": ("Q04 NOT IN", ORANGE, "-"), "Q02": ("Q02 値引き後の売上（引き算）", BLUE, "-"), "Q06": ("Q06 NOT（…）", GREEN, "-"),
        "Q05": ("Q05 <> の比較", GRAY, "-"), "Q10": ("Q10 外部結合のあとの引き算", INK, "--")}
x = sorted(sw["NULLの倍率"].unique())
for k, (name, c, ls) in show.items():
    d = sw[sw["書き方"].str.startswith(k)].sort_values("NULLの倍率")
    ax.plot(range(len(x)), d["差(%)"].abs().values, ls, color=c, marker="o", ms=4, label=name)
ax.set_xticks(range(len(x))); ax.set_xticklabels(["0", "2%", "10%", "25%", "50%", "100%\n（基本）", "150%"])
ax.set_xlabel("NULL の入れ方（基本の割合に対する倍率）"); ax.set_ylabel("差の大きさ（%）"); ax.set_ylim(0, 110)
ax.legend(frameon=False, fontsize=9, loc="center right")
ax.set_title("ずれ方は3通り：NULL が少しでもあれば全部消える（NOT IN）、\n割合に応じて大きくなる、データに NULL がなくても起きる（外部結合）", loc="left")
save(fig, "a312_rate.png")

# 図3：なぜずれるか・どう書くか（表）
rows = [("Q01 AVG(割引)", "NULL の行を分母から外す", "AVG(COALESCE(割引, 0))"),
        ("Q02 SUM(金額 − 割引)", "NULL を引くと NULL になり、行ごと合計から外れる", "金額 − COALESCE(割引, 0)"),
        ("Q03 COUNT(顧客番号)", "NULL の行を数えない", "COUNT(*)"),
        ("Q04 NOT IN (副問い合わせ)", "副問い合わせに NULL が1つあると、結果は0行", "NOT EXISTS"),
        ("Q05 地域 <> '関東'", "NULL との比較は真にならず、行が外れる", "… OR 地域 IS NULL"),
        ("Q06 NOT (割引 > 100)", "NOT をつけても NULL は真にならない", "COALESCE(割引, 0) <= 100"),
        ("Q07 SUM(年齢) / COUNT(*)", "分子は NULL を外し、分母は外さない", "分母を COUNT(生年) に"),
        ("Q08 姓 + ' ' + 名", "どちらかが NULL だと全体が NULL", "CONCAT(姓, ' ', 名)"),
        ("Q09 地域で集計してから結合", "NULL どうしは等しくないので結合で落ちる", "COALESCE(地域, '不明') で集計"),
        ("Q10 売上 − 返品（外部結合）", "相手のない行は NULL になり、引き算が NULL に", "売上 − COALESCE(返品, 0)")]
fig, ax = plt.subplots(figsize=(10.2, 5.4)); ax.axis("off")
t = ax.table(cellText=rows, colLabels=["NULL を気にしない書き方", "何が起きるか", "扱いを書いた書き方"], cellLoc="left", colLoc="left", loc="center", colWidths=[0.27, 0.43, 0.30])
t.auto_set_font_size(False); t.set_fontsize(9.2); t.scale(1, 1.75)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#dddcd6"); cell.set_linewidth(0.6)
    if r == 0: cell.set_facecolor(LIGHT); cell.set_text_props(fontweight="bold")
ax.set_title("ずれた10本：何が起きたかと、扱いを書いた書き方", loc="left", fontsize=13)
save(fig, "a312_why.png", y=0.02)
