"""A164 学習塾の売上は少子化でも伸びていたのか：伸び率をつないだ指数とトレンド回帰"""
from common import *

lv = load("juku_annual_level.csv").set_index("year")
gr = load("juku_annual_growth.csv").set_index("year")

# 1) 調査対象の追加による段差を除くため、公表の前年比（調整済み）をつないで 2004年＝100 の指数をつくる
idx = pd.concat([pd.DataFrame([[100.0] * gr.shape[1]], index=[2004], columns=gr.columns),
                 (1 + gr / 100).cumprod() * 100]).round(2)
idx.index.name = "year"
idx.to_csv(RES / "a164_chain_index.csv", encoding="utf-8-sig")
per_student = (idx["tuition"] / idx["students"] * 100).round(1)

# 2) トレンド回帰：log(売上指数) = a + b*年（伸びが落ち着いた2012〜2019年）、2020〜2024年を外挿して実績と比べる
fit = idx.loc[2012:2019]
b, a = np.polyfit(fit.index, np.log(fit["sales"]), 1)
pred = np.exp(a + b * idx.index)
resid = np.log(fit["sales"]) - (a + b * fit.index)
r2 = 1 - (resid ** 2).sum() / ((np.log(fit["sales"]) - np.log(fit["sales"]).mean()) ** 2).sum()
tr = pd.DataFrame({"売上指数": idx["sales"], "トレンド": pred.round(2)}, index=idx.index)
tr["実績/トレンド(%)"] = (tr["売上指数"] / tr["トレンド"] * 100).round(1)
tr.to_csv(RES / "a164_trend.csv", encoding="utf-8-sig")

# 同じ回帰を受講生数と1人当たり受講料にも
def slope(s, a0=2004, a1=2019):
    s = s.loc[a0:a1]
    return (np.exp(np.polyfit(s.index, np.log(s), 1)[0]) - 1) * 100

cagr = lambda s, a0, a1: ((s.loc[a1] / s.loc[a0]) ** (1 / (a1 - a0)) - 1) * 100
with open(RES / "a164_summary.txt", "w", encoding="utf-8") as f:
    f.write("前年比をつないだ指数（2004年=100）\n" + idx.loc[[2012, 2019, 2020, 2021, 2024], ["sales", "tuition", "students", "establishments", "instructors", "instr_fulltime", "instr_parttime"]].to_string() + "\n")
    f.write(f"受講生1人当たり受講料収入 指数: 2019 {per_student[2019]} / 2024 {per_student[2024]}\n")
    f.write(f"トレンド（2012〜2019年）: 年 {(np.exp(b)-1)*100:.2f}% 増、R2={r2:.3f}\n")
    f.write(f"年平均伸び率 売上: 2004-12 {cagr(idx['sales'],2004,2012):.2f}% / 2012-19 {cagr(idx['sales'],2012,2019):.2f}% / 2019-24 {cagr(idx['sales'],2019,2024):.2f}%\n")
    f.write(f"年平均伸び率 受講生数: 2004-12 {cagr(idx['students'],2004,2012):.2f}% / 2012-19 {cagr(idx['students'],2012,2019):.2f}% / 2019-24 {cagr(idx['students'],2019,2024):.2f}%\n")
    f.write(f"受講生数のトレンド 2004-2019: {slope(idx['students']):.2f}%/年、1人当たり受講料 {slope(per_student):.2f}%/年\n")
    f.write("実績/トレンド:\n" + tr.loc[2015:].to_string() + "\n")
    f.write(f"公表の実数（不連続あり）: 売上 2004 {lv.loc[2004,'sales']:,} / 2024 {lv.loc[2024,'sales']:,} 百万円、受講生 2024 {lv.loc[2024,'students']:,}人\n")

# 図1 売上・受講生数・1人当たり（指数）
fig, ax = plt.subplots(figsize=(8.6, 4.6))
for s, l, c_ in [(idx["sales"], "売上高", BLUE), (idx["students"], "受講生数", GREEN), (per_student.where(per_student.index >= 2004), "受講生1人当たり受講料収入", ORANGE)]:
    ax.plot(s.index, s, marker="o", ms=3.5, color=c_, lw=2)
    ax.text(2024.3, s.loc[2024], f"{l} {s.loc[2024]:.0f}", va="center", color=c_, fontsize=9.5)
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_xlim(2003.5, 2030.5); ax.set_xticks(range(2004, 2025, 2))
ax.set_ylabel("2004年＝100（前年比をつないだ指数）")
ax.set_title("学習塾の売上高・受講生数・1人当たり受講料（2004年＝100）")
save(fig, "a164_index.png")

# 図2 トレンド回帰
fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.plot(idx.index, idx["sales"], "o-", color=BLUE, ms=4, lw=2, label="売上高（指数）")
ax.plot(idx.index[idx.index >= 2012], pred[idx.index >= 2012], "--", color=GRAY, lw=1.6, label=f"2012〜2019年のトレンド（年{(np.exp(b)-1)*100:.1f}%増）")
ax.axvspan(2019.5, 2024.5, color=LIGHT, alpha=0.3, lw=0)
for y in [2020, 2021, 2024]:
    ax.annotate(f"{tr.loc[y,'実績/トレンド(%)']:.0f}%", (y, idx.loc[y, "sales"]), textcoords="offset points", xytext=(0, -16 if y == 2020 else 9), ha="center", fontsize=9, color=INK)
ax.text(2022, 108, "外挿した期間\n（％は実績÷トレンド）", ha="center", fontsize=8.5, color=GRAY)
ax.set_xticks(range(2004, 2025, 2)); ax.set_ylabel("2004年＝100")
ax.set_title("学習塾の売上高と、2019年までのトレンド")
ax.legend(loc="upper left", frameon=False)
save(fig, "a164_trend.png")

# 図3 講師と事業所
fig, ax = plt.subplots(figsize=(8.6, 4.6))
for k, l, c_ in [("instr_parttime", "非常勤講師", ORANGE), ("instr_fulltime", "専任講師", PURPLE), ("establishments", "事業所数", GRAY), ("students", "受講生数", GREEN)]:
    ax.plot(idx.index, idx[k], marker="o", ms=3, color=c_, lw=1.8)
    ax.text(2024.3, idx.loc[2024, k], f"{l} {idx.loc[2024,k]:.0f}", va="center", color=c_, fontsize=9.5)
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_xlim(2003.5, 2030.5); ax.set_xticks(range(2004, 2025, 2))
ax.set_ylabel("2004年＝100")
ax.set_title("講師数・事業所数・受講生数（2004年＝100、前年比をつないだ指数）")
save(fig, "a164_staff.png")
print(open(RES / "a164_summary.txt", encoding="utf-8").read())
