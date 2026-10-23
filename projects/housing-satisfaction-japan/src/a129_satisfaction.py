"""129：住まいへの不満は何に多いか、10年でどう変わったか、総合的な不満と結びつくのはどれか（住生活総合調査 表4）"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import *

df = load()
el = df[df.group.isin(["住宅", "居住環境"])]
ANS = ["満足", "まあ満足", "多少不満", "非常に不満"]
w = el.pivot_table(index=["year", "group", "item"], columns="answer", values="総計").reset_index()
w["回答計"] = w[ANS].sum(axis=1)
w["不満率"] = (w["多少不満"] + w["非常に不満"]) / w["回答計"]
w["非常に不満率"] = w["非常に不満"] / w["回答計"]
w.round(4).to_csv(RES / "a129_element_dissatisfaction.csv", index=False)

# 総合満足度の不満率（不明を除く）
def odis(r):
    return (r["総合_多少不満"] + r["総合_非常に不満"]) / (r["総計"] - r["総合_不明"])
tot = df[df.group == "総計"].assign(総合の不満率=lambda d: d.apply(odis, axis=1))[["year", "総計", "総合の不満率"]]
tot.round(4).to_csv(RES / "a129_overall.csv", index=False)

# 持ち家・借家、世帯の型（2023年のみ表にある）
att = df[df.group.str.startswith("属性：持ち家")].copy()
att["総合の不満率"] = att.apply(odis, axis=1)
att["tenure"] = np.where(att.item.isin(["持ち家", "借家", "不明"]), att.item, None)
att["tenure"] = att["tenure"].ffill()
att[["tenure", "item", "総計", "総合の不満率"]].round(4).to_csv(RES / "a129_tenure_2023.csv", index=False)

# 要素の満足／不満ごとの、総合の不満率（2023年）
g = el[el.year == 2023].copy()
g["総合の不満"] = g["総合_多少不満"] + g["総合_非常に不満"]
g["総合の回答"] = g["総計"] - g["総合_不明"]
g["side"] = np.where(g.answer.isin(["満足", "まあ満足"]), "要素に満足", np.where(g.answer.isin(["多少不満", "非常に不満"]), "要素に不満", None))
h = g.dropna(subset=["side"]).groupby(["group", "item", "side"])[["総合の不満", "総合の回答"]].sum()
h = (h["総合の不満"] / h["総合の回答"]).unstack()
h["差（ポイント）"] = (h["要素に不満"] - h["要素に満足"]) * 100
h["比"] = h["要素に不満"] / h["要素に満足"]
h = h.sort_values("差（ポイント）", ascending=False)
h.round(4).to_csv(RES / "a129_link_overall_2023.csv")

# 2013年と2023年で中身がほぼ同じ項目（表記が違うものは対応づけ）
MAP = [  # 表示名, group, 2013の項目の頭, 2023の項目の頭
    ("広さや間取り", "住宅", "①住宅の広さ", "①広さや間取り"), ("収納", "住宅", "②収納", "②収納"),
    ("台所・トイレ・浴室（水回り）", "住宅", "③台所", "③水回り"), ("いたみの少なさ", "住宅", "⑧住宅のいたみ", "④いたみ"),
    ("維持管理のしやすさ", "住宅", "⑨住宅の維持管理", "⑤維持管理"), ("換気", "住宅", "⑬換気", "⑥換気"),
    ("居室の採光", "住宅", "⑭居間", "⑦居間"), ("外部の騒音への遮音", "住宅", "⑮外部", "⑧外部"),
    ("上下階・隣戸の音への遮音", "住宅", "⑯上下階", "⑨上下階"), ("断熱性", "住宅", "⑩住宅の断熱", "⑩断熱"),
    ("省エネ性（光熱費）", "住宅", "⑪冷暖房", "⑪エネルギー"), ("高齢者への配慮", "住宅", "⑫高齢者", "⑫高齢者"),
    ("地震への安全性", "住宅", "④地震", "⑭地震"), ("火災への安全性", "住宅", "⑥火災", "⑯火災"),
    ("防犯性", "住宅", "⑦住宅の防犯", "⑰防犯"), ("プライバシー", "住宅", "⑰外部からのプライバシー", "⑱プライバシー"),
    ("通勤・通学の利便", "居住環境", "⑫通勤", "①通勤"), ("治安", "居住環境", "④治安", "⑧治安"),
    ("近隣との関わり", "居住環境", "⑰近隣", "⑦近隣"), ("親・子との距離", "居住環境", "⑯親", "⑥親"),
    ("歩行時の安全性", "居住環境", "⑥まわりの道路", "⑨道路"), ("災害時の避難", "居住環境", "①災害時", "⑩災害時"),
    ("延焼のしにくさ", "居住環境", "③火災の延焼", "⑫周辺からの延焼"), ("騒音・大気汚染", "居住環境", "⑤騒音", "⑬騒音"),
    ("空間のゆとり", "居住環境", "⑧敷地の広さ", "⑭敷地の広さ"), ("自然とのふれあい", "居住環境", "⑩緑", "⑮公園"),
    ("まちなみ・景観", "居住環境", "⑪まちなみ", "⑯まちなみ"), ("バリアフリー（敷地・まわり）", "居住環境", "⑦敷地やまわり", "⑰敷地やまわり"),
]
def pick(y, grp, head):
    d = w[(w.year == y) & (w.group == grp) & w.item.str.startswith(head)]
    assert len(d) == 1, (y, grp, head, len(d))
    return d.iloc[0]
rows = []
for name, grp, h13, h23 in MAP:
    a, b = pick(2013, grp, h13), pick(2023, grp, h23)
    rows.append(dict(項目=name, group=grp, item2013=a.item, item2023=b.item, 不満率2013=a["不満率"], 不満率2023=b["不満率"]))
ch = pd.DataFrame(rows)
ch["変化（ポイント）"] = (ch["不満率2023"] - ch["不満率2013"]) * 100
ch = ch.sort_values("変化（ポイント）")
ch.round(4).to_csv(RES / "a129_change_2013_2023.csv", index=False)

print(tot.round(4)); print(att[["tenure", "item", "総合の不満率"]].round(3))
print(w[w.year == 2023].sort_values("不満率", ascending=False)[["group", "item", "不満率", "非常に不満率"]].round(3).head(8))
print(w[w.year == 2023].sort_values("不満率")[["group", "item", "不満率"]].round(3).head(5))
print(ch[["項目", "不満率2013", "不満率2023", "変化（ポイント）"]].round(3).to_string())
print(h.round(3).head(8)); print(h.round(3).tail(5))

# 図1：2023年の不満率（住宅・居住環境の全要素）
d = w[w.year == 2023].sort_values("不満率")
short = lambda s: re.sub(r"^[①-⑳]", "", s)[:22]
fig, ax = plt.subplots(figsize=(7.5, 10))
yy = np.arange(len(d))
col = [BLUE if g_ == "住宅" else GREEN for g_ in d.group]
ax.barh(yy, d["不満率"] * 100, color=col, height=0.7)
ax.barh(yy, d["非常に不満率"] * 100, color=INK, alpha=0.35, height=0.7)
ax.set_yticks(yy, [short(s) for s in d.item], fontsize=8.5)
ax.set_xlabel("不満の割合（%、「多少不満」＋「非常に不満」、不明を除く）")
ax.set_title("2023年、住まいの要素ごとの不満の割合", loc="left")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="住宅"), Patch(color=GREEN, label="居住環境"), Patch(color=INK, alpha=0.35, label="うち非常に不満")], loc="lower right", frameon=False)
fig.text(0, -0.02, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a129_rank2023.png"); plt.close(fig)

# 図2：2013→2023 の変化（ダンベル）
fig, ax = plt.subplots(figsize=(7.5, 8.5))
c2 = ch.sort_values("不満率2023")
yy = np.arange(len(c2))
for i, r in enumerate(c2.itertuples()):
    ax.plot([r.不満率2013 * 100, r.不満率2023 * 100], [i, i], color=LIGHT, lw=2.5, zorder=1)
ax.scatter(c2["不満率2013"] * 100, yy, color=GRAY, s=28, label="2013年", zorder=2)
ax.scatter(c2["不満率2023"] * 100, yy, color=ORANGE, s=34, label="2023年", zorder=3)
ax.set_yticks(yy, c2["項目"], fontsize=9)
ax.set_xlabel("不満の割合（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("10年で、ほとんどの項目の不満は減った", loc="left")
fig.text(0, -0.03, "2013年と2023年で調査票の項目の言い回しが違うものは、内容が近い項目どうしを対応させた。\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a129_change.png"); plt.close(fig)

# 図3：要素に不満な世帯ほど総合でも不満か（2023年）
fig, ax = plt.subplots(figsize=(7.5, 6.5))
hh = h.reset_index()
ax.scatter(hh["要素に満足"] * 100, hh["要素に不満"] * 100, c=[BLUE if g_ == "住宅" else GREEN for g_ in hh.group], s=40, alpha=0.85, edgecolor="white")
for r in hh.head(3).itertuples():
    ax.annotate(short(r.item)[:12], (r.要素に満足 * 100, r.要素に不満 * 100), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
for r in hh.tail(3).itertuples():
    ax.annotate(short(r.item)[:12], (r.要素に満足 * 100, r.要素に不満 * 100), fontsize=8.5, xytext=(4, -10), textcoords="offset points")
ax.axhline(tot[tot.year == 2023]["総合の不満率"].iloc[0] * 100, color=GRAY, ls="--", lw=0.8)
ax.set_xlabel("その要素に満足している世帯の、総合での不満の割合（%）")
ax.set_ylabel("その要素に不満な世帯の、総合での不満の割合（%）")
ax.set_title("治安や維持管理に不満な世帯は、総合でも4割以上が不満", loc="left")
fig.text(0, -0.04, "点線は全世帯の総合の不満の割合。青は住宅、緑は居住環境の要素。\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a129_link.png"); plt.close(fig)
