"""407 名前を消しただけの顧客データは、何%の人が1人に絞れてしまうのか
架空の顧客10万人（郵便番号・生年月日・性別）で、項目の組み合わせが1人だけになる行を数える。乱数の種は407。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 407
N_ZIP7, N_ZIP3 = 12_000, 90           # 架空の地域：7桁の郵便番号が12,000個、上3桁が90個


_g = np.random.default_rng(SEED)                              # 地域（郵便番号）は、どの表でも同じものを使う
ZIP3 = _g.integers(0, N_ZIP3, N_ZIP7)                         # 7桁の郵便番号がどの上3桁に入るか
ZIPW = _g.lognormal(0, 1.0, N_ZIP7); ZIPW /= ZIPW.sum()       # 郵便番号ごとの住民の多さ（偏らせる）
ZIP7 = (100 + ZIP3) * 10_000 + pd.Series(ZIP3).groupby(ZIP3).cumcount().to_numpy()


def make(n, seed):
    """架空の人 n 人。年齢は18〜89歳。地域は共通で、人だけを seed で変える"""
    r = np.random.default_rng(seed)
    z = r.choice(N_ZIP7, n, p=ZIPW)
    ages = np.arange(18, 90); aw = np.exp(-0.5 * ((ages - 47) / 17) ** 2) + 0.15
    age = r.choice(ages, n, p=aw / aw.sum())
    doy = r.integers(0, 365, n)                                # 誕生日（うるう日は入れない）
    by = 2025 - age - (doy > 300)                              # 生まれた年
    sex = r.integers(0, 2, n)
    d = pd.to_datetime(by.astype(str)) + pd.to_timedelta(doy, unit="D")
    return pd.DataFrame({"顧客ID": np.arange(1, n + 1), "郵便番号7桁": ZIP7[z], "郵便番号3桁": 100 + ZIP3[z],
                         "生年月日": d.strftime("%Y-%m-%d"), "性別": np.where(sex == 0, "女", "男")})


def add_cols(df):
    df = df.copy()
    df["生年月"] = df["生年月日"].str[:7]; df["生年"] = df["生年月日"].str[:4].astype(int)
    df["年齢5歳きざみ"] = ((2025 - df["生年"]) // 5) * 5; df["年齢10歳きざみ"] = ((2025 - df["生年"]) // 10) * 10
    return df


COMBOS = {  # 名前：使う列
    "郵便番号7桁＋生年月日＋性別": ["郵便番号7桁", "生年月日", "性別"],
    "郵便番号7桁＋生年月日": ["郵便番号7桁", "生年月日"],
    "郵便番号7桁＋生年月＋性別": ["郵便番号7桁", "生年月", "性別"],
    "郵便番号7桁＋生年＋性別": ["郵便番号7桁", "生年", "性別"],
    "郵便番号7桁＋5歳きざみ＋性別": ["郵便番号7桁", "年齢5歳きざみ", "性別"],
    "郵便番号7桁＋10歳きざみ＋性別": ["郵便番号7桁", "年齢10歳きざみ", "性別"],
    "郵便番号3桁＋生年月日＋性別": ["郵便番号3桁", "生年月日", "性別"],
    "郵便番号3桁＋生年月＋性別": ["郵便番号3桁", "生年月", "性別"],
    "郵便番号3桁＋生年＋性別": ["郵便番号3桁", "生年", "性別"],
    "郵便番号3桁＋5歳きざみ＋性別": ["郵便番号3桁", "年齢5歳きざみ", "性別"],
    "郵便番号3桁＋10歳きざみ＋性別": ["郵便番号3桁", "年齢10歳きざみ", "性別"],
    "生年月日＋性別": ["生年月日", "性別"],
    "郵便番号7桁だけ": ["郵便番号7桁"],
    "生年＋性別": ["生年", "性別"],
}


def k_stats(df, cols):
    k = df.groupby(cols)[cols[0]].transform("size").to_numpy()
    return {"組み合わせの数": int(df.groupby(cols).ngroups), "1人に絞れる(%)": round(100 * (k == 1).mean(), 2),
            "2人以下(%)": round(100 * (k <= 2).mean(), 2), "5人未満(%)": round(100 * (k < 5).mean(), 2),
            "10人未満(%)": round(100 * (k < 10).mean(), 2), "kの中央値": float(np.median(k)), "kの最小": int(k.min())}


# ---- 1. 10万人：項目の組み合わせごと ----
df = add_cols(make(100_000, SEED + 10))
df[["顧客ID", "郵便番号7桁", "郵便番号3桁", "生年月日", "性別"]].to_csv(DATA / "customers.csv", index=False)
T1 = pd.DataFrame([{"組み合わせ": name, **k_stats(df, cols)} for name, cols in COMBOS.items()])
T1.to_csv(RES / "unique_by_combo.csv", index=False)

# SQL（DuckDB）でも同じ数になるか
con = duckdb.connect(); con.register("customers", df)
q = """
WITH g AS (
  SELECT "郵便番号7桁", "生年月日", "性別", COUNT(*) AS k
  FROM customers GROUP BY "郵便番号7桁", "生年月日", "性別"
)
SELECT SUM(CASE WHEN k = 1 THEN k ELSE 0 END) AS 一人だけ,
       SUM(CASE WHEN k < 5 THEN k ELSE 0 END) AS 五人未満, SUM(k) AS 全体 FROM g"""
s = con.sql(q).fetchone()
assert abs(100 * s[0] / s[2] - T1.iloc[0]["1人に絞れる(%)"]) < 0.006
pd.DataFrame([{"1人だけ": s[0], "5人未満": s[1], "全体": s[2]}]).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- 2. 人数を変える（同じ地域に何人の顧客がいるか）----
rows = []
SEL = ["郵便番号7桁＋生年月日＋性別", "郵便番号7桁＋生年＋性別", "郵便番号3桁＋生年月日＋性別", "郵便番号3桁＋生年月＋性別",
       "郵便番号3桁＋生年＋性別", "郵便番号3桁＋5歳きざみ＋性別"]
for n in [1_000, 10_000, 100_000, 1_000_000]:
    d = add_cols(make(n, SEED + 1))
    for name in SEL:
        rows.append({"顧客の数": n, "組み合わせ": name, **k_stats(d, COMBOS[name])})
T2 = pd.DataFrame(rows); T2.to_csv(RES / "unique_by_size.csv", index=False)

# ---- 3. 5人未満の行を消す／粗くする：どれだけ残るか ----
rows = []
for name in ["郵便番号7桁＋生年月日＋性別", "郵便番号3桁＋生年月＋性別", "郵便番号3桁＋生年＋性別", "郵便番号3桁＋5歳きざみ＋性別",
             "郵便番号3桁＋10歳きざみ＋性別"]:
    cols = COMBOS[name]; k = df.groupby(cols)[cols[0]].transform("size").to_numpy()
    for kk in (2, 5, 10):
        rows.append({"組み合わせ": name, "k": kk, "消さずに出せる行(%)": round(100 * (k >= kk).mean(), 2)})
T3 = pd.DataFrame(rows); T3.to_csv(RES / "rows_kept_by_k.csv", index=False)

# ---- 4. 外の名簿と突き合わせる：名前を消した表の何%に、1人の名前が付くか ----
# 外の名簿＝同じ地域の住民のうち、顧客を全員含む名簿（顧客10万人＋顧客でない人40万人）。同じ3項目を持つ
others = add_cols(make(400_000, SEED + 3))
pop = pd.concat([df.assign(客=1), others.assign(客=0)], ignore_index=True)
rows = []
for name in ["郵便番号7桁＋生年月日＋性別", "郵便番号7桁＋生年＋性別", "郵便番号3桁＋生年月日＋性別", "郵便番号3桁＋生年月＋性別", "郵便番号3桁＋生年＋性別"]:
    cols = COMBOS[name]
    kp = pop.groupby(cols)["客"].transform("size").to_numpy()[: len(df)]          # 名簿の中で同じ組み合わせの人数
    kc = df.groupby(cols)[cols[0]].transform("size").to_numpy()                   # 顧客の表の中だけで数えた人数
    rows.append({"組み合わせ": name, "顧客の表の中で1人(%)": round(100 * (kc == 1).mean(), 2),
                 "50万人の名簿の中でも1人(%)": round(100 * (kp == 1).mean(), 2)})
T4 = pd.DataFrame(rows); T4.to_csv(RES / "unique_in_population.csv", index=False)

main = {"顧客": 100_000, "郵便番号7桁の数": int(df["郵便番号7桁"].nunique()), "郵便番号3桁の数": int(df["郵便番号3桁"].nunique()),
        "組み合わせごと": T1.set_index("組み合わせ")[["1人に絞れる(%)", "5人未満(%)", "kの中央値"]].to_dict("index"),
        "人数を変える": {f"{n}人": T2[T2["顧客の数"] == n].set_index("組み合わせ")["1人に絞れる(%)"].to_dict() for n in T2["顧客の数"].unique()},
        "名簿との突き合わせ": T4.set_index("組み合わせ").to_dict("index")}
json.dump(main, open(RES / "a407_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
SRC = "架空の顧客データ（作成者が乱数で作成、seed 407）"
show = ["郵便番号7桁＋生年月日＋性別", "郵便番号7桁＋生年＋性別", "郵便番号7桁＋10歳きざみ＋性別", "郵便番号3桁＋生年月日＋性別",
        "郵便番号3桁＋生年月＋性別", "郵便番号3桁＋生年＋性別", "郵便番号3桁＋5歳きざみ＋性別", "郵便番号3桁＋10歳きざみ＋性別", "生年月日＋性別", "郵便番号7桁だけ"]
t = T1.set_index("組み合わせ").loc[show][::-1]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.barh(t.index, t["5人未満(%)"], color=LIGHT, label="同じ組み合わせが5人未満")
ax.barh(t.index, t["1人に絞れる(%)"], color=BLUE, label="1人だけ（1人に絞れる）")
for i, (a, b) in enumerate(zip(t["1人に絞れる(%)"], t["5人未満(%)"])):
    ax.text(max(a, b) + 1, i, f"{a:.1f}%／{b:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, 118); ax.set_xlabel("顧客10万人のうちの割合（%）"); ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.set_title("名前を消しても、残した項目の組み合わせで1人に絞れる割合")
save(fig, "a407_unique_by_combo.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4.4))
for name, c in zip(SEL, [INK, BLUE, ORANGE, GREEN, GRAY, LIGHT]):
    s = T2[T2["組み合わせ"] == name]
    ax.plot(range(4), s["1人に絞れる(%)"], marker="o", color=c, label=name)
ax.set_xticks(range(4)); ax.set_xticklabels(["1,000人", "1万人", "10万人", "100万人"]); ax.set_ylim(-3, 103)
ax.set_xlabel("表に入っている顧客の数（地域の広さは同じ）"); ax.set_ylabel("1人に絞れる割合（%）")
ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.0, 0.5)); ax.set_title("顧客の数が少ない表ほど、1人に絞れる")
save(fig, "a407_unique_by_size.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4.2))
names = T4["組み合わせ"]; x = np.arange(len(names)); w = 0.38
ax.bar(x - w / 2, T4["顧客の表の中で1人(%)"], w, color=LIGHT, label="顧客の表（10万人）の中で1人だけ")
ax.bar(x + w / 2, T4["50万人の名簿の中でも1人(%)"], w, color=ORANGE, label="住民50万人の名簿の中でも1人だけ")
for i, (a, b) in enumerate(zip(T4["顧客の表の中で1人(%)"], T4["50万人の名簿の中でも1人(%)"])):
    ax.text(i - w / 2, a + 1.5, f"{a:.1f}", ha="center", fontsize=9); ax.text(i + w / 2, b + 1.5, f"{b:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([n.replace("＋", "\n＋") for n in names], fontsize=8); ax.set_ylim(0, 112); ax.set_ylabel("割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("同じ項目を持つ名簿と突き合わせたとき、1人の名前が付く割合")
save(fig, "a407_unique_in_population.png", SRC, y=-0.06)
print(T1.to_string()); print(T2.pivot(index="組み合わせ", columns="顧客の数", values="1人に絞れる(%)").to_string()); print(T3.to_string()); print(T4.to_string())
