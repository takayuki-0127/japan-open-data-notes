"""I1：動画共有サイト（YouTube など）・SNS・オンラインゲームを使う人は、年代でどれくらい違うか。2019年→2025年でどう変わったか"""
from common import *
AGES = ["６～１２歳", "１３～１９歳", "２０～２９歳", "３０～３９歳", "４０～４９歳", "５０～５９歳", "６０～６９歳", "７０～７９歳", "８０歳以上"]
AGEL = ["6〜12歳", "13〜19歳", "20代", "30代", "40代", "50代", "60代", "70代", "80歳以上"]

def by_age(df, col):
    a = df[(df.section == "本人の性別・年齢") & (df.sex == "男女計")].drop_duplicates("label").set_index("label")
    return a.loc[AGES, col].astype(float).values

use25, use19 = read_table("構9表"), read_table("構9表", path=RAW / "r1_kosein.xls")
s25, s19 = read_table("構15表"), read_table("構14表", path=RAW / "r1_kosein.xls")
V25, V19 = "動画投稿・共有サイトの利用（ＹｏｕＴｕｂｅ、ニコニコ動画など）", "動画投稿・共有サイトの利用"
G25 = G19 = "オンラインゲームの利用"
u25, u19 = by_age(use25, "はい"), by_age(use19, "はい")
t = pd.DataFrame({"age": AGEL, "internet_2025": u25, "internet_2019": u19,
                  "video_users_2025": by_age(s25, V25), "video_users_2019": by_age(s19, V19),
                  "sns_users_2025": by_age(s25, "ＳＮＳ（無料通話機能を含む）の利用"), "freevod_users_2025": by_age(s25, "無料動画配信サービスの利用（Tver、NHKプラスなど）"),
                  "game_users_2025": by_age(s25, G25), "game_users_2019": by_age(s19, G19)})
for c in ["video", "game"]:                     # 人口に占める割合 ＝ ネット利用率 × 利用者のうちの割合
    for y in ["2025", "2019"]:
        t[f"{c}_pop_{y}"] = t[f"internet_{y}"] * t[f"{c}_users_{y}"] / 100
t["sns_pop_2025"] = t.internet_2025 * t.sns_users_2025 / 100
t["freevod_pop_2025"] = t.internet_2025 * t.freevod_users_2025 / 100
t["video_pop_ratio"] = t.video_pop_2025 / t.video_pop_2019
t.round(2).to_csv(RES / "i1_by_age.csv", index=False, encoding="utf-8-sig"); print(t.round(1).to_string())
sns = read_table("構16表"); sa = sns[(sns.section == "本人の性別・年齢") & (sns.sex == "男女計")].drop_duplicates("label").set_index("label").loc[AGES]
purpose = sa[["従来からの知人とのコミュニケーションのため", "知りたいことについて情報を探すため", "ひまつぶしのため", "災害発生時の情報収集・発信のため", "自分の情報や作品などの発信のため"]].astype(float)
purpose.index = AGEL; purpose.to_csv(RES / "i1_sns_purpose.csv", encoding="utf-8-sig"); print(purpose)
tot25 = s25[s25.label == "男女計："].iloc[0]; tot19 = s19[s19.label == "男女計："].iloc[0]
s = {"video_users_all_2025": tot25[V25], "video_users_all_2019": tot19[V19], "video_pop_60s_2019": t.loc[6, "video_pop_2019"], "video_pop_60s_2025": t.loc[6, "video_pop_2025"],
     "video_pop_70s_2019": t.loc[7, "video_pop_2019"], "video_pop_70s_2025": t.loc[7, "video_pop_2025"], "video_pop_20s_2025": t.loc[2, "video_pop_2025"]}
pd.Series(s).round(2).to_csv(RES / "i1_summary.csv", header=["value"]); print(pd.Series(s).round(1))

# 図1：2025年、年代別に「使っている人の割合（人口に占める）」
fig, ax = plt.subplots(figsize=(9, 4.4)); x = np.arange(len(AGEL)); w = 0.2
for i, (c, lab, col) in enumerate([("sns_pop_2025", "SNS", BLUE), ("video_pop_2025", "動画投稿・共有サイト（YouTube など）", ORANGE), ("freevod_pop_2025", "無料動画配信（TVer など）", GREEN), ("game_pop_2025", "オンラインゲーム", PURPLE)]):
    ax.bar(x + (i - 1.5) * w, t[c], width=w, color=col, label=lab)
ax.set_xticks(x, AGEL); ax.set_ylabel("その年代の人のうち、使った人（%）"); ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
ax.set_title("動画サイトは20〜40代の7割が使い、70代でも2割（2025年）", loc="left")
fig.text(0.01, -0.04, SOURCE + "（ネットの利用率 × 利用者のうち各サービスを使った割合）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "i1_by_age.png"); plt.close(fig)

# 図2：2019年→2025年
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(AGEL, t.video_pop_2019, marker="o", color=GRAY, label="2019年")
ax.plot(AGEL, t.video_pop_2025, marker="o", color=ORANGE, label="2025年")
for i, (a, b) in enumerate(zip(t.video_pop_2019, t.video_pop_2025)):
    ax.annotate(f"{b - a:+.0f}", (i, b), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, color="#52514e")
ax.set_ylabel("動画投稿・共有サイトを使った人（%、人口に占める）"); ax.set_ylim(0, 85); ax.legend(frameon=False, loc="upper right")
ax.set_title("6年で、60代は23%→45%、70代は7%→21%に", loc="left")
fig.text(0.01, -0.04, SOURCE.replace("令和7年", "令和元年・令和7年") + "（数字は2025年−2019年のポイント差）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "i1_change.png"); plt.close(fig)

# 図3：SNS の利用目的（ひまつぶし・情報収集）
fig, ax = plt.subplots(figsize=(9, 4))
for c, col, lab in [("知りたいことについて情報を探すため", BLUE, "知りたいことを探すため"), ("ひまつぶしのため", ORANGE, "ひまつぶしのため"), ("災害発生時の情報収集・発信のため", GREEN, "災害時の情報収集・発信")]:
    ax.plot(AGEL, purpose[c], marker="o", color=col, label=lab)
ax.set_ylabel("SNS 利用者のうち（%、複数回答）"); ax.set_ylim(0, 85); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("SNS を「ひまつぶし」に使う人は30代がいちばん多く、年代が上がると減る", loc="left")
fig.text(0.01, -0.04, SOURCE + "（「従来からの知人とのコミュニケーション」はどの年代も8割前後なので省略）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "i1_sns_purpose.png"); plt.close(fig)
